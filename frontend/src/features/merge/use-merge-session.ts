import { useCallback, useEffect, useRef, useState } from 'react';
import { arrayMove } from '@dnd-kit/sortable';
import type { DragEndEvent } from '@dnd-kit/core';

import { api } from '@/lib/api';
import type { MergeResult, PdfDocument } from '@/lib/api/types';

interface UseMergeSessionOptions {
  outputDir: string;
  outputName: string;
  overwrite: boolean;
  announce: (message: string) => void;
}

/**
 * Estado y acciones del lote de unión: documentos, importación, orden y job.
 * No conoce la selección múltiple ni la previsualización.
 */
export function useMergeSession({ outputDir, outputName, overwrite, announce }: UseMergeSessionOptions) {
  const [docs, setDocs] = useState<PdfDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>('idle');
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<string>('');
  const [currentFile, setCurrentFile] = useState<string>('');
  const [result, setResult] = useState<MergeResult | null>(null);
  const [showResult, setShowResult] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const refresh = useCallback(async () => {
    const r = await api.listDocuments();
    setDocs(r.documents);
  }, []);
  // Al montar hay que traer la lista del lote desde el backend.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void refresh(); }, [refresh]);

  const handleFiles = async (files: File[]) => {
    const pdfs = files.filter((f) => f.name.toLowerCase().endsWith('.pdf'));
    if (!pdfs.length) return;
    setUploading(true);
    try { await api.uploadFiles(pdfs); await refresh(); }
    catch (e) { alert('Error al importar: ' + (e as Error).message); }
    finally { setUploading(false); }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false);
    const files: File[] = [];
    if (e.dataTransfer.items) for (let i = 0; i < e.dataTransfer.items.length; i++) { const f = e.dataTransfer.items[i].getAsFile(); if (f) files.push(f); }
    else for (let i = 0; i < e.dataTransfer.files.length; i++) files.push(e.dataTransfer.files[i]);
    handleFiles(files);
  };

  const onDragEnd = async (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = docs.findIndex((d) => d.id === active.id);
    const newIndex = docs.findIndex((d) => d.id === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    const newDocs = arrayMove(docs, oldIndex, newIndex);
    setDocs(newDocs);
    try { await api.reorder(newDocs.map((d) => d.id)); }
    catch (e) { alert('Error al reordenar: ' + (e as Error).message); await refresh(); }
  };

  const removeDoc = async (id: string) => { await api.removeDocument(id); await refresh(); };

  const toggleDoc = async (id: string) => {
    const d = docs.find((x) => x.id === id);
    if (!d) return;
    await api.updateDocument(id, { included: !d.included });
    await refresh();
  };

  /** Quita todos los documentos y devuelve cuántos había. */
  const clearLot = async () => {
    const removed = docs.length;
    for (const d of docs) await api.removeDocument(d.id);
    setDocs([]);
    await refresh();
    return removed;
  };

  const startMerge = async (forceOverwrite = false) => {
    setResult(null); setShowResult(false); setJobStatus('starting'); setProgress(0);
    try {
      const combined = outputDir.trim()
        ? `${outputDir.trim().replace(/[\\/]+$/, '')}\\${outputName.trim() || 'documentos_unidos.pdf'}`
        : (outputName.trim() || undefined);
      const r = await api.startMerge(combined, forceOverwrite || overwrite);
      setJobId(r.job_id); setJobStatus('running');
      if (eventSourceRef.current) eventSourceRef.current.close();
      const es = new EventSource(`/api/merge-jobs/${r.job_id}/events`);
      eventSourceRef.current = es;
      es.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === 'progress') { setProgress(data.progress ?? 0); setStage(data.stage ?? ''); setCurrentFile(data.file ?? ''); }
          else if (data.type === 'result') setResult(data.result);
          else if (data.type === 'done') {
            setJobStatus(data.status); es.close();
            api.report(r.job_id).then((rep) => {
              setResult(rep); setShowResult(true);
              announce(
                rep.status === 'cancelled'
                  ? 'Unión cancelada.'
                  : rep.status === 'completed'
                    ? `Unión completada: ${rep.total_pages} páginas.`
                    : `Unión terminada con ${rep.errors?.length ?? 0} problema(s).`,
              );
            }).catch(() => {});
          }
          else if (data.type === 'error') setJobStatus('failed');
        } catch {}
      };
      es.onerror = () => es.close();
    } catch (e) { setJobStatus('failed'); alert('Error al iniciar unión: ' + (e as Error).message); }
  };

  const cancelMerge = async () => { if (jobId) await api.cancelJob(jobId); };

  return {
    docs,
    uploading,
    dragOver,
    setDragOver,
    jobId,
    jobStatus,
    progress,
    stage,
    currentFile,
    result,
    showResult,
    setShowResult,
    refresh,
    handleFiles,
    onDrop,
    onDragEnd,
    removeDoc,
    toggleDoc,
    clearLot,
    startMerge,
    cancelMerge,
  };
}
