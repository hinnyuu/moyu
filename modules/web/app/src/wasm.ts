interface WasmModule {
  default: () => Promise<void>;
  capabilities: () => string;
  PackBuilder: new () => {
    add_file(name: string, mtimeNs: bigint, data: Uint8Array): void;
    finish(targetEpoch: bigint, utcOffsetSeconds: number): Uint8Array;
    free?: () => void;
  };
  transcode?: (
    data: Uint8Array,
    maxWidth: number,
    maxHeight: number,
    format: string,
    quality: number,
  ) => Uint8Array;
}

let cached: Promise<WasmModule | null> | null = null;

export function loadWasmClient(): Promise<WasmModule | null> {
  if (!cached) {
    cached = (async () => {
      try {
        const specifier = "/wasm/moyu_wasm_client.js";
        const module = (await import(/* @vite-ignore */ specifier)) as WasmModule;
        await module.default();
        return module;
      } catch {
        return null;
      }
    })();
  }
  return cached;
}

export async function wasmCapabilities(): Promise<string | null> {
  const module = await loadWasmClient();
  if (!module) return null;
  try {
    return module.capabilities();
  } catch {
    return null;
  }
}

export async function transcodeImage(
  file: Blob,
  maxWidth = 512,
  maxHeight = 512,
): Promise<Blob | null> {
  const module = await loadWasmClient();
  if (!module?.transcode) return null;
  try {
    const bytes = new Uint8Array(await file.arrayBuffer());
    const output = module.transcode(bytes, maxWidth, maxHeight, "jpeg", 85);
    return new Blob([output as unknown as BlobPart], { type: "image/jpeg" });
  } catch {
    return null;
  }
}

export async function packLocally(
  files: Array<{ name: string; lastModified: number; blob: Blob }>,
  targetEpoch: number,
): Promise<Blob | null> {
  const module = await loadWasmClient();
  if (!module) return null;
  const builder = new module.PackBuilder();
  try {
    for (const file of files) {
      const bytes = new Uint8Array(await file.blob.arrayBuffer());
      builder.add_file(
        file.name,
        BigInt(Math.floor(file.lastModified) * 1_000_000),
        bytes,
      );
    }
    const data = builder.finish(BigInt(targetEpoch), 0);
    return new Blob([data as unknown as BlobPart], { type: "application/zip" });
  } finally {
    builder.free?.();
  }
}
