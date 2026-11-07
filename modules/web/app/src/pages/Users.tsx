import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api";
import type { User } from "../api";
import { formatError } from "./Login";

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("operator");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    try {
      setUsers(await api.users());
      setError("");
    } catch (caught) {
      setError(formatError(caught));
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function create(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    setMessage("");
    try {
      await api.createUser(username, password, role);
      setUsername("");
      setPassword("");
      setMessage("用户已创建");
      await load();
    } catch (caught) {
      setError(formatError(caught));
    } finally {
      setPending(false);
    }
  }

  async function remove(user: User) {
    if (!window.confirm(`删除用户 ${user.username}？`)) return;
    try {
      await api.deleteUser(user.username);
      await load();
    } catch (caught) {
      setError(formatError(caught));
    }
  }

  async function reset(user: User) {
    const next = window.prompt(`为 ${user.username} 设置新密码（至少 8 位）`);
    if (!next) return;
    try {
      await api.resetUserPassword(user.username, next);
      setMessage(`已重置 ${user.username} 的密码`);
    } catch (caught) {
      setError(formatError(caught));
    }
  }

  return (
    <div className="stack">
      <section className="card">
        <h2>用户</h2>
        <p className="hint">管理员可创建/删除用户并重置密码；operator 只能使用任务与上传。</p>
        <form className="row" onSubmit={create}>
          <div className="field">
            <label htmlFor="new-username">用户名</label>
            <input
              id="new-username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="new-password">初始密码</label>
            <input
              id="new-password"
              type="password"
              minLength={8}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </div>
          <div className="field" style={{ flex: 0, minWidth: 140 }}>
            <label htmlFor="new-role">角色</label>
            <select id="new-role" value={role} onChange={(event) => setRole(event.target.value)}>
              <option value="operator">operator</option>
              <option value="admin">admin</option>
            </select>
          </div>
          <button className="btn btn-primary" type="submit" disabled={pending}>
            创建
          </button>
        </form>
        {error && <div className="error" style={{ marginTop: 12 }}>{error}</div>}
        {message && <div className="success" style={{ marginTop: 12 }}>{message}</div>}
      </section>

      <section className="card">
        {users.length === 0 ? (
          <div className="empty">没有用户。</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>用户</th>
                <th>角色</th>
                <th>创建时间</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.username}>
                  <td>{user.username}</td>
                  <td>
                    <span className={`badge ${user.role === "admin" ? "succeeded" : "queued"}`}>
                      {user.role}
                    </span>
                  </td>
                  <td className="muted">{new Date(user.created_at).toLocaleString()}</td>
                  <td style={{ textAlign: "right" }}>
                    <button className="btn" onClick={() => void reset(user)}>
                      重置密码
                    </button>
                    <button className="btn btn-danger" onClick={() => void remove(user)}>
                      删除
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
