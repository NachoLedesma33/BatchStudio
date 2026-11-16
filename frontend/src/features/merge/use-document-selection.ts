import { useEffect, useMemo, useRef, useState } from 'react';

import { api } from '@/lib/api';

interface UseDocumentSelectionOptions {
  visibleIds: string[];
  refresh: () => Promise<void>;
  announce: (message: string) => void;
}

/** Selección múltiple de la lista: clic, Ctrl, Shift, por lote y teclado. */
export function useDocumentSelection({ visibleIds, refresh, announce }: UseDocumentSelectionOptions) {
  // `selectedIds` marca los documentos operados en lote;
  // `previewId` es el último documento enfocado, el que muestra el panel derecho.
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [previewId, setPreviewId] = useState<string | null>(null);
  const selectionAnchorRef = useRef<string | null>(null);

  const selectedCount = selectedIds.size;
  const allVisibleSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.has(id));
  const someVisibleSelected = visibleIds.some((id) => selectedIds.has(id));

  const handleRowSelect = (id: string, e: React.MouseEvent) => {
    const additive = e.ctrlKey || e.metaKey;
    if (e.shiftKey && selectionAnchorRef.current) {
      const from = visibleIds.indexOf(selectionAnchorRef.current);
      const to = visibleIds.indexOf(id);
      if (from >= 0 && to >= 0) {
        const [lo, hi] = from <= to ? [from, to] : [to, from];
        setSelectedIds(new Set(visibleIds.slice(lo, hi + 1)));
        setPreviewId(id);
        return;
      }
    }
    selectionAnchorRef.current = id;
    setSelectedIds((prev) => {
      if (!additive) return new Set([id]);
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
    setPreviewId(id);
  };

  const toggleRowSelection = (id: string) => {
    selectionAnchorRef.current = id;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
    setPreviewId(id);
  };

  const selectAllVisible = () => {
    setSelectedIds(new Set(visibleIds));
    if (visibleIds.length) setPreviewId(visibleIds[0]);
  };

  const clearSelection = () => setSelectedIds(new Set());

  const bulkSetIncluded = async (included: boolean) => {
    const ids = [...selectedIds];
    if (!ids.length) return;
    try {
      await Promise.all(ids.map((id) => api.updateDocument(id, { included })));
      await refresh();
      announce(`${ids.length} ${ids.length === 1 ? 'documento' : 'documentos'} ${included ? 'incluido' : 'excluido'}${ids.length === 1 ? '' : 's'} en el lote.`);
    } catch (e) { alert('No se pudo actualizar la selección: ' + (e as Error).message); }
  };

  const bulkRemove = async () => {
    const ids = [...selectedIds];
    if (!ids.length) return;
    try {
      await Promise.all(ids.map((id) => api.removeDocument(id)));
      if (previewId && ids.includes(previewId)) setPreviewId(null);
      setSelectedIds(new Set());
      await refresh();
      announce(`${ids.length} ${ids.length === 1 ? 'documento quitado' : 'documentos quitados'} de la lista.`);
    } catch (e) { alert('No se pudieron quitar los documentos: ' + (e as Error).message); }
  };

  return {
    selectedIds,
    setSelectedIds,
    previewId,
    setPreviewId,
    selectedCount,
    allVisibleSelected,
    someVisibleSelected,
    handleRowSelect,
    toggleRowSelection,
    selectAllVisible,
    clearSelection,
    bulkSetIncluded,
    bulkRemove,
  };
}

/** Ajusta selección y previsualización cuando cambian los documentos del lote. */
export function usePruneSelection(
  docs: { id: string }[],
  setSelectedIds: (updater: (prev: Set<string>) => Set<string>) => void,
  setPreviewId: (updater: (prev: string | null) => string | null) => void,
) {
  const ids = useMemo(() => docs.map((d) => d.id), [docs]);
  useEffect(() => {
    setSelectedIds((prev) => {
      if (!prev.size) return prev;
      const alive = new Set(ids);
      let changed = false;
      const next = new Set<string>();
      for (const id of prev) { if (alive.has(id)) next.add(id); else changed = true; }
      return changed ? next : prev;
    });
    setPreviewId((prev) => (prev && !ids.includes(prev) ? null : prev));
  }, [ids, setSelectedIds, setPreviewId]);
}
