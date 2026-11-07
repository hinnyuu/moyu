interface FFmpegInstance {
  loaded: boolean;
  load: (config: { coreURL: string; wasmURL: string }) => Promise<void>;
  writeFile: (name: string, data: Uint8Array) => Promise<void>;
  exec: (args: string[]) => Promise<number>;
  readFile: (name: string) => Promise<Uint8Array | string>;
  deleteFile: (name: string) => Promise<void>;
}

let instance: FFmpegInstance | null = null;
let loading: Promise<FFmpegInstance> | null = null;

export function ffmpegSupported(): boolean {
  return typeof window !== "undefined" && window.crossOriginIsolated === true;
}

async function getFFmpeg(): Promise<FFmpegInstance> {
  if (!ffmpegSupported()) {
    throw new Error("浏览器未启用 COOP/COEP 跨源隔离，无法使用 ffmpeg.wasm");
  }
  if (instance) return instance;
  if (!loading) {
    loading = (async () => {
      const { FFmpeg } = await import("@ffmpeg/ffmpeg");
      const ffmpeg = new FFmpeg() as unknown as FFmpegInstance;
      await ffmpeg.load({
        coreURL: "/ffmpeg/ffmpeg-core.js",
        wasmURL: "/ffmpeg/ffmpeg-core.wasm",
      });
      instance = ffmpeg;
      return ffmpeg;
    })();
  }
  return loading;
}

export async function transcodeVideo(
  file: Blob,
  filename: string,
  maxWidth = 640,
  maxHeight = 360,
): Promise<Blob> {
  const ffmpeg = await getFFmpeg();
  const { fetchFile } = await import("@ffmpeg/util");
  const extension = filename.includes(".")
    ? filename.slice(filename.lastIndexOf("."))
    : ".bin";
  const input = `input${extension}`;
  const output = "output.mp4";
  await ffmpeg.writeFile(input, await fetchFile(file));
  const scale = `scale=${maxWidth}:${maxHeight}:force_original_aspect_ratio=decrease`;
  let code = await ffmpeg.exec([
    "-i", input,
    "-vf", scale,
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-crf", "28",
    "-an",
    output,
  ]);
  if (code !== 0) {
    code = await ffmpeg.exec([
      "-i", input,
      "-vf", scale,
      "-c:v", "mpeg4",
      "-q:v", "6",
      "-an",
      output,
    ]);
  }
  if (code !== 0) {
    await ffmpeg.deleteFile(input);
    throw new Error("ffmpeg.wasm 视频转码失败");
  }
  const data = await ffmpeg.readFile(output);
  await ffmpeg.deleteFile(input);
  await ffmpeg.deleteFile(output);
  const bytes = typeof data === "string" ? new TextEncoder().encode(data) : data;
  return new Blob([bytes as unknown as BlobPart], { type: "video/mp4" });
}
