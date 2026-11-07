let csrfToken = "";

export class ApiError extends Error {
  status: number;
  code: string;
  details: string[];
  module: string;

  constructor(status: number, body: Record<string, unknown>) {
    const message =
      typeof body.message === "string" ? body.message : `请求失败 (${status})`;
    super(message);
    this.status = status;
    this.code = typeof body.code === "string" ? body.code : "error";
    this.details = Array.isArray(body.details) ? body.details.map(String) : [];
    this.module = typeof body.module === "string" ? body.module : "";
  }
}

export function setCsrf(token: string) {
  csrfToken = token;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (init.method && init.method !== "GET" && init.method !== "HEAD") {
    headers.set("X-CSRF-Token", csrfToken);
  }
  const response = await fetch(path, {
    credentials: "same-origin",
    ...init,
    headers,
  });
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  let body: Record<string, unknown> = {};
  if (text) {
    try {
      body = JSON.parse(text) as Record<string, unknown>;
    } catch {
      body = { message: text };
    }
  }
  if (!response.ok) {
    if (response.status === 401) {
      window.dispatchEvent(new Event("moyu:unauthorized"));
    }
    throw new ApiError(response.status, body);
  }
  return body as T;
}

export interface Health {
  status: string;
  configured: boolean;
}

export interface Session {
  username: string;
  role: string;
  csrf: string;
  expires_at: number;
}

export interface UploadSession {
  id: string;
  offset: number;
  size: number;
  chunk_size?: number;
  tus_url?: string;
}

export interface Asset {
  id: string;
  original_name: string;
  size: number;
  sha256: string;
  media_type: string;
  created_at: string;
}

export interface Job {
  id: string;
  status: string;
  progress: number;
  error: string;
  created_at: string;
  updated_at: string;
  request: Record<string, unknown>;
}

export interface User {
  username: string;
  role: string;
  created_at: string;
}

export interface ConfigSnapshot {
  global: Record<string, unknown>;
  modules: Record<string, Record<string, unknown>>;
  revisions: Record<string, string>;
  degraded: string[];
}

export const api = {
  health: () => request<Health>("/api/v1/health"),
  session: async () => {
    const session = await request<Session>("/api/v1/auth/session");
    setCsrf(session.csrf);
    return session;
  },
  login: async (password: string, bootstrapToken?: string) => {
    await request<void>("/api/v1/auth/session", {
      method: "POST",
      body: JSON.stringify(
        bootstrapToken
          ? { password, bootstrap_token: bootstrapToken }
          : { password },
      ),
    });
    return api.session();
  },
  logout: () =>
    request<void>("/api/v1/auth/session", { method: "DELETE" }),
  users: () => request<User[]>("/api/v1/users"),
  createUser: (username: string, password: string, role: string) =>
    request<User>("/api/v1/users", {
      method: "POST",
      body: JSON.stringify({ username, password, role }),
    }),
  deleteUser: (username: string) =>
    request<void>(`/api/v1/users/${username}`, { method: "DELETE" }),
  resetUserPassword: (username: string, password: string) =>
    request<void>(`/api/v1/users/${username}/password`, {
      method: "POST",
      body: JSON.stringify({ password }),
    }),
  config: () => request<ConfigSnapshot>("/api/v1/config"),
  saveConfig: (module: string, patch: unknown, revision: string) =>
    request<{ config: Record<string, unknown>; revision: string }>(
      `/api/v1/config/${module}`,
      {
        method: "PUT",
        body: JSON.stringify({ patch, revision }),
      },
    ),
  jobs: () => request<Job[]>("/api/v1/jobs?limit=50"),
  createJob: (payload: Record<string, unknown>) =>
    request<Job>("/api/v1/jobs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  cancelJob: (id: string) =>
    request<Job>(`/api/v1/jobs/${id}`, { method: "DELETE" }),
  createUpload: (filename: string, size: number, mediaType: string) =>
    request<UploadSession>("/api/v1/uploads", {
      method: "POST",
      body: JSON.stringify({
        filename,
        size,
        media_type: mediaType || "application/octet-stream",
      }),
    }),
  getUpload: (id: string) =>
    request<{ id: string; offset: number; size: number; status?: string }>(
      `/api/v1/uploads/${id}`,
    ),
  appendChunk: async (id: string, offset: number, chunk: Blob) => {
    const response = await fetch(`/api/v1/uploads/${id}`, {
      method: "PATCH",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/offset+octet-stream",
        "Upload-Offset": String(offset),
        "X-CSRF-Token": csrfToken,
      },
      body: chunk,
    });
    if (response.status !== 204) {
      const text = await response.text();
      let body: Record<string, unknown> = {};
      try {
        body = JSON.parse(text) as Record<string, unknown>;
      } catch {
        body = { message: text };
      }
      throw new ApiError(response.status, body);
    }
    return Number(response.headers.get("Upload-Offset") || offset + chunk.size);
  },
  finishUpload: (id: string) =>
    request<Asset>(`/api/v1/uploads/${id}/finish`, { method: "POST" }),
  previewUrl: (assetId: string, profile = "thumb") =>
    `/api/v1/previews/${assetId}/${profile}`,
  downloadUrl: (assetId: string) => `/api/v1/assets/${assetId}/download`,
};