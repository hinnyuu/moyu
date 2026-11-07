import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import { api } from "../api";
import type { Job } from "../api";
import {
  createQueueItems,
  deleteBlob,
  getBlob,
  loadQueue,
  saveQueue,
  uploadItem,
} from "../queue";
import type { QueueItem } from "../queue";
import { formatError } from "./Login";
import { HlsPreview } from "../components/HlsPreview";
import { packLocally, wasmCapabilities } from "../wasm";

function defaultTarget(): string {
  const value = new Date(Date.now() + 10 * 60 * 1000);
  const pad = (part: number) => String(part).padStart(2, "0");
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(
    value.getDate(),
  )}T${pad(value.getHours())}:${pad(value.getMinutes())}`;
}

export function UploadPage() {
  const [items, setItems] = useState<QueueItem[]>([]);
  const [busy, setBusy] = useState("");
  const [target, setTarget] = useState(defaultTarget());
  const [selected, setSelected] = useState("");
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [previewReady, setPreviewReady] = useState(true);
  const [wasmReady, setWasmReady] = useState(false);
  const [wasmInfo, setWasmInfo] = useState("");
  const [clientZip, setClientZip] = useState("");
  const pauseRef = useRef(false);
  const timezone = useMemo(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC",
    [],
  );

  useEffect(() => {
    void (async () => {
      const caps = await wasmCapabilities();
      if (caps) {
        setWasmReady(true);
        setWasmInfo(caps);
      }
    })();
  }, []);

  useEffect(() => {
    const restored = loadQueue().map((item) =>
      item.status === "uploading"
        ? { ...item, status: "paused" as const }
        : item,
    );
    setItems(restored);
    saveQueue(restored);
  }, []);

  function persist(next: QueueItem[]) {
    setItems(next);
    saveQueue(next);
  }

  function patch(id: string, changes: Partial<QueueItem>) {
    setItems((current) => {
      const next = current.map((item) =>
        item.id === id ? { ...item, ...changes } : item,
      );
      saveQueue(next);
      return next;
    });
  }

  async function addFiles(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []);
    event.target.value = "";
    if (!files.length) return;
    setError("");
    try {
      const created = await createQueueItems(files);
      setItems((current) => {
        const next = [...current, ...created];
        saveQueue(next);
        return next;
      });
    } catch (caught) {
      setError(formatError(caught));
    }
  }

  async function start(item: QueueItem): Promise<boolean> {
    const blob = await getBlob(item.id);
    if (!blob) {
      patch(item.id, { status: "error", error: "本地文件缓存丢失，请重新添加" });
      return false;
    }
    pauseRef.current = false;
    try {
      const result = await uploadItem(item, blob, api, {
        onUpdate: (next) => patch(next.id, next),
        shouldPause: () => pauseRef.current,
      });
      patch(result.id, result);
      return result.status === "done";
    } catch (caught) {
      patch(item.id, { status: "error", error: formatError(caught) });
      return false;
    }
  }

  async function startAll() {
    setBusy("all");
    setError("");
    const queue = items.filter(
      (item) => item.status === "pending" || item.status === "paused" || item.status === "error",
    );
    for (const item of queue) {
      if (pauseRef.current) break;
      await start(item);
    }
    setBusy("");
  }

  async function runOne(item: QueueItem) {
    setBusy(item.id);
    setError("");
    await start(item);
    setBusy("");
  }

  async function remove(item: QueueItem) {
    await deleteBlob(item.id);
    persist(items.filter((entry) => entry.id !== item.id));
    if (selected === item.assetId) setSelected("");
  }

  async function buildClientZip() {
    setError("");
    setClientZip("");
    const packed = [];
    for (const item of items) {
      const blob = await getBlob(item.id);
      if (!blob) continue;
      packed.push({ name: item.name, lastModified: item.lastModified, blob });
    }
    if (!packed.length) {
      setError("队列中没有可打包的文件");
      return;
    }
    const epoch = Math.floor(new Date(target).getTime() / 1000);
    const zip = await packLocally(packed, epoch);
    if (!zip) {
      setError("WASM 客户端不可用");
      return;
    }
    const url = URL.createObjectURL(zip);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "moyu-client.zip";
    anchor.click();
    URL.revokeObjectURL(url);
    setClientZip(`已生成 ${packed.length} 个条目的客户端 ZIP（仅 DOS 时间）`);
  }

  const done = items.filter((item) => item.status === "done" && item.assetId);
  const selectedItem = done.find((item) => item.assetId === selected);
  const progress = (item: QueueItem) =>
    item.size > 0 ? Math.round((item.offset / item.size) * 100) : 0;

  async function createJob() {
    if (!selected) return;
    setBusy("job");
    setError("");
    try {
      const epoch = Math.floor(new Date(target).getTime() / 1000);
      const created = await api.createJob({
        inputs: [
          {
            asset_id: selected,
            arcname: selectedItem?.name ?? "upload.bin",
          },
        ],
        target_epoch: epoch,
        timezone,
        output_name: "delivery.zip",
      });
      setJob(created);
    } catch (caught) {
      setError(formatError(caught));
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <div className="row" style={{ marginBottom: 12 }}>
          <div>
            <h2>上传队列</h2>
            <p className="hint">
              文件保存在浏览器 IndexedDB；刷新后可继续从服务器偏移量续传。
            </p>
          </div>
          <div className="spacer" />
          <label className="btn btn-primary">
            添加文件
            <input
              type="file"
              multiple
              onChange={(event) => void addFiles(event)}
              style={{ display: "none" }}
            />
          </label>
          <button
            className="btn"
            onClick={() => void startAll()}
            disabled={busy !== "" || items.length === 0}
          >
            开始/恢复全部
          </button>
          <button
            className="btn"
            onClick={() => {
              pauseRef.current = true;
            }}
            disabled={busy === ""}
          >
            暂停
          </button>
        </div>
        {error && <div className="error" style={{ marginBottom: 12 }}>{error}</div>}
        {items.length === 0 ? (
          <div className="empty">还没有待上传文件。</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>文件</th>
                <th>状态</th>
                <th>进度</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>
                    <div>{item.name}</div>
                    <div className="muted mono">{item.size} bytes</div>
                    {item.error && (
                      <div className="muted" style={{ fontSize: 12 }}>{item.error}</div>
                    )}
                  </td>
                  <td>
                    <span className={`badge ${item.status}`}>{item.status}</span>
                  </td>
                  <td>
                    <div className="row" style={{ gap: 8 }}>
                      <div className="progress" style={{ flex: 1 }}>
                        <span style={{ width: `${progress(item)}%` }} />
                      </div>
                      <span className="muted mono">{progress(item)}%</span>
                    </div>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    <button
                      className="btn"
                      onClick={() => void runOne(item)}
                      disabled={busy !== "" || item.status === "done"}
                    >
                      {item.status === "paused" ? "继续" : "上传"}
                    </button>
                    <button
                      className="btn btn-danger"
                      onClick={() => void remove(item)}
                      disabled={busy === item.id}
                    >
                      移除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {wasmReady && (
        <section className="card">
          <h2>客户端 ZIP（可选）</h2>
          <p className="hint">
            使用 WASM 在浏览器本地生成 STORE ZIP，只写 DOS mtime，不修改文件内部元数据。
          </p>
          <div className="row">
            <button
              className="btn"
              onClick={() => void buildClientZip()}
              disabled={items.length === 0 || busy !== ""}
            >
              本地生成 ZIP
            </button>
            <span className="muted mono">{wasmInfo}</span>
          </div>
          {clientZip && <div className="success" style={{ marginTop: 12 }}>{clientZip}</div>}
        </section>
      )}

      {done.length > 0 && (
        <section className="card">
          <h2>创建打包任务</h2>
          <p className="hint">选择一个已完成上传的资产，按目标时间生成交付 ZIP。</p>
          <div className="grid-2">
            <div className="media-preview">
              {selectedItem && previewReady ? (
                <img
                  src={api.previewUrl(selectedItem.assetId!, "thumb")}
                  alt={selectedItem.name}
                  onError={() => setPreviewReady(false)}
                />
              ) : (
                <span className="muted">选择资产后显示预览</span>
              )}
            </div>
            <div className="stack">
              <div className="field">
                <label htmlFor="asset">资产</label>
                <select
                  id="asset"
                  value={selected}
                  onChange={(event) => {
                    setSelected(event.target.value);
                    setPreviewReady(true);
                  }}
                >
                  <option value="">请选择</option>
                  {done.map((item) => (
                    <option key={item.assetId} value={item.assetId}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="target">目标完成时间（{timezone}）</label>
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
                  disabled={!selected || busy !== ""}
                >
                  {busy === "job" ? "创建中…" : "创建任务"}
                </button>
                {selectedItem && (
                  <a className="btn" href={api.downloadUrl(selectedItem.assetId!)}>
                    下载资产
                  </a>
                )}
              </div>
              {selected && <HlsPreview assetId={selected} />}
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
