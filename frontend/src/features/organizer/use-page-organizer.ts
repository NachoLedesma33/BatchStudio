import { useCallback, useEffect, useRef, useState } from 'react';

import { api } from '@/lib/api';

export interface PageState {
  page_no: number;
  page_order: number;
  rotation: number;
  excluded: boolean;
}

interface UsePageOrganizerOptions {
  documentId: string | null;
  announce: (message: string) => void;
}

export function usePageOrganizer({ documentId, announce }: UsePageOrganizerOptions) {
  const [pages, setPages] = useState<PageState[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<PageState[][]>([]);
  const [future, setFuture] = useState<PageState[][]>([]);
  const [jobStatus, setJobStatus] = useState<string>('idle');
  const [progress, setProgress] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);

  const load = useCallback(async () => {
    if (!documentId) { setPages([]); return; }
    setLoading(true);
    try {
      const r = await api.getPages(documentId);
      const list = (r.pages || []).map((p) => ({
        page_no: p.page_no,
        page_order: p.page_order,
        rotation: p.rotation,
        excluded: p.excluded,
      }));
      list.sort((a, b) => a.page_order - b.page_order);
      setPages(list);
      setSelected(new Set());
      setHistory([]);
      setFuture([]);
    } catch (e) {
      alert('No se pudieron cargar las páginas: ' + (e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [documentId]);

  // Al cambiar de documento hay que cargar su modelo de páginas.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { void load(); }, [load]);

  const commit = useCallback((next: PageState[]) => {
    setHistory((h) => [...h, pages]);
    setFuture([]);
    setPages(next);
  }, [pages]);

  const undo = useCallback(() => {
    setHistory((h) => {
      if (!h.length) return h;
      const prev = h[h.length - 1];
      setFuture((f) => [pages, ...f]);
      setPages(prev);
      return h.slice(0, -1);
    });
  }, [pages]);

  const redo = useCallback(() => {
    setFuture((f) => {
      if (!f.length) return f;
      const next = f[0];
      setHistory((h) => [...h, pages]);
      setPages(next);
      return f.slice(1);
    });
  }, [pages]);

  const persist = useCallback(async () => {
    if (!documentId) return;
    try {
      await api.replacePages(documentId, pages.map((p, index) => ({
        page_no: p.page_no,
        page_order: index,
        rotation: p.rotation,
        excluded: p.excluded,
      })));
      announce('Estado de páginas guardado.');
    } catch (e) {
      alert('No se pudo guardar: ' + (e as Error).message);
    }
  }, [documentId, pages, announce]);

  const reorder = useCallback((from: number, to: number) => {
    if (from === to) return;
    const next = [...pages];
    const [moved] = next.splice(from, 1);
    next.splice(to, 0, moved);
    commit(next);
  }, [pages, commit]);

  const rotateSelected = useCallback((angle: number) => {
    if (selected.size === 0) return;
    const next = pages.map((p) =>
      selected.has(p.page_no) ? { ...p, rotation: (p.rotation + angle + 360) % 360 } : p,
    );
    commit(next);
  }, [pages, selected, commit]);

  const toggleExcludedSelected = useCallback(() => {
    if (selected.size === 0) return;
    const next = pages.map((p) =>
      selected.has(p.page_no) ? { ...p, excluded: !p.excluded } : p,
    );
    commit(next);
  }, [pages, selected, commit]);

  const selectPage = useCallback((pageNo: number, event?: { ctrlKey?: boolean; shiftKey?: boolean; metaKey?: boolean }) => {
    const ctrl = !!(event?.ctrlKey || event?.metaKey);
    const shift = !!event?.shiftKey;
    setSelected((prev) => {
      if (shift && prev.size > 0) {
        const last = Array.from(prev).pop() as number;
        const ordered = pages.map((p) => p.page_no);
        const from = ordered.indexOf(last);
        const to = ordered.indexOf(pageNo);
        const [start, end] = from < to ? [from, to] : [to, from];
        const next = new Set(prev);
        for (let i = start; i <= end; i++) next.add(ordered[i]);
        return next;
      }
      if (ctrl) {
        const next = new Set(prev);
        if (next.has(pageNo)) next.delete(pageNo);
        else next.add(pageNo);
        return next;
      }
      return new Set([pageNo]);
    });
  }, [pages]);

  const extractSelected = useCallback(async (outputDir: string) => {
    if (!documentId || selected.size === 0) return;
    setJobStatus('starting');
    setProgress(0);
    try {
      const r = await api.createJob('extract', {
        document_id: documentId,
        pages: Array.from(selected),
        output_dir: outputDir || undefined,
        name_template: '{name}_extraido',
      });
      setJobStatus('running');
      if (eventSourceRef.current) eventSourceRef.current.close();
      const es = new EventSource(`/api/jobs/${r.job_id}/events`);
      eventSourceRef.current = es;
      es.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === 'progress') setProgress(data.progress ?? 0);
          else if (data.type === 'done') {
            setJobStatus(data.status);
            es.close();
            announce(data.status === 'completed' ? 'Extracción completada.' : 'Extracción terminada con problemas.');
          }
        } catch {}
      };
      es.onerror = () => es.close();
    } catch (e) {
      setJobStatus('failed');
      alert('Error al extraer: ' + (e as Error).message);
    }
  }, [documentId, selected, announce]);

  return {
    pages,
    selected,
    loading,
    history,
    future,
    jobStatus,
    progress,
    load,
    commit,
    undo,
    redo,
    persist,
    reorder,
    rotateSelected,
    toggleExcludedSelected,
    selectPage,
    extractSelected,
    setSelected,
  };
}
