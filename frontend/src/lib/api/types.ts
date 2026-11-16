export type PdfStatus =
  | 'pending' | 'inspecting' | 'ready' | 'warning' | 'invalid'
  | 'protected' | 'processing' | 'completed' | 'failed';

export interface PdfDocument {
  id: string;
  path: string;
  name: string;
  size_bytes: number;
  page_count: number | null;
  sha256: string | null;
  status: PdfStatus;
  error_message: string | null;
  included: boolean;
  order_index: number;
  metadata: Record<string, unknown>;
}

export interface MergeError {
  document_id: string | null;
  path: string | null;
  message: string;
  detail: string | null;
}

export interface MergeResult {
  job_id: string;
  status: string;
  output_path: string | null;
  total_pages: number;
  processed_documents: number;
  error_count: number;
  errors: MergeError[];
  started_at: string | null;
  finished_at: string | null;
  elapsed_seconds: number;
  peak_rss_mb: number;
  cancelled: boolean;
}

export type JobStatus =
  | 'queued' | 'running' | 'completed' | 'completed_with_errors'
  | 'failed' | 'cancelled' | 'interrupted';

export interface JobItem {
  index: number;
  label: string;
  status: string;
  output_path: string | null;
  message: string | null;
}

export interface Job {
  id: string;
  job_id: string;
  kind: string;
  status: JobStatus;
  progress: number;
  stage: string | null;
  total_items: number;
  done_items: number;
  error_count: number;
  errors: Array<Record<string, unknown>>;
  output: Record<string, unknown> | null;
  items: JobItem[];
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

export interface PlanMessage {
  code: string;
  message: string;
}

export interface OperationPlan {
  kind: string;
  summary: {
    total_files?: number;
    total_pages?: number;
    total_bytes_estimate?: number;
    [key: string]: unknown;
  };
  items: Array<{
    index: number;
    label: string;
    pages: number[] | null;
    exists: boolean;
    output_path: string | null;
  }>;
  warnings: PlanMessage[];
  errors: PlanMessage[];
}

export interface CapabilityTool {
  available: boolean;
  path: string | null;
  version: string | null;
  note: string;
}

export interface Capabilities {
  checked_at: string;
  platform: Record<string, string>;
  pdf_engine: { name: string; available: boolean; version: string };
  tools: Record<string, CapabilityTool>;
}
