// Where the tile pyramids and their index files live: out/<area>/tiles, served by the dev
// server and linked into dist for local builds; VITE_TILE_BASE names another place.
export const TILE_BASE = (import.meta.env.VITE_TILE_BASE as string | undefined) ?? "tiles/";
