"""Upload each tile pyramid that R2 does not have yet; pyramids never change once named.

Files go up with rclone through R2's S3-compatible endpoint, which, unlike the account API
behind `wrangler r2 bulk put`, has no limit of a few requests a second. rclone lists what
the bucket already has and sends only what is missing, so a stopped run picks up where it
left off; each pyramid is recorded once it is complete. The index files go last, so the
manifest never names a pyramid R2 does not have yet.

Two sets of pyramids go up. The ones the manifest on disk names are a whole build, since
the build rewrites the manifest only once every view is finished; they are what the index
files publish. The ones of views finished since, which the next manifest will name, go up
ahead of it. A view the build is about to draw again is left out. So it is safe to run
while `bengaluru build` is still working or has stopped partway.

With --pyramids-only only the second set goes, and it stops before the index files, which
switch the live site over. With --until=HH:MM it starts no new pyramid after that local
time. With --prune it then removes from R2 the pyramids the manifest no longer names: a
rebuild of the whole city leaves 4 GB of them, and the bucket shares R2's free 10 GB with
the Manipur map's.

Needs R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY in .env: an R2 API token with Object Read
& Write on the bucket.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from bengaluru.areas import get_area
from bengaluru.detail import frames_fingerprint
from bengaluru.tile import pyramids_of

BUCKET = "bengaluru-tiles"
ACCOUNT_ID = "091e65b116deac24fcc274459b6fbde0"
ARGS = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
AREA = ARGS[0] if ARGS else "bbmp"
PYRAMIDS_ONLY = "--pyramids-only" in sys.argv
PRUNE = "--prune" in sys.argv
UNTIL = next((arg.removeprefix("--until=") for arg in sys.argv if arg.startswith("--until=")), None)
TILES = Path("out", AREA, "tiles").resolve()
DONE = Path("out", AREA, "uploaded-pyramids.json")
CACHE_CONTROL = "public, max-age=31536000, immutable"
INDEX_CACHE_CONTROL = "no-cache"
CONTENT_TYPES = {".webp": "image/webp", ".dzi": "application/xml"}
VIEWS_RECORD = TILES / "views.json"
INDEXES = ("manifest.json", "search.json", "flow.json", "metro.json", "credits.json")
TRANSFERS = 32
ATTEMPTS = 5


def rclone_env() -> dict[str, str]:
    """An `r2` remote for rclone, configured from the environment rather than a file."""
    missing = [
        name for name in ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY") if not os.environ.get(name)
    ]
    if missing:
        sys.exit(f"Set {' and '.join(missing)} in .env (see .env.example).")
    return {
        **os.environ,
        "RCLONE_CONFIG_R2_TYPE": "s3",
        "RCLONE_CONFIG_R2_PROVIDER": "Cloudflare",
        "RCLONE_CONFIG_R2_ACCESS_KEY_ID": os.environ["R2_ACCESS_KEY_ID"],
        "RCLONE_CONFIG_R2_SECRET_ACCESS_KEY": os.environ["R2_SECRET_ACCESS_KEY"],
        "RCLONE_CONFIG_R2_ENDPOINT": f"https://{ACCOUNT_ID}.r2.cloudflarestorage.com",
        # The token reaches objects only, so rclone must not try to create the bucket.
        "RCLONE_CONFIG_R2_NO_CHECK_BUCKET": "true",
    }  # fmt: skip


def copy(
    env: dict[str, str], source: Path, dest: str, content_type: str, cache_control: str, *flags: str
) -> None:
    subprocess.run(
        [
            "rclone", "copy", str(source), f"r2:{BUCKET}/{dest}",
            "--header-upload", f"Content-Type: {content_type}",
            "--header-upload", f"Cache-Control: {cache_control}",
            "--transfers", str(TRANSFERS), "--checkers", str(TRANSFERS),
            "--retries", str(ATTEMPTS), "--fast-list", "--stats-one-line", "--stats", "30s",
            *flags,
        ],
        env=env,
        check=True,
    )  # fmt: skip


def prune(env: dict[str, str], keep: set[str], done: set[str]) -> None:
    """Remove from R2 every pyramid the manifest does not name."""
    listed = subprocess.run(
        ["rclone", "lsf", f"r2:{BUCKET}/pyramid/", "--dirs-only"],
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    for name in sorted({line.strip("/") for line in listed.stdout.split()} - keep):
        subprocess.run(["rclone", "purge", f"r2:{BUCKET}/pyramid/{name}"], env=env, check=True)
        done.discard(name)
        DONE.write_text(json.dumps(sorted(done)))
        print(f"{name}: removed from R2", flush=True)


def deadline() -> datetime | None:
    """The next time the clock reads --until, today or tomorrow."""
    if not UNTIL:
        return None
    hour, minute = (int(part) for part in UNTIL.split(":"))
    now = datetime.now()
    stop = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return stop if stop > now else stop + timedelta(days=1)


def named_pyramids() -> set[str]:
    """The pyramids the manifest on disk names, each view's map and its layers: one whole build."""
    manifest = json.loads((TILES / INDEXES[0]).read_text())
    return pyramids_of(manifest["views"])


def main() -> None:
    stop = deadline()  # before touching the drive, so a slow first read can't move it a day
    env = rclone_env()
    done = set(json.loads(DONE.read_text())) if DONE.exists() else set()
    # A view drawn from older data or drawing code is due to be drawn again; skip it.
    inputs = frames_fingerprint(get_area(AREA))
    views = json.loads(VIEWS_RECORD.read_text())
    finished = pyramids_of(
        {name: view for name, view in views.items() if view.get("inputs") == inputs}
    )
    named = named_pyramids()
    wanted = finished if PYRAMIDS_ONLY else named | finished
    for pyramid in sorted((TILES / "pyramid").iterdir()):
        if pyramid.name in done or pyramid.name not in wanted:
            continue
        if stop and datetime.now() >= stop:
            print(f"stopped at {UNTIL}, {len(wanted & done)} of {len(wanted)} uploaded")
            return
        for suffix, content_type in CONTENT_TYPES.items():
            # Tiles are named by content and never rewritten, so a size match is enough.
            dest = f"pyramid/{pyramid.name}"
            copy(
                env,
                pyramid,
                dest,
                content_type,
                CACHE_CONTROL,
                "--include",
                f"*{suffix}",
                "--size-only",
            )
        done.add(pyramid.name)
        DONE.write_text(json.dumps(sorted(done)))
        print(f"{pyramid.name}: uploaded", flush=True)
    if PYRAMIDS_ONLY:
        print(f"{len(finished & done)} of {len(finished)} finished pyramids uploaded")
        return
    if not named <= done:
        sys.exit("R2 does not have every pyramid the manifest names; upload again.")
    # Always sent, since an index can change without changing size.
    indexes = [flag for name in INDEXES for flag in ("--include", name)]
    copy(
        env,
        TILES,
        "",
        "application/json",
        INDEX_CACHE_CONTROL,
        *indexes,
        "--ignore-times",
        "--max-depth",
        "1",
    )
    print("indexes: uploaded", flush=True)
    if PRUNE:
        prune(env, named | finished, done)


if __name__ == "__main__":
    main()
