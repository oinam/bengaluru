import { createReadStream, statSync } from "node:fs";
import { extname, join, normalize } from "node:path";
import process from "node:process";
import { defineConfig } from "vite";

// `vite preview` serves the built map, whose tiles are linked into dist; the dev server
// serves them straight from the render output.
// MAP_AREA picks another rendered area, such as `vidhana-soudha` or `central`, instead of
// `bbmp`, the whole city.
const TILES = join(import.meta.dirname, "../out", process.env.MAP_AREA ?? "bbmp", "tiles");
const TYPES = {
  ".json": "application/json",
  ".webp": "image/webp",
  ".dzi": "application/xml",
  ".xml": "application/xml",
};

const localTiles = {
  name: "local-tiles",
  configureServer(server) {
    server.middlewares.use("/tiles", (request, response, next) => {
      const path = normalize(join(TILES, decodeURIComponent(request.url.split("?")[0])));
      if (!path.startsWith(TILES)) {
        next();
        return;
      }
      try {
        if (!statSync(path).isFile()) {
          next();
          return;
        }
      } catch {
        next();
        return;
      }
      response.setHeader("Content-Type", TYPES[extname(path)] ?? "application/octet-stream");
      createReadStream(path).pipe(response);
    });
  },
};

// Ports beside the Manipur map's 8645 and 8644, so both can run at once.
export default defineConfig({
  plugins: [localTiles],
  server: { port: 8655 },
  preview: { port: 8654 },
});
