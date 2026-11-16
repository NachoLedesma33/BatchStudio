import { useCallback, useEffect, useRef, useState } from 'react';

import { api } from '@/lib/api';
import type { OperationPlan, PdfDocument } from '@/lib/api';

interface UseSplitSessionOptions {
  outputDir: string;
  announce: (message: string) => void;
}

export type SplitMode = 'ranges' | 'every' | 'single';
export type CollisionPolicy = 'suffix' | 'fail' | 'overwrite';

export function useSplitSession({ outputDir, announce }: UseSplitSessionOptions) {
  const [docs, setDocs] = useState<PdfDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

  const [mode, setMode] = useState<SplitMode>('ranges');
  const [ranges, setRanges] = useState('1-3');
  const [every, setEvery] = useState('2');
  const [template, setTemplate] = useState('{name}_parte_{index:02}');
  const [collisionPolicy, setCollisionPolicy] = useState<CollisionPolicy>('suffix');

  const [plan, setPlan] = useState<OperationPlan | null>(null);
  const [previewing, setPreviewing] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>('idle');
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<string>('');
  const [currentFile, setCurrentFile] = useState<string>('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
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

  const buildParams = useCallback(() => ({
    mode,
    ranges: mode === 'ranges' ? ranges : undefined,
    every: mode === 'every' ? Number(every) : undefined,
    name_template: template,
    collision_policy: collisionPolicy,
    output_dir: outputDir.trim() || undefined,
  }), [mode, ranges, every, template, collisionPolicy, outputDir]);

  const preview = useCallback(async () => {
    setPreviewing(true);
    setPreviewError(null);
    try {
      const p = await api.previewOperation('split', buildParams());
      setPlan(p);
    } catch (e) {
      setPreviewError((e as Error).message);
      setPlan(null);
    } finally {
      setPreviewing(false);
    }
  }, [buildParams]);

  const startSplit = useCallback(async () => {
    setResult(null); setShowResult(false); setJobStatus('starting'); setProgress(0); setStage('');
    try {
      const r = await api.createJob('split', buildParams());
      setJobId(r.job_id); setJobStatus('running');
      if (eventSourceRef.current) eventSourceRef.current.close();
      const es = new EventSource(`/api/jobs/${r.job_id}/events`);
      eventSourceRef.current = es;
      es.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === 'progress') {
            setProgress(data.progress ?? 0);
            setStage(data.stage ?? '');
            setCurrentFile(data.file ?? data.current ?? '');
          } else if (data.type === 'result') {
            setResult((data.result ?? null) as Record<string, unknown> | null);
          } else if (data.type === 'done') {
            setJobStatus(data.status);
            es.close();
            api.jobReport(r.job_id).then((rep) => {
              const r = rep as { status?: string; result?: { total_files?: number } | null; errors?: unknown[] };
              setResult((r.result ?? (rep as Record<string, unknown>)) as Record<string, unknown> | null);
              setShowResult(true);
              announce(r.status === 'cancelled' ? 'División cancelada.' : r.status === 'completed' ? `División completada: ${r.result?.total_files ?? 0} archivos.` : `División terminada con ${r.errors?.length ?? 0} problema(s).`);
            }).catch(() => {});
          } else if (data.type === 'error') {
            setJobStatus('failed');
          }
        } catch {}
      };
      es.onerror = () => es.close();
    } catch (e) {
      setJobStatus('failed');
      alert('Error al iniciar la división: ' + (e as Error).message);
    }
  }, [buildParams, announce]);

  const cancelSplit = async () => { if (jobId) await api.cancelJobById(jobId); };

  const removeDoc = async (id: string) => { await api.removeDocument(id); await refresh(); };
  const toggleDoc = async (id: string) => {
    const d = docs.find((x) => x.id === id);
    if (!d) return;
    await api.updateDocument(id, { included: !d.included });
    await refresh();
  };
  const clearLot = async () => {
    const removed = docs.length;
    for (const d of docs) await api.removeDocument(d.id);
    setDocs([]);
    await refresh();
    return removed;
  };

  return {
    docs, uploading, dragOver, setDragOver, refresh, handleFiles, onDrop,
    mode, setMode, ranges, setRanges, every, setEvery, template, setTemplate,
    collisionPolicy, setCollisionPolicy,
    plan, previewing, previewError, preview,
    jobId, jobStatus, progress, stage, currentFile, result, showResult, setShowResult,
    startSplit, cancelSplit,
    removeDoc, toggleDoc, clearLot,
  };
}