import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { api } from "../api";
import type { Asset, Job } from "../api";
import { formatError } from "./Login";

const CHUNK_SIZE = 8 * 1024 * 1024;

function defaultTarget(): string {
  const value = new Date(Date.now() + 10 * 60 * 1000);
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(
    value.getDate(),
  )}T${pad(value.getHours())}:${pad(value.getMinutes())}`;
}

export function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const [asset, setAsset] = useState<Asset | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [target, setTarget] = useState(defaultTarget());
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [previewReady, setPreviewReady] = useState(true);

  const timezone = useMemo(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    [],
  );

  function pick(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
    setAsset(null);
    setJob(null);
    setProgress(0);
    setPreviewReady(true);
  }

  async function upload() {
    if (!file) return;
    setPending(true);
    setError("");
    setAsset(null);
    setJob(null);
    setProgress(0);
    try {
      const session = await api.createUpload(file.name, file.size, file.type);
      let offset = session.offset;
      while (offset < file.size) {
        const chunk = file.slice(offset, offset + CHUNK_SIZE);
        offset = await api.appendChunk(session.id, offset, chunk);
        setProgress(Math.round((offset / file.size) * 100));
      }
      const finished = await api.finishUpload(session.id);
      setAsset(finished);
      setProgress(100);
    } catch (caught) {
      setError(formatError(caught));
    } finally {
      setPending(false);
    }
  }

  async function createJob() {
    if (!asset) return;
    setPending(true);
    setError("");
    try {
      const epoch = Math.floor(new Date(target).getTime() / 1000);
      const created = await api.createJob({
        inputs: [{ asset_id: asset.id, arcname: asset.original_name }],
        target_epoch: epoch,
        timezone,
        output_name: "delivery.zip",
      });
      setJob(created);
    } catch (caught) {
      setError(formatError(caught));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <h2>上传文件</h2>
        <p className="hint">
          分片上传，完成后登记为资产；随后可以按目标时间创建打包任务。
        </p>
        <div className="row">
          <div className="field">
            <label htmlFor="file">选择文件</label>
            <input id="file" type="file" onChange={pick} disabled={pending} />
          </div>
          <button
            className="btn btn-primary"
            onClick={() => void upload()}
            disabled={!file || pending}
          >
            {pending ? "处理中…" : "上传"}
          </button>
        </div>
        {progress > 0 && (
          <div className="row" style={{ marginTop: 12 }}>
            <div className="progress" style={{ flex: 1 }}>
              <span style={{ width: `${progress}%` }} />
            </div>
            <span className="muted mono">{progress}%</span>
          </div>
        )}
        {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}
      </section>

      {asset && (
        <section className="card">
          <h2>资产已登记</h2>
          <p className="hint">
            {asset.original_name} · {asset.size} bytes ·{" "}
            <span className="mono">{asset.id.slice(0, 12)}</span>
          </p>
          <div className="grid-2">
            <div className="media-preview">
              {previewReady ? (
                <img
                  src={api.previewUrl(asset.id)}
                  alt={asset.original_name}
                  onError={() => setPreviewReady(false)}
                />
              ) : (
                <span className="muted">该格式暂不支持预览</span>
              )}
            </div>
            <div className="stack">
              <div className="field">
                <label htmlFor="target">目标完成时间（本地时区 {timezone}）</label>
                <input
                  id="target"
                  type="datetime-local"
                  value={target}
                  onChange={(event) => setTarget(event.target.value)}
                />
              </div>
              <div className="row">
                <button
                  className="btn btn-primary"
                  onClick={() => void createJob()}
                  disabled={pending}
                >
                  创建打包任务
                </button>
                <a className="btn" href={api.downloadUrl(asset.id)}>
                  下载资产
                </a>
              </div>
              {job && (
                <div className="success">
                  任务 {job.id.slice(0, 12)} 已创建，状态 {job.status}。
                </div>
              )}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}