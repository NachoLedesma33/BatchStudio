import type { PdfDocument } from '@/lib/api';

export function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

export const STATUS_LABEL: Record<PdfDocument['status'], string> = {
  pending: 'Pendiente',
  inspecting: 'Analizando',
  ready: 'Listo',
  warning: 'Advertencia',
  invalid: 'Inválido',
  protected: 'Protegido',
  processing: 'Procesando',
  completed: 'Completado',
  failed: 'Error',
};

export function statusVariant(status: PdfDocument['status']): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'ready' || status === 'completed') return 'default';
  if (status === 'invalid' || status === 'failed' || status === 'protected') return 'destructive';
  if (status === 'warning') return 'secondary';
  return 'outline';
}
