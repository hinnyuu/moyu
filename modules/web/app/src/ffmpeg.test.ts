import { describe, expect, it } from "vitest";
import { ffmpegSupported, transcodeVideo } from "./ffmpeg";

describe("ffmpeg fallback", () => {
  it("reports unsupported outside browsers", () => {
    expect(ffmpegSupported()).toBe(false);
  });

  it("rejects without cross-origin isolation", async () => {
    await expect(
      transcodeVideo(new Blob([new Uint8Array(4)]), "clip.mp4"),
    ).rejects.toThrow(/COOP\/COEP/);
  });
});
