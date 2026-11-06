import { useEffect, useState } from "react";
import { api } from "../api";
import type { Job } from "../api";
import { formatError } from "./Login";

const FINAL = new Set(["succeeded", "failed", "canceled"]);

export function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [error, setError] = useState("");
  const [pending, setPending] = useState("");

  async function refresh() {
    try {
      setJobs(await api.jobs());
      setError("");
    } catch (caught) {
      setError(formatError(caught));
    }
  }

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5000);
    return () => window.clearInterval(timer);
  }, []);

  async function cancel(job: Job) {
    setPending(job.id);
    try {
      await api.cancelJob(job.id);
      await refresh();
    } catch (caught) {
      setError(formatError(caught));
    } finally {
      setPending("");
    }
  }

  return (
    <section className="card">
      <div className="row" style={{ marginBottom: 12 }}>
        <div>
          <h2>任务</h2>
          <p className="hint">每 5 秒刷新一次；打包由后台 worker 执行。</p>
        </div>
        <div className="spacer" />
        <button className="btn btn-ghost" onClick={() => void refresh()}>
          刷新
        </button>
      </div>
      {error && <div className="error" style={{ marginBottom: 12 }}>{error}</div>}
      {jobs.length === 0 ? (
        <div className="empty">还没有任务。先在上传页上传文件并创建任务。</div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>任务</th>
              <th>状态</th>
              <th>创建时间</th>
              <th>进度</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id}>
                <td>
                  <div className="mono">{job.id.slice(0, 12)}</div>
                  {job.error && (
                    <div className="muted" style={{ fontSize: 12 }}>
                      {job.error}
                    </div>
                  )}
                </td>
                <td>
                  <span className={`badge ${job.status}`}>{job.status}</span>
                </td>
                <td className="muted">{new Date(job.created_at).toLocaleString()}</td>
                <td>
                  <div className="row" style={{ gap: 8 }}>
                    <div className="progress" style={{ flex: 1 }}>
                      <span style={{ width: `${job.progress}%` }} />
                    </div>
                    <span className="muted mono">{job.progress}%</span>
                  </div>
                </td>
                <td style={{ textAlign: "right" }}>
                  <button
                    className="btn btn-danger"
                    disabled={FINAL.has(job.status) || pending === job.id}
                    onClick={() => void cancel(job)}
                  >
                    取消
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}