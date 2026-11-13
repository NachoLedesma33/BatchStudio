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
