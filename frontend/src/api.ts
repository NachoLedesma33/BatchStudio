const BASE = '/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, init);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  listDocuments: () => request<{ documents: any[] }>('/documents'),
  uploadFiles: async (files: File[]) => {
    const form = new FormData();
    files.forEach((f) => form.append('files', f));
    const res = await fetch(BASE + '/files/upload', { method: 'POST', body: form });
    if (!res.ok) throw new Error(await res.text());
    return res.json() as Promise<{ documents: any[] }>;
  },
  removeDocument: (id: string) => request(`/documents/${id}`, { method: 'DELETE' }),
  reorder: (ids: string[]) => request('/documents/order', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  }),
  updateDocument: (id: string, body: { included?: boolean }) =>
    request(`/documents/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  startMerge: (outputPath?: string, overwrite = false) =>
    request<{ job_id: string }>('/merge-jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ output_path: outputPath, overwrite }),
    }),
  getJob: (id: string) => request<any>(`/merge-jobs/${id}`),
  cancelJob: (id: string) => request(`/merge-jobs/${id}/cancel`, { method: 'POST' }),
  report: (id: string) => request<any>(`/merge-jobs/${id}/report`),
  saveSession: () => request<any>('/sessions/save', { method: 'POST' }),
  pickFolder: (initialDir?: string) =>
    request<{ path: string | null }>(
      `/system/pick-folder${initialDir ? `?initial_dir=${encodeURIComponent(initialDir)}` : ''}`,
      { method: 'POST' },
    ),
  pickSavePath: (initialDir?: string, initialName?: string) =>
    request<{ path: string | null }>('/system/pick-save-path', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initial_dir: initialDir || null, initial_name: initialName || null }),
    }),
  reveal: (path: string) =>
    request<{ ok: boolean }>('/system/reveal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    }),
};
