import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const source = path.join(root, "node_modules", "@ffmpeg", "core", "dist", "esm");
const target = path.join(root, "public", "ffmpeg");
fs.mkdirSync(target, { recursive: true });
for (const name of ["ffmpeg-core.js", "ffmpeg-core.wasm"]) {
  fs.copyFileSync(path.join(source, name), path.join(target, name));
}
console.log(`ffmpeg core copied to ${target}`);
