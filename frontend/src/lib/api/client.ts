const BASE = '/api';
const TOKEN_STORAGE_KEY = 'pdfbs_token';

export class ApiClientError extends Error {
  code: string;
  hint: string | null;

  constructor(message: string, code = 'API_ERROR', hint: string | null = null) {
    super(message);
    this.name = 'ApiClientError';
    this.code = code;
    this.hint = hint;
  }
}

/** El token llega en `#token=…`, se guarda en sessionStorage y se limpia de la URL. */
export function readToken(): string | null {
  if (typeof window === 'undefined') return null;
  const hash = window.location.hash;
  if (hash.startsWith('#token=')) {
    const token = decodeURIComponent(hash.slice('#token='.length));
    try {
      window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    } catch {
      /* sessionStorage puede estar bloqueado; igual se usa el token en memoria */
    }
    window.history.replaceState(null, '', window.location.pathname + window.location.search);
    return token;
  }
  try {
    return window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

let memoryToken = readToken();

export function setToken(token: string | null): void {
  memoryToken = token;
  if (typeof window === 'undefined') return;
  try {
    if (token) window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    else window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* noop */
  }
}

export function authHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra);
  if (memoryToken) headers.set('X-PDFBS-Token', memoryToken);
  return headers;
}

export async function parseError(res: Response): Promise<ApiClientError> {
  const text = await res.text();
  try {
    const payload = JSON.parse(text) as { detail?: { code?: string; message?: string; hint?: string | null } };
    const detail = payload.detail;
    if (detail && typeof detail === 'object') {
      return new ApiClientError(detail.message || res.statusText, detail.code, detail.hint ?? null);
    }
  } catch {
    /* respuesta no JSON */
  }
  return new ApiClientError(text || res.statusText, `HTTP_${res.status}`);
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    ...init,
    headers: authHeaders(init?.headers),
  });
  if (!res.ok) throw await parseError(res);
  return res.json() as Promise<T>;
}

export async function requestBinary(path: string, init?: RequestInit): Promise<Blob> {
  const res = await fetch(BASE + path, { ...init, headers: authHeaders(init?.headers) });
  if (!res.ok) throw await parseError(res);
  return res.blob();
}

export function apiBase(): string {
  return BASE;
}
