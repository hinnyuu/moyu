import { useEffect, useState } from "react";
import { api } from "./api";
import type { Session } from "./api";
import { JobsPage } from "./pages/Jobs";
import { LoginPage } from "./pages/Login";
import { SettingsPage } from "./pages/Settings";
import { UploadPage } from "./pages/Upload";
import { applyTheme, loadPref, nextPref, themeLabel } from "./theme";
import type { ThemePref } from "./theme";

type View = "jobs" | "upload" | "settings";
type Phase = "loading" | "login" | "ready";

export function App() {
  const [phase, setPhase] = useState<Phase>("loading");
  const [configured, setConfigured] = useState(false);
  const [session, setSession] = useState<Session | null>(null);
  const [view, setView] = useState<View>("jobs");
  const [theme, setTheme] = useState<ThemePref>(loadPref());

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  useEffect(() => {
    if (theme !== "system") return;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const listener = () => applyTheme("system");
    media.addEventListener("change", listener);
    return () => media.removeEventListener("change", listener);
  }, [theme]);

  useEffect(() => {
    async function boot() {
      try {
        const health = await api.health();
        setConfigured(health.configured);
        try {
          const current = await api.session();
          setSession(current);
          setPhase("ready");
        } catch {
          setPhase("login");
        }
      } catch {
        setPhase("login");
      }
    }
    void boot();
  }, []);

  useEffect(() => {
    const handler = () => {
      setSession(null);
      setPhase("login");
    };
    window.addEventListener("moyu:unauthorized", handler);
    return () => window.removeEventListener("moyu:unauthorized", handler);
  }, []);

  async function logout() {
    try {
      await api.logout();
    } catch {
      /* session may already be gone */
    }
    setSession(null);
    setPhase("login");
  }

  if (phase === "loading") {
    return (
      <div className="login-wrap">
        <div className="card login-card">
          <h1>moyu</h1>
          <p className="sub">正在检查会话…</p>
        </div>
      </div>
    );
  }

  if (phase === "login") {
    return (
      <LoginPage
        configured={configured}
        onLogin={(next) => {
          setSession(next);
          setConfigured(true);
          setPhase("ready");
        }}
      />
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          moyu <small>delivery</small>
        </div>
        <nav className="nav">
          <button
            className={view === "jobs" ? "active" : ""}
            onClick={() => setView("jobs")}
          >
            任务
          </button>
          <button
            className={view === "upload" ? "active" : ""}
            onClick={() => setView("upload")}
          >
            上传
          </button>
          <button
            className={view === "settings" ? "active" : ""}
            onClick={() => setView("settings")}
          >
            配置
          </button>
        </nav>
        <div className="topbar-actions">
          <button
            className="btn btn-ghost theme-toggle"
            onClick={() => setTheme(nextPref(theme))}
            title="切换主题"
          >
            主题：{themeLabel(theme)}
          </button>
          <span className="muted">{session?.username}</span>
          <button className="btn" onClick={() => void logout()}>
            退出
          </button>
        </div>
      </header>
      <main className="container">
        {view === "jobs" && <JobsPage />}
        {view === "upload" && <UploadPage />}
        {view === "settings" && <SettingsPage />}
      </main>
    </div>
  );
}