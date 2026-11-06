import { useState } from "react";
import type { FormEvent } from "react";
import { ApiError, api } from "../api";
import type { Session } from "../api";

interface LoginProps {
  configured: boolean;
  onLogin: (session: Session) => void;
}

export function LoginPage({ configured, onLogin }: LoginProps) {
  const [password, setPassword] = useState("");
  const [bootstrap, setBootstrap] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      const session = await api.login(
        password,
        configured ? undefined : bootstrap,
      );
      setPassword("");
      setBootstrap("");
      onLogin(session);
    } catch (caught) {
      setError(formatError(caught));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <div>
          <h1>moyu</h1>
          <p className="sub">
            {configured
              ? "输入管理员密码继续。"
              : "首次启动：使用 bootstrap token 设置管理员密码。"}
          </p>
        </div>
        {!configured && (
          <div className="field">
            <label htmlFor="bootstrap">Bootstrap token</label>
            <input
              id="bootstrap"
              type="password"
              autoComplete="one-time-code"
              value={bootstrap}
              onChange={(event) => setBootstrap(event.target.value)}
              required
            />
          </div>
        )}
        <div className="field">
          <label htmlFor="password">
            {configured ? "密码" : "设置管理员密码（至少 8 位）"}
          </label>
          <input
            id="password"
            type="password"
            autoComplete={configured ? "current-password" : "new-password"}
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </div>
        {error && <div className="error">{error}</div>}
        <button className="btn btn-primary" type="submit" disabled={pending}>
          {pending ? "登录中…" : configured ? "登录" : "初始化并登录"}
        </button>
      </form>
    </div>
  );
}

export function formatError(caught: unknown): string {
  if (caught instanceof ApiError) {
    if (caught.details.length) {
      return `${caught.code}: ${caught.message} (${caught.details.join("; ")})`;
    }
    return `${caught.code}: ${caught.message}`;
  }
  if (caught instanceof Error) return caught.message;
  return String(caught);
}