import type { Asset, UploadSession } from "./api";

export type UploadStatus = "pending" | "uploading" | "paused" | "done" | "error";

export interface QueueItem {
  id: string;
  name: string;
  size: number;
  type: string;
  lastModified: number;
  status: UploadStatus;
  offset: number;
  sessionId?: string;
  assetId?: string;
  error?: string;
}

export interface QueueApi {
  createUpload(filename: string, size: number, mediaType: string): Promise<UploadSession>;
  getUpload(id: string): Promise<{ id: string; offset: number; size: number; status?: string }>;
  appendChunk(id: string, offset: number, chunk: Blob): Promise<number>;
  finishUpload(id: string): Promise<Asset>;
}

export interface UploadHooks {
  onUpdate(item: QueueItem): void;
  shouldPause(): boolean;
}

export const QUEUE_KEY = "moyu-upload-queue";
export const CHUNK_SIZE = 8 * 1024 * 1024;

export function loadQueue(): QueueItem[] {
  try {
    const text = localStorage.getItem(QUEUE_KEY);
    if (!text) return [];
    const parsed = JSON.parse(text) as QueueItem[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function saveQueue(items: QueueItem[]) {
  try {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(items));
  } catch {
    /* storage unavailable */
  }
}

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("moyu-uploads", 1);
    request.onupgradeneeded = () => {
      request.result.createObjectStore("blobs");
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function putBlob(id: string, blob: Blob) {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction("blobs", "readwrite");
    transaction.objectStore("blobs").put(blob, id);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
  db.close();
}

export async function getBlob(id: string): Promise<Blob | null> {
  const db = await openDb();
  const blob = await new Promise<Blob | null>((resolve, reject) => {
    const transaction = db.transaction("blobs", "readonly");
    const request = transaction.objectStore("blobs").get(id);
    request.onsuccess = () => resolve((request.result as Blob) ?? null);
    request.onerror = () => reject(request.error);
  });
  db.close();
  return blob;
}

export async function deleteBlob(id: string) {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction("blobs", "readwrite");
    transaction.objectStore("blobs").delete(id);
    transaction.oncomplete = () => resolve();
    transaction.onerror = () => reject(transaction.error);
  });
  db.close();
}

export async function createQueueItems(files: File[]): Promise<QueueItem[]> {
  const items = files.map((file) => ({
    id: crypto.randomUUID(),
    name: file.name,
    size: file.size,
    type: file.type || "application/octet-stream",
    lastModified: file.lastModified,
    status: "pending" as const,
    offset: 0,
  }));
  for (const [index, item] of items.entries()) {
    await putBlob(item.id, files[index]);
  }
  return items;
}

export async function uploadItem(
  item: QueueItem,
  blob: Blob,
  api: QueueApi,
  hooks: UploadHooks,
  chunkSize = CHUNK_SIZE,
): Promise<QueueItem> {
  let current = { ...item };
  let offset = current.offset;
  if (!current.sessionId) {
    const session = await api.createUpload(current.name, current.size, current.type);
    current.sessionId = session.id;
    offset = session.offset;
  } else {
    const session = await api.getUpload(current.sessionId);
    offset = session.offset;
    if (offset >= blob.size) {
      const asset = await api.finishUpload(current.sessionId);
      current = { ...current, status: "done", offset, assetId: asset.id };
      hooks.onUpdate(current);
      return current;
    }
  }
  current = { ...current, status: "uploading", offset };
  hooks.onUpdate(current);

  while (offset < blob.size) {
    if (hooks.shouldPause()) {
      current = { ...current, status: "paused", offset };
      hooks.onUpdate(current);
      return current;
    }
    const chunk = blob.slice(offset, offset + chunkSize);
    offset = await api.appendChunk(current.sessionId as string, offset, chunk);
    current = { ...current, offset };
    hooks.onUpdate(current);
  }

  const asset = await api.finishUpload(current.sessionId as string);
  current = { ...current, status: "done", offset, assetId: asset.id };
  hooks.onUpdate(current);
  return current;
}
