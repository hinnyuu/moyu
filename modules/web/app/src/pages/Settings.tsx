import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import type { ConfigSnapshot } from "../api";
import { formatError } from "./Login";

const MODULES = [
  "global",
  "gateway",
  "api",
  "worker",
  "preview",
  "storage",
  "uploads",
];

export function SettingsPage() {
  const [snapshot, setSnapshot] = useState<ConfigSnapshot | null>(null);
  const [selected, setSelected] = useState("worker");
  const [text, setText] = useState("");
  const [revision, setRevision] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    try {
      const data = await api.config();
      setSnapshot(data);
      setError("");
      return data;
    } catch (caught) {
      setError(formatError(caught));
      return null;
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (!snapshot) return;
    const data =
      selected === "global" ? snapshot.global : snapshot.modules[selected];
    setText(JSON.stringify(data ?? {}, null, 2));
    setRevision(snapshot.revisions[selected] ?? "");
    setMessage("");
  }, [selected, snapshot]);

  const degraded = useMemo(() => snapshot?.degraded ?? [], [snapshot]);

  async function save() {
    let patch: Record<string, unknown>;
    try {
      const parsed = JSON.parse(text) as unknown;
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("配置必须是 JSON 对象");
      }
      patch = parsed as Record<string, unknown>;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : String(caught));
      return;
    }
    setPending(true);
    setError("");
    setMessage("");
    try {
      const result = await api.saveConfig(selected, patch, revision);
      setRevision(result.revision);
      setMessage(`已保存，revision ${result.revision.slice(0, 12)}`);
      await load();
    } catch (caught) {
      setError(formatError(caught));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="stack">
      {degraded.length > 0 && (
        <div className="error">
          以下模块当前使用 last-known-good：{degraded.join(", ")}
        </div>
      )}
      <section className="card">
        <h2>运行配置</h2>
        <p className="hint">
          保存前会做 schema 校验；revision 不匹配会拒绝覆盖。部署配置不在这里修改。
        </p>
        <div className="row" style={{ marginBottom: 12 }}>
          <div className="field" style={{ flex: 0, minWidth: 180 }}>
            <label htmlFor="module">模块</label>
            <select
              id="module"
              value={selected}
              onChange={(event) => setSelected(event.target.value)}
            >
              {MODULES.filter(
                (name) => name === "global" || snapshot?.modules[name],
              ).map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>revision</label>
            <input className="mono" readOnly value={revision} />
          </div>
        </div>
        <div className="field">
          <label htmlFor="config-json">JSON</label>
          <textarea
            id="config-json"
            spellCheck={false}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
        </div>
        {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}
        {message && (
          <div className="success" style={{ marginTop: 12 }}>{message}</div>
        )}
        <div className="row" style={{ marginTop: 12 }}>
          <button
            className="btn btn-primary"
            onClick={() => void save()}
            disabled={pending}
          >
            {pending ? "保存中…" : "校验并保存"}
          </button>
          <button
            className="btn"
            onClick={() => snapshot && setSnapshot({ ...snapshot })}
          >
            重置编辑
          </button>
        </div>
      </section>
    </div>
  );
}