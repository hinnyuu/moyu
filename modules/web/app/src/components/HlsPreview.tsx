import { useEffect, useRef, useState } from "react";

interface Props {
  assetId: string;
}

export function HlsPreview({ assetId }: Props) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [active, setActive] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!active || !videoRef.current) return;
    const video = videoRef.current;
    const url = `/api/v1/previews/${assetId}/hls/index.m3u8`;
    let disposed = false;
    let destroy: (() => void) | undefined;
    setError("");

    async function start() {
      if (video.canPlayType("application/vnd.apple.mpegurl")) {
        video.src = url;
        return;
      }
      try {
        const { default: Hls } = await import("hls.js");
        if (disposed) return;
        if (!Hls.isSupported()) {
          setError("浏览器不支持 HLS");
          return;
        }
        const hls = new Hls({ enableWorker: true });
        hls.loadSource(url);
        hls.attachMedia(video);
        hls.on(Hls.Events.ERROR, (_event, data) => {
          if (data.fatal) setError("HLS 不可用（可能不是视频或 ffmpeg 未启用）");
        });
        destroy = () => hls.destroy();
      } catch {
        setError("HLS 播放器加载失败");
      }
    }

    void start();
    return () => {
      disposed = true;
      destroy?.();
    };
  }, [active, assetId]);

  return (
    <div className="stack">
      <div className="row">
        <button className="btn" onClick={() => setActive(!active)}>
          {active ? "关闭 HLS 预览" : "视频预览（HLS）"}
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      {active && (
        <video
          ref={videoRef}
          controls
          muted
          playsInline
          style={{ width: "100%", maxHeight: 360, borderRadius: 10, background: "#000" }}
        />
      )}
    </div>
  );
}
