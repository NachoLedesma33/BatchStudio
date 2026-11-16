import { apiBase, authHeaders, parseError, request } from './client';
import type { Capabilities, Job, MergeResult, OperationPlan, PdfDocument } from './types';

export type {
  Capabilities,
  CapabilityTool,
  Job,
  JobItem,
  JobStatus,
  MergeError,
  MergeResult,
  OperationPlan,
  PdfDocument,
  PdfStatus,
  PlanMessage,
} from './types';

interface DocumentList {
  documents: PdfDocument[];
}

interface JobCreated {
  job_id: string;
  status?: string;
}

export const api = {
  health: () => request<{ status: string }>('/health'),
  capabilities: (refresh = false) =>
    request<Capabilities>(`/capabilities${refresh ? '?refresh=true' : ''}`),

  listDocuments: () => request<DocumentList>('/documents'),
  importPaths: (paths: string[]) =>
    request<DocumentList>('/files/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ paths }),
    }),
  importFolder: (folder: string, recursive = true) =>
    request<DocumentList>('/folders/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ folder, recursive }),
    }),
  uploadFiles: async (files: File[]) => {
    const form = new FormData();
    files.forEach((file) => form.append('files', file));
    const res = await fetch(apiBase() + '/files/upload', {
      method: 'POST',
      body: form,
      headers: authHeaders(),
    });
    if (!res.ok) throw await parseError(res);
    return (await res.json()) as DocumentList;
  },
  removeDocument: (id: string) => request<{ ok: boolean }>(`/documents/${id}`, { method: 'DELETE' }),
  clearDocuments: () => request<{ ok: boolean; removed: number }>('/documents', { method: 'DELETE' }),
  reorder: (ids: string[]) =>
    request<DocumentList>('/documents/order', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ids }),
    }),
  updateDocument: (id: string, body: { included?: boolean; name?: string }) =>
    request<PdfDocument>(`/documents/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),

  previewOperation: (kind: string, params: Record<string, unknown>) =>
    request<OperationPlan>('/operations/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, params }),
    }),
  createJob: (kind: string, params: Record<string, unknown>) =>
    request<JobCreated>('/jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, params }),
    }),
  listJobs: (status?: string, limit = 50) =>
    request<{ jobs: Job[] }>(
      `/jobs?limit=${limit}${status ? `&status=${encodeURIComponent(status)}` : ''}`,
    ),
  getJob: (id: string) => request<Job>(`/jobs/${id}`),
  cancelJobById: (id: string) => request<{ ok: boolean }>(`/jobs/${id}/cancel`, { method: 'POST' }),
  retryJob: (id: string) =>
    request<{ job_id: string; status: string }>(`/jobs/${id}/retry`, { method: 'POST' }),
  jobReport: (id: string) => request<Record<string, unknown>>(`/jobs/${id}/report`),

  // Alias retrocompatible con la UI de unión existente.
  startMerge: (outputPath?: string, overwrite = false) =>
    request<JobCreated>('/merge-jobs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ output_path: outputPath, overwrite }),
    }),
  getJobLegacy: (id: string) => request<Record<string, unknown>>(`/merge-jobs/${id}`),
  cancelJob: (id: string) => request<{ ok: boolean }>(`/merge-jobs/${id}/cancel`, { method: 'POST' }),
  report: (id: string) => request<MergeResult>(`/merge-jobs/${id}/report`),

  autosaveSession: () => request<{ path: string }>('/sessions/autosave', { method: 'POST' }),
  autorestoreSession: () => request<{ restored: boolean; documents: PdfDocument[] }>('/sessions/autorestore', { method: 'POST' }),
  listSessions: () =>
    request<{ sessions: Array<Record<string, unknown>> }>('/sessions'),
  history: (limit = 50) =>
    request<{ history: Array<Record<string, unknown>> }>(`/history?limit=${limit}`),

  pickFolder: (initialDir?: string) =>
    request<{ path: string | null }>(
      `/system/pick-folder${initialDir ? `?initial_dir=${encodeURIComponent(initialDir)}` : ''}`,
      { method: 'POST' },
    ),
  pickFiles: (initialDir?: string) =>
    request<{ paths: string[] }>('/system/pick-files', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initial_dir: initialDir || null, multiple: true }),
    }),
  pickSavePath: (initialDir?: string, initialName?: string) =>
    request<{ path: string | null }>('/system/pick-save-path', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ initial_dir: initialDir || null, initial_name: initialName || null }),
    }),
  getPages: (id: string) =>
    request<{ document_id: string; pages: Array<{ page_no: number; page_order: number; rotation: number; excluded: boolean }> }>(`/documents/${id}/pages`),
  replacePages: (id: string, pages: Array<{ page_no: number; page_order?: number; rotation?: number; excluded?: boolean }>) =>
    request<{ document_id: string; pages: Array<{ page_no: number; page_order: number; rotation: number; excluded: boolean }> }>(`/documents/${id}/pages`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pages }),
    }),
  patchPage: (id: string, pageNo: number, body: { page_order?: number; rotation?: number; excluded?: boolean }) =>
    request<{ document_id: string; page_no: number; updated: boolean }>(`/documents/${id}/pages/${pageNo}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  reveal: (path: string) =>
    request<{ ok: boolean }>('/system/reveal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    }),
};

export type Api = typeof api;
