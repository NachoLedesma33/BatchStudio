import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';

import { api } from '@/lib/api';
import type { Job } from '@/lib/api';

interface HistoryEntry {
  id: string;
  job_id: string;
  kind: string;
  summary: string;
  created_at: string;
}

export function JobsPanel({ announce }: { announce: (m: string) => void }) {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.listJobs(undefined, 100);
      setJobs(r.jobs || []);
      const h = await api.listHistory(100);
      setHistory((h.history || []) as unknown as HistoryEntry[]);
    } catch (e) {
      alert('No se pudo cargar la cola: ' + (e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const cancel = async (id: string) => {
    try { await api.cancelJobById(id); announce('Trabajo cancelado.'); await load(); }
    catch (e) { alert((e as Error).message); }
  };

  const retry = async (id: string) => {
    try { await api.retryJob(id); announce('Trabajo reencolado.'); await load(); }
    catch (e) { alert((e as Error).message); }
  };

  const downloadExport = async (format: 'json' | 'csv' | 'txt') => {
    try {
      const r = await api.exportHistory(format, 500);
      let content = '';
      if (format === 'json') content = JSON.stringify(r.items ?? r, null, 2);
      else content = r.content || '';
      const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `historial.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert('No se pudo exportar: ' + (e as Error).message);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold">Cola de trabajos</h2>
        <Button size="sm" variant="outline" onClick={load} disabled={loading}>Actualizar</Button>
      </div>
      {loading && <div className="text-xs text-muted-foreground">Cargando…</div>}
      <div className="overflow-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="py-1">ID</th>
              <th className="py-1">Tipo</th>
              <th className="py-1">Estado</th>
              <th className="py-1">Progreso</th>
              <th className="py-1">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id} className="border-t">
                <td className="py-1 font-mono">{job.id.slice(0, 8)}</td>
                <td className="py-1">{job.kind}</td>
                <td className="py-1">{job.status}</td>
                <td className="py-1">{Math.round(job.progress)}%</td>
                <td className="py-1 flex gap-1">
                  {job.status === 'running' && <Button size="xs" variant="destructive" onClick={() => cancel(job.id)}>Cancelar</Button>}
                  {(job.status === 'failed' || job.status === 'cancelled' || job.status === 'interrupted') && (
                    <Button size="xs" variant="outline" onClick={() => retry(job.id)}>Reintentar</Button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {jobs.length === 0 && <div className="py-4 text-center text-xs text-muted-foreground">No hay trabajos.</div>}
      </div>

      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold">Historial</h2>
        <div className="ml-auto flex gap-1">
          <Button size="xs" variant="outline" onClick={() => downloadExport('json')}>JSON</Button>
          <Button size="xs" variant="outline" onClick={() => downloadExport('csv')}>CSV</Button>
          <Button size="xs" variant="outline" onClick={() => downloadExport('txt')}>TXT</Button>
        </div>
      </div>
      <div className="max-h-48 overflow-auto rounded border">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-muted-foreground">
              <th className="py-1 px-2">Fecha</th>
              <th className="py-1 px-2">Tipo</th>
              <th className="py-1 px-2">Resumen</th>
            </tr>
          </thead>
          <tbody>
            {history.map((h) => (
              <tr key={h.id} className="border-t">
                <td className="py-1 px-2">{new Date(h.created_at).toLocaleString()}</td>
                <td className="py-1 px-2">{h.kind}</td>
                <td className="py-1 px-2">{h.summary}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {history.length === 0 && <div className="py-4 text-center text-xs text-muted-foreground">Sin historial.</div>}
      </div>
    </div>
  );
}
