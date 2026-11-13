import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Upload, FolderOpen, Eye, Trash2, Check, X, Square, FileText, Loader2,
  Files, HardDrive, ChevronLeft, ChevronRight, Merge, CheckCircle,
  Search, Trash, HelpCircle, Plus, GripVertical, ExternalLink,
  AlertTriangle, CircleSlash, Save, Copy,
} from 'lucide-react';

import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors, type DragEndEvent } from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates, useSortable, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useVirtualizer } from '@tanstack/react-virtual';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';

import { api } from './api';
import type { PdfDocument, MergeResult } from './types';
import { ThemeToggle } from '@/components/theme-toggle';
import { ShortcutsDialog } from '@/components/shortcuts-dialog';
import { isFormControl, isTextEntry } from './lib/shortcuts';

function formatBytes(n: number) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

const STATUS_LABEL: Record<PdfDocument['status'], string> = {
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

function statusVariant(status: PdfDocument['status']): 'default' | 'secondary' | 'destructive' | 'outline' {
  if (status === 'ready' || status === 'completed') return 'default';
  if (status === 'invalid' || status === 'failed' || status === 'protected') return 'destructive';
  if (status === 'warning') return 'secondary';
  return 'outline';
}

type SortMode = 'manual' | 'name' | 'size' | 'pages';

const ROW_HEIGHT = 64;

function IconButton({ label, onClick, disabled, tabIndex, children }: {
  label: string; onClick: (e: React.MouseEvent) => void; disabled?: boolean; tabIndex?: number; children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button size="icon-sm" variant="ghost" onClick={onClick} disabled={disabled} tabIndex={tabIndex} aria-label={label}>
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

/** Checkbox nativo que además soporta el estado indeterminado (selección parcial). */
function TriCheckbox({ checked, indeterminate, onChange, disabled, label }: {
  checked: boolean; indeterminate?: boolean; onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean; label: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { if (ref.current) ref.current.indeterminate = Boolean(indeterminate) && !checked; }, [indeterminate, checked]);
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      disabled={disabled}
      onChange={onChange}
      aria-label={label}
      className="h-3.5 w-3.5 flex-shrink-0 cursor-pointer accent-primary disabled:cursor-not-allowed"
    />
  );
}

function DocumentRow({ doc, selected, onSelect, onToggleSelect, onRemove, onToggle, duplicateGroup, rowIndex, tabIndex, onKeyDown, onFocus }: {
  doc: PdfDocument; selected: boolean; onSelect: (e: React.MouseEvent) => void;
  onToggleSelect: () => void; onRemove: () => void; onToggle: () => void;
  duplicateGroup: number | null; rowIndex: number;
  tabIndex: number; onKeyDown: (e: React.KeyboardEvent) => void; onFocus: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: doc.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 20 : undefined,
  };
  return (
    <div
      ref={setNodeRef}
      style={style}
      data-row-index={rowIndex}
      onClick={onSelect}
      onKeyDown={onKeyDown}
      onFocus={onFocus}
      tabIndex={tabIndex}
      className={`flex h-14 items-center gap-2.5 rounded-lg border px-2.5 transition-colors cursor-pointer outline-none
        focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-card
        ${selected ? 'border-primary/40 bg-accent/5 ring-1 ring-primary/25' : 'border-transparent hover:bg-muted/60'}
        ${doc.included ? '' : 'opacity-55'}
        ${isDragging ? 'shadow-lg bg-card border-primary/40' : ''}`}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={() => onToggleSelect()}
        onClick={(e) => e.stopPropagation()}
        tabIndex={-1}
        aria-label={`Seleccionar ${doc.name}`}
        className="h-3.5 w-3.5 flex-shrink-0 cursor-pointer accent-primary"
      />
      <button
        {...attributes}
        {...listeners}
        className="flex h-8 w-5 flex-shrink-0 cursor-grab items-center justify-center rounded text-muted-foreground/50 hover:bg-muted hover:text-muted-foreground active:cursor-grabbing"
        onClick={(e) => e.stopPropagation()}
        aria-label="Reordenar documento"
        title="Arrastrar para reordenar"
      >
        <GripVertical className="h-4 w-4" />
      </button>
      <div className="relative h-11 w-8 flex-shrink-0">
        <div className={`h-11 w-8 overflow-hidden rounded border bg-muted ${duplicateGroup ? 'border-amber-400 ring-1 ring-amber-400/60' : 'border-border/60'}`}>
          <img
            src={`/api/documents/${doc.id}/preview/1`}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover"
            onError={(e) => { (e.target as HTMLImageElement).style.visibility = 'hidden'; }}
          />
        </div>
        {duplicateGroup !== null && (
          <span
            className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-white shadow ring-2 ring-card"
            title={`Archivo repetido: hay ${duplicateGroup} copias iguales en el lote`}
          >
            <Copy className="h-2.5 w-2.5" />
          </span>
        )}
      </div>
      <div className="min-w-0 flex-1">
        <div className="truncate text-sm font-medium" title={doc.name}>{doc.name}</div>
        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span className="tabular-nums">{doc.page_count ?? '—'} págs</span>
          <span className="opacity-40">·</span>
          <span className="tabular-nums">{formatBytes(doc.size_bytes)}</span>
        </div>
      </div>
      <div className="flex flex-shrink-0 items-center gap-1">
        <Badge variant={statusVariant(doc.status)} className="hidden px-1.5 py-0 text-[10px] xl:inline-flex">
          {STATUS_LABEL[doc.status]}
        </Badge>
        <IconButton
          label={doc.included ? 'Excluir del lote' : 'Incluir en el lote'}
          tabIndex={-1}
          onClick={(e) => { e.stopPropagation(); onToggle(); }}
        >
          {doc.included ? <Check className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> : <X className="h-4 w-4" />}
        </IconButton>
        <IconButton
          label="Quitar de la lista"
          tabIndex={-1}
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
        >
          <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
        </IconButton>
      </div>
    </div>
  );
}

export default function App() {
  const [docs, setDocs] = useState<PdfDocument[]>([]);
  // Selección múltiple: `selectedIds` marca los documentos operados en lote;
  // `previewId` es el último documento enfocado, el que muestra el panel derecho.
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewPage, setPreviewPage] = useState(1);
  const [previewZoom, setPreviewZoom] = useState(1);
  const [uploading, setUploading] = useState(false);
  const [outputDir, setOutputDir] = useState('');
  const [outputName, setOutputName] = useState('documentos_unidos.pdf');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortMode, setSortMode] = useState<SortMode>('manual');
  const [onlyDuplicates, setOnlyDuplicates] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>('idle');
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<string>('');
  const [currentFile, setCurrentFile] = useState<string>('');
  const [result, setResult] = useState<MergeResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [overwrite, setOverwrite] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [focusIndex, setFocusIndex] = useState(-1);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const listParentRef = useRef<HTMLDivElement>(null);
  const selectionAnchorRef = useRef<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const refresh = useCallback(async () => {
    const r = await api.listDocuments();
    setDocs(r.documents as PdfDocument[]);
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  const selectedDoc = docs.find((d) => d.id === previewId) || null;
  useEffect(() => { if (previewId) { setPreviewPage(1); setPreviewZoom(1); } }, [previewId]);

  // Si se quitan documentos del lote, la selección y la previsualización se ajustan solas.
  useEffect(() => {
    setSelectedIds((prev) => {
      if (!prev.size) return prev;
      const alive = new Set(docs.map((d) => d.id));
      let changed = false;
      const next = new Set<string>();
      for (const id of prev) { if (alive.has(id)) next.add(id); else changed = true; }
      return changed ? next : prev;
    });
    setPreviewId((prev) => (prev && !docs.some((d) => d.id === prev) ? null : prev));
  }, [docs]);

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

  const removeDoc = async (id: string) => { await api.removeDocument(id); if (previewId === id) setPreviewId(null); await refresh(); };
  const toggleDoc = async (id: string) => { const d = docs.find((x) => x.id === id); if (!d) return; await api.updateDocument(id, { included: !d.included }); await refresh(); };
  const clearLot = async () => { for (const d of docs) await api.removeDocument(d.id); setDocs([]); setPreviewId(null); setSelectedIds(new Set()); setShowClearConfirm(false); await refresh(); };

  const pickFolder = async () => {
    try {
      const r = await api.pickFolder(outputDir.trim() || undefined);
      if (r.path) setOutputDir(r.path);
    } catch (e) { alert('No se pudo abrir el selector de carpetas: ' + (e as Error).message); }
  };

  const saveAs = async () => {
    try {
      const r = await api.pickSavePath(outputDir.trim() || undefined, outputName.trim() || undefined);
      if (r.path) {
        const sep = Math.max(r.path.lastIndexOf('\\'), r.path.lastIndexOf('/'));
        if (sep > 0) {
          setOutputDir(r.path.slice(0, sep));
          setOutputName(r.path.slice(sep + 1));
        } else {
          setOutputName(r.path);
        }
      }
    } catch (e) { alert('No se pudo abrir el diálogo de guardado: ' + (e as Error).message); }
  };

  const reveal = async (path: string) => {
    try { await api.reveal(path); }
    catch (e) { alert('No se pudo abrir: ' + (e as Error).message); }
  };

  // Detección de repetidos: solo comparamos sha256 (mismo contenido byte a byte),
  // así nunca marcamos un archivo distinto por error. Sin hash, no se marca nada.
  const duplicates = useMemo(() => {
    const firstByHash = new Map<string, string>();
    const groups = new Map<string, number>();
    const flagged = new Set<string>();
    const extras = new Set<string>();
    for (const d of docs) {
      if (!d.sha256) continue;
      const first = firstByHash.get(d.sha256);
      if (first === undefined) { firstByHash.set(d.sha256, d.id); continue; }
      if (!flagged.has(first)) { flagged.add(first); groups.set(d.sha256, 2); }
      else groups.set(d.sha256, (groups.get(d.sha256) ?? 1) + 1);
      flagged.add(d.id);
      extras.add(d.id);
    }
    const groupSize = new Map<string, number>();
    for (const [hash, size] of groups) {
      for (const d of docs) if (d.sha256 === hash) groupSize.set(d.id, size);
    }
    return { groupSize, flagged, extras, groupCount: groups.size };
  }, [docs]);

  const dupExtras = duplicates.extras.size;
  const dupExtrasIncluded = useMemo(
    () => docs.filter((d) => duplicates.extras.has(d.id) && d.included).length,
    [docs, duplicates],
  );

  const excludeDuplicates = async () => {
    // Por cada grupo conservamos la primera copia incluida y excluimos el resto.
    const byHash = new Map<string, PdfDocument[]>();
    for (const d of docs) {
      if (!d.sha256 || !duplicates.groupSize.has(d.id)) continue;
      const arr = byHash.get(d.sha256) ?? [];
      arr.push(d);
      byHash.set(d.sha256, arr);
    }
    const toExclude: string[] = [];
    for (const group of byHash.values()) {
      let kept = false;
      for (const d of group) {
        if (!kept && d.included) { kept = true; continue; }
        if (d.included) toExclude.push(d.id);
      }
    }
    if (!toExclude.length) return;
    try {
      await Promise.all(toExclude.map((id) => api.updateDocument(id, { included: false })));
      await refresh();
    } catch (e) { alert('No se pudieron excluir los repetidos: ' + (e as Error).message); }
  };

  const includeAllDuplicates = async () => {
    const toInclude = docs.filter((d) => duplicates.flagged.has(d.id) && !d.included).map((d) => d.id);
    if (!toInclude.length) return;
    try {
      await Promise.all(toInclude.map((id) => api.updateDocument(id, { included: true })));
      await refresh();
    } catch (e) { alert('No se pudieron incluir los repetidos: ' + (e as Error).message); }
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
            api.report(r.job_id).then((rep) => { setResult(rep); setShowResult(true); }).catch(() => {});
          }
          else if (data.type === 'error') setJobStatus('failed');
        } catch {}
      };
      es.onerror = () => es.close();
    } catch (e) { setJobStatus('failed'); alert('Error al iniciar unión: ' + (e as Error).message); }
  };

  const cancelMerge = async () => { if (jobId) await api.cancelJob(jobId); };

  const filteredDocs = useMemo(() => {
    let list = docs;
    if (onlyDuplicates) list = list.filter((d) => duplicates.flagged.has(d.id));
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter((d) => d.name.toLowerCase().includes(q));
    }
    if (sortMode === 'name') list = [...list].sort((a, b) => a.name.localeCompare(b.name));
    else if (sortMode === 'size') list = [...list].sort((a, b) => b.size_bytes - a.size_bytes);
    else if (sortMode === 'pages') list = [...list].sort((a, b) => (b.page_count || 0) - (a.page_count || 0));
    return list;
  }, [docs, searchQuery, sortMode, onlyDuplicates, duplicates]);

  const virtualizer = useVirtualizer({
    count: filteredDocs.length,
    getScrollElement: () => listParentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  });

  const visibleIds = useMemo(() => filteredDocs.map((d) => d.id), [filteredDocs]);
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
    } catch (e) { alert('No se pudieron quitar los documentos: ' + (e as Error).message); }
  };

  // Foco por teclado dentro de la lista: la fila enfocada es la única con tabIndex 0.
  const focusRow = useCallback((index: number) => {
    if (!visibleIds.length) return;
    const clamped = Math.max(0, Math.min(visibleIds.length - 1, index));
    setFocusIndex(clamped);
    virtualizer.scrollToIndex(clamped, { align: 'auto' });
    requestAnimationFrame(() => {
      const el = listParentRef.current?.querySelector<HTMLElement>(`[data-row-index="${clamped}"]`);
      el?.focus();
    });
  }, [visibleIds.length, virtualizer]);

  const onRowKeyDown = (index: number, doc: PdfDocument, e: React.KeyboardEvent) => {
    // Solo cuando el foco está en la fila, no en sus controles internos.
    if (e.target !== e.currentTarget) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); focusRow(index + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); focusRow(index - 1); }
    else if (e.key === 'Home') { e.preventDefault(); focusRow(0); }
    else if (e.key === 'End') { e.preventDefault(); focusRow(visibleIds.length - 1); }
    else if (e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); toggleRowSelection(doc.id); }
    else if (e.key === 'Enter') { e.preventDefault(); handleRowSelect(doc.id, e as unknown as React.MouseEvent); }
  };

  // Atajos globales: se leen desde un ref para suscribir el listener una sola vez.
  const shortcutActions = useRef({
    openFiles: () => {}, selectAll: () => {}, clearSelection: () => {},
    removeSelected: () => {}, merge: () => {}, openShortcuts: () => {},
    canSelectAll: false, hasSelection: false, canMerge: false, dialogOpen: false,
  });
  useEffect(() => {
    shortcutActions.current = {
      openFiles: () => fileInputRef.current?.click(),
      selectAll: selectAllVisible,
      clearSelection,
      removeSelected: () => { void bulkRemove(); },
      merge: () => { void startMerge(); },
      openShortcuts: () => setShowShortcuts(true),
      canSelectAll: visibleIds.length > 0,
      hasSelection: selectedCount > 0,
      canMerge: includedCount > 0 && jobStatus !== 'running',
      dialogOpen: showClearConfirm || showResult || showShortcuts,
    };
  });

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const a = shortcutActions.current;
      const mod = e.ctrlKey || e.metaKey;
      const key = e.key;
      if (mod && key.toLowerCase() === 'o') { e.preventDefault(); a.openFiles(); return; }
      if (mod && key.toLowerCase() === 'a') {
        if (isTextEntry(e.target)) return;            // deja que se seleccione el texto del campo
        if (!a.canSelectAll) return;
        e.preventDefault(); a.selectAll(); return;
      }
      if (mod && key === 'Enter') { if (a.canMerge) { e.preventDefault(); a.merge(); } return; }
      if (isFormControl(e.target)) return;
      if (a.dialogOpen) return;                        // los diálogos manejan Esc y el foco
      if (key === 'Escape') { if (a.hasSelection) { e.preventDefault(); a.clearSelection(); } return; }
      if (key === 'Delete') { if (a.hasSelection) { e.preventDefault(); a.removeSelected(); } return; }
      if (key === '?') { e.preventDefault(); a.openShortcuts(); return; }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  const totalFiles = docs.length;
  const includedCount = docs.filter((d) => d.included).length;
  const totalPages = docs.reduce((a, d) => a + (d.included ? (d.page_count || 0) : 0), 0);
  const totalBytes = docs.reduce((a, d) => a + (d.included ? d.size_bytes : 0), 0);
  const hasInvalid = docs.some((d) => d.included && (d.status === 'invalid' || d.status === 'failed'));
  const destExists = result?.errors?.some((e) => /ya existe/i.test(e.message)) ?? false;

  const summary = [
    { icon: Files, value: String(totalFiles), label: 'archivos' },
    { icon: FileText, value: String(totalPages), label: 'páginas' },
    { icon: HardDrive, value: formatBytes(totalBytes), label: 'tamaño' },
    { icon: Check, value: String(includedCount), label: 'incluidos', tone: 'text-emerald-600 dark:text-emerald-400' },
  ];

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background text-foreground">
      {/* Application header */}
      <header className="flex h-14 flex-shrink-0 items-center justify-between border-b bg-card px-5">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <FileText className="h-4 w-4" />
          </div>
          <span className="text-sm font-semibold">PDF Batch Studio</span>
          <Badge variant="outline" className="px-1.5 py-0 text-[10px] text-muted-foreground">LOCAL</Badge>
        </div>
        <div className="flex items-center gap-0.5">
          <ThemeToggle />
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label="Atajos de teclado" onClick={() => setShowShortcuts(true)}>
                <HelpCircle className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Atajos de teclado (?)</TooltipContent>
          </Tooltip>
        </div>
      </header>

      {/* Page heading + batch summary */}
      <div className="flex-shrink-0 border-b bg-card/40 px-5 py-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <h1 className="text-xl font-semibold tracking-tight">Unir documentos PDF</h1>
            <p className="text-sm text-muted-foreground">Organizá tus archivos, revisá su contenido y generá un único documento.</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowClearConfirm(true)} disabled={docs.length === 0}>
            <Trash className="mr-1.5 h-4 w-4" /> Limpiar lote
          </Button>
        </div>
        <div className="mt-3 flex flex-wrap gap-2.5">
          {summary.map((s) => (
            <div key={s.label} className="flex items-center gap-2 rounded-lg border bg-card px-3 py-1.5">
              <s.icon className={`h-4 w-4 ${s.tone ?? 'text-primary'}`} />
              <span className="text-sm font-semibold tabular-nums">{s.value}</span>
              <span className="text-xs text-muted-foreground">{s.label}</span>
            </div>
          ))}
        </div>

        {duplicates.groupCount > 0 && (
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-500/40 dark:bg-amber-500/10 dark:text-amber-200">
            <Copy className="h-3.5 w-3.5 flex-shrink-0" />
            <span>
              <strong className="font-semibold">{dupExtras}</strong> {dupExtras === 1 ? 'archivo repetido' : 'archivos repetidos'} en{' '}
              <strong className="font-semibold">{duplicates.groupCount}</strong> {duplicates.groupCount === 1 ? 'grupo' : 'grupos'} de contenido idéntico.
              {dupExtrasIncluded > 0 ? ' Se conserva la primera copia de cada grupo.' : ' Ya están excluidos del lote.'}
            </span>
            <div className="ml-auto flex items-center gap-2">
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-2 text-xs text-amber-900 hover:bg-amber-100 dark:text-amber-200 dark:hover:bg-amber-500/15"
                onClick={() => setOnlyDuplicates((v) => !v)}
              >
                {onlyDuplicates ? 'Ver todos' : 'Ver repetidos'}
              </Button>
              {dupExtrasIncluded > 0 ? (
                <Button size="sm" variant="outline" className="h-7 border-amber-400 bg-card text-xs dark:border-amber-500/50" onClick={excludeDuplicates}>
                  Excluir repetidos ({dupExtrasIncluded})
                </Button>
              ) : (
                <Button size="sm" variant="outline" className="h-7 border-amber-400 bg-card text-xs dark:border-amber-500/50" onClick={includeAllDuplicates}>
                  Volver a incluirlos
                </Button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Workspace */}
      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        {/* Document panel */}
        <div className="flex w-full flex-col border-r bg-card md:w-[38%] md:min-w-[340px] md:max-w-[500px]">
          <div className="flex-shrink-0 space-y-2 border-b p-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">Documentos</span>
              <span className="text-xs text-muted-foreground">{filteredDocs.length} de {docs.length}</span>
            </div>
            <div className="flex gap-2">
              <Button size="sm" className="flex-1" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                {uploading ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Plus className="mr-1.5 h-3.5 w-3.5" />}
                Agregar PDF
              </Button>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button size="icon" variant="outline" onClick={() => folderInputRef.current?.click()} disabled={uploading} aria-label="Agregar carpeta">
                    <FolderOpen className="h-4 w-4" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Agregar una carpeta completa</TooltipContent>
              </Tooltip>
            </div>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Buscar por nombre..."
                  className="h-8 pl-8 text-sm"
                  aria-label="Buscar documentos"
                />
              </div>
              <Select value={sortMode} onValueChange={(v) => setSortMode(v as SortMode)}>
                <SelectTrigger size="sm" className="w-[112px] text-xs" aria-label="Ordenar documentos">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="manual">Manual</SelectItem>
                  <SelectItem value="name">Nombre</SelectItem>
                  <SelectItem value="size">Tamaño</SelectItem>
                  <SelectItem value="pages">Páginas</SelectItem>
                </SelectContent>
              </Select>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    size="icon-sm"
                    variant={onlyDuplicates ? 'default' : 'outline'}
                    className="h-8 w-8 flex-shrink-0"
                    onClick={() => setOnlyDuplicates((v) => !v)}
                    disabled={duplicates.groupCount === 0}
                    aria-label="Mostrar solo archivos repetidos"
                    aria-pressed={onlyDuplicates}
                  >
                    <Copy className="h-3.5 w-3.5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>
                  {duplicates.groupCount === 0 ? 'No hay archivos repetidos' : 'Mostrar solo archivos repetidos'}
                </TooltipContent>
              </Tooltip>
            </div>
          </div>

          {/* Selection toolbar */}
          {docs.length > 0 && (
            <div className="flex flex-shrink-0 flex-wrap items-center gap-x-2 gap-y-1.5 border-b bg-muted/40 px-3 py-2">
              <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <TriCheckbox
                  checked={allVisibleSelected}
                  indeterminate={someVisibleSelected}
                  disabled={visibleIds.length === 0}
                  onChange={(e) => (e.target.checked ? selectAllVisible() : clearSelection())}
                  label={allVisibleSelected ? 'Quitar la selección de todos los documentos' : 'Seleccionar todos los documentos visibles'}
                />
                <span>{onlyDuplicates ? 'Seleccionar los repetidos' : 'Seleccionar todo'}</span>
              </label>

              {selectedCount > 0 ? (
                <>
                  <span className="text-xs font-medium text-foreground">{selectedCount} seleccionado{selectedCount === 1 ? '' : 's'}</span>
                  <div className="ml-auto flex items-center gap-1">
                    <Button size="xs" variant="outline" onClick={() => bulkSetIncluded(true)}>Incluir</Button>
                    <Button size="xs" variant="outline" onClick={() => bulkSetIncluded(false)}>Excluir</Button>
                    <Button size="xs" variant="outline" onClick={bulkRemove}>Quitar de la lista</Button>
                    <Button size="xs" variant="ghost" onClick={clearSelection}>Limpiar</Button>
                  </div>
                </>
              ) : (
                <span className="hidden text-[11px] text-muted-foreground/80 xl:inline">
                  Ctrl + clic para sumar · Shift + clic para un rango
                </span>
              )}
            </div>
          )}

          {/* Empty-state dropzone */}
          {docs.length === 0 && (
            <div
              onDragOver={(e: React.DragEvent) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              className={`m-3 rounded-xl border-2 border-dashed p-6 text-center transition-colors ${dragOver ? 'border-primary bg-primary/5' : 'border-border'}`}
            >
              <Upload className={`mx-auto mb-2 h-8 w-8 ${dragOver ? 'text-primary' : 'text-muted-foreground/50'}`} />
              <p className="text-sm font-medium">Arrastrá tus PDF aquí</p>
              <p className="mt-1 text-xs text-muted-foreground">o elegí archivos o una carpeta desde tu equipo</p>
              <div className="mt-3 flex justify-center gap-2">
                <Button size="sm" variant="outline" onClick={() => fileInputRef.current?.click()}>Elegir archivos</Button>
                <Button size="sm" variant="outline" onClick={() => folderInputRef.current?.click()}>Elegir carpeta</Button>
              </div>
            </div>
          )}

          {/* Virtualized document list */}
          <div ref={listParentRef} className="min-h-0 flex-1 overflow-auto p-2">
            {filteredDocs.length > 0 && (
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
                <SortableContext items={filteredDocs.map((d) => d.id)} strategy={verticalListSortingStrategy}>
                  <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
                    {virtualizer.getVirtualItems().map((vi) => {
                      const doc = filteredDocs[vi.index];
                      return (
                        <div
                          key={doc.id}
                          style={{ position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${vi.start}px)` }}
                        >
                          <div style={{ paddingBottom: 4 }}>
                            <DocumentRow
                              doc={doc}
                              rowIndex={vi.index}
                              tabIndex={vi.index === (focusIndex === -1 ? 0 : focusIndex) ? 0 : -1}
                              selected={selectedIds.has(doc.id)}
                              duplicateGroup={duplicates.groupSize.get(doc.id) ?? null}
                              onSelect={(e) => handleRowSelect(doc.id, e)}
                              onToggleSelect={() => toggleRowSelection(doc.id)}
                              onRemove={() => removeDoc(doc.id)}
                              onToggle={() => toggleDoc(doc.id)}
                              onKeyDown={(e) => onRowKeyDown(vi.index, doc, e)}
                              onFocus={() => { setFocusIndex(vi.index); setPreviewId(doc.id); }}
                            />
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </SortableContext>
              </DndContext>
            )}
            {docs.length > 0 && filteredDocs.length === 0 && (
              <div className="py-8 text-center text-sm text-muted-foreground">No se encontraron documentos.</div>
            )}
          </div>

          {/* Compact drop hint when there are docs */}
          {docs.length > 0 && (
            <div
              onDragOver={(e: React.DragEvent) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              className={`mx-3 mb-2 rounded-lg border border-dashed px-3 py-2 text-center text-xs transition-colors ${dragOver ? 'border-primary bg-primary/5 text-primary' : 'border-border text-muted-foreground'}`}
            >
              <Upload className="mr-1 inline h-3 w-3" /> Arrastrá más PDF aquí
            </div>
          )}
        </div>

        {/* Preview panel */}
        <div className="flex min-w-0 flex-1 flex-col bg-muted/40">
          <div className="flex min-h-0 flex-1 flex-col p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Previsualización</h2>
              {selectedDoc && (
                <span className="max-w-[320px] truncate text-xs text-muted-foreground" title={selectedDoc.name}>{selectedDoc.name}</span>
              )}
            </div>
            <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
              <CardContent className="flex min-h-0 flex-1 flex-col p-4">
                {selectedDoc ? (
                  <>
                    <div className="mb-3 flex items-center justify-between gap-2">
                      <span className="truncate text-sm font-medium" title={selectedDoc.name}>{selectedDoc.name}</span>
                      <span className="flex-shrink-0 text-xs text-muted-foreground">Página {previewPage} de {selectedDoc.page_count ?? '—'}</span>
                    </div>
                    <div className="flex min-h-0 flex-1 items-center justify-center overflow-auto rounded-lg bg-muted/60 p-3">
                      <img
                        src={`/api/documents/${selectedDoc.id}/preview/${previewPage}`}
                        alt={`Vista previa de ${selectedDoc.name}`}
                        className="max-h-full max-w-full rounded shadow-sm"
                        style={{ zoom: previewZoom }}
                      />
                    </div>
                    <div className="mt-3 flex items-center justify-center gap-2">
                      <Button variant="outline" size="icon-sm" disabled={previewPage <= 1} onClick={() => setPreviewPage((p) => Math.max(1, p - 1))} aria-label="Página anterior">
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <span className="min-w-[72px] text-center text-sm font-medium tabular-nums text-muted-foreground">{previewPage} / {selectedDoc.page_count ?? '—'}</span>
                      <Button variant="outline" size="icon-sm" disabled={!selectedDoc.page_count || previewPage >= (selectedDoc.page_count || 1)} onClick={() => setPreviewPage((p) => p + 1)} aria-label="Página siguiente">
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                      <div className="ml-4 flex items-center gap-1">
                        <Button variant="ghost" size="icon-sm" onClick={() => setPreviewZoom((z) => Math.max(0.5, +(z - 0.25).toFixed(2)))} aria-label="Alejar">−</Button>
                        <span className="w-11 text-center text-xs tabular-nums text-muted-foreground">{Math.round(previewZoom * 100)}%</span>
                        <Button variant="ghost" size="icon-sm" onClick={() => setPreviewZoom((z) => Math.min(3, +(z + 0.25).toFixed(2)))} aria-label="Acercar">+</Button>
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="flex flex-1 flex-col items-center justify-center gap-2 text-muted-foreground">
                    <Eye className="h-12 w-12 opacity-25" />
                    <span className="text-sm">Seleccioná un documento para previsualizar.</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Output bar */}
      <div className="flex-shrink-0 border-t bg-card px-5 py-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[200px] flex-1 space-y-1">
            <label className="text-xs font-medium text-muted-foreground" htmlFor="out-name">Nombre del archivo final</label>
            <Input id="out-name" value={outputName} onChange={(e) => setOutputName(e.target.value)} placeholder="documentos_unidos.pdf" className="h-9 text-sm" />
          </div>
          <div className="min-w-[260px] flex-1 space-y-1">
            <label className="text-xs font-medium text-muted-foreground" htmlFor="out-dir">Carpeta de destino</label>
            <div className="flex gap-2">
              <Input id="out-dir" value={outputDir} onChange={(e) => setOutputDir(e.target.value)} placeholder="Vacío = carpeta Descargas" className="h-9 flex-1 text-sm" title={outputDir || 'Vacío = carpeta Descargas'} />
              <Button variant="outline" className="h-9 flex-shrink-0" onClick={pickFolder} aria-label="Elegir carpeta de destino">
                <FolderOpen className="mr-1.5 h-4 w-4" /> Elegir carpeta…
              </Button>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <label
              className="flex h-9 cursor-pointer select-none items-center gap-1.5 text-xs text-muted-foreground"
              title="Si ya existe un PDF con ese nombre, lo reemplaza"
            >
              <input
                type="checkbox"
                checked={overwrite}
                onChange={(e) => setOverwrite(e.target.checked)}
                className="h-3.5 w-3.5 accent-primary"
              />
              Sobrescribir si ya existe
            </label>
            <Button variant="outline" className="h-9" onClick={saveAs} disabled={jobStatus === 'running'}>
              <Save className="mr-1.5 h-4 w-4" /> Guardar como…
            </Button>
            <Button className="h-9" onClick={() => startMerge()} disabled={includedCount === 0 || jobStatus === 'running'}>
              {jobStatus === 'running' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Merge className="mr-2 h-4 w-4" />}
              {jobStatus === 'running' ? 'Uniendo…' : `Unir ${includedCount} documento${includedCount === 1 ? '' : 's'}`}
            </Button>
          </div>
        </div>

        {hasInvalid && (
          <div className="mt-2 flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400">
            <AlertTriangle className="h-3.5 w-3.5" /> Hay documentos con problemas incluidos en el lote. Revisá los estados antes de unir.
          </div>
        )}

        {jobStatus !== 'idle' && jobStatus !== 'completed' && jobStatus !== 'completed_with_errors' && (
          <div className="mt-3 space-y-2">
            <Progress value={progress} className="h-2" />
            <div className="flex items-center justify-between text-xs">
              <span className="truncate text-muted-foreground">
                Etapa: <strong className="text-foreground">{stage || 'preparando'}</strong>
                {currentFile && <span className="ml-2 text-muted-foreground/70">{currentFile}</span>}
              </span>
              <span className="font-semibold tabular-nums text-primary">{Math.round(progress)}%</span>
            </div>
            {jobStatus === 'running' && (
              <Button variant="destructive" size="sm" onClick={cancelMerge}>
                <Square className="mr-1.5 h-3.5 w-3.5" /> Cancelar
              </Button>
            )}
          </div>
        )}
      </div>

      {/* Keyboard shortcuts help */}
      <ShortcutsDialog open={showShortcuts} onOpenChange={setShowShortcuts} />

      {/* Clear confirm */}
      <Dialog open={showClearConfirm} onOpenChange={setShowClearConfirm}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle>¿Limpiar el lote?</DialogTitle>
            <DialogDescription>
              Se quitarán los {docs.length} documentos de la lista. Los archivos originales no se modificarán.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" size="sm" onClick={() => setShowClearConfirm(false)}>Cancelar</Button>
            <Button variant="destructive" size="sm" onClick={clearLot}>Limpiar lote</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Merge result */}
      <Dialog open={showResult} onOpenChange={setShowResult}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {result?.status === 'completed' ? (
                <><CheckCircle className="h-5 w-5 text-emerald-600 dark:text-emerald-400" /> Unión completada</>
              ) : result?.status === 'completed_with_errors' ? (
                <><AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" /> Completado con errores</>
              ) : result?.status === 'cancelled' ? (
                <><CircleSlash className="h-5 w-5 text-muted-foreground" /> Unión cancelada</>
              ) : (
                <><AlertTriangle className="h-5 w-5 text-destructive" /> La unión falló</>
              )}
            </DialogTitle>
            <DialogDescription>
              {result && (
                <>
                  {result.processed_documents} documentos · {result.total_pages} páginas · {result.elapsed_seconds}s
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          {result?.output_path && (
            <div className="rounded-lg border bg-muted/50 px-3 py-2">
              <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Archivo generado</div>
              <div className="mt-0.5 break-all text-xs">{result.output_path}</div>
            </div>
          )}

          {result && result.errors.length > 0 && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              <div className="mb-1 font-medium">{result.errors.length} problema(s):</div>
              <ul className="list-disc space-y-0.5 pl-4">
                {result.errors.slice(0, 6).map((err, i) => <li key={i}>{err.message}</li>)}
              </ul>
            </div>
          )}

          <DialogFooter>
            {destExists && (
              <Button size="sm" onClick={() => { setOverwrite(true); setShowResult(false); startMerge(true); }}>
                <Merge className="mr-1.5 h-4 w-4" /> Sobrescribir y unir
              </Button>
            )}
            {result?.output_path && (
              <>
                <Button variant="outline" size="sm" onClick={() => reveal(result.output_path!)}>
                  <FolderOpen className="mr-1.5 h-4 w-4" /> Abrir carpeta
                </Button>
                <Button size="sm" onClick={() => reveal(result.output_path!)}>
                  <ExternalLink className="mr-1.5 h-4 w-4" /> Abrir PDF
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Hidden inputs */}
      <input ref={fileInputRef} type="file" accept="application/pdf" multiple hidden
        onChange={(e) => { if (e.target.files) handleFiles(Array.from(e.target.files)); e.target.value = ''; }} />
      <input ref={folderInputRef} type="file" accept="application/pdf" multiple hidden
        // @ts-ignore
        webkitdirectory=""
        onChange={(e) => { if (e.target.files) handleFiles(Array.from(e.target.files)); e.target.value = ''; }} />
    </div>
  );
}
