import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Upload, FolderOpen, Eye, Square, FileText, Loader2,
  Files, HardDrive, ChevronLeft, ChevronRight, Merge, CheckCircle,
  Search, Trash, HelpCircle, Plus, ExternalLink,
  AlertTriangle, CircleSlash, Save, Copy, Check,
} from 'lucide-react';

import { DndContext, closestCenter, KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable';
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

import { api } from '@/lib/api';
import type { PdfDocument } from '@/lib/api';
import { ThemeToggle } from '@/components/theme-toggle';
import { ShortcutsDialog } from '@/components/shortcuts-dialog';
import { TriCheckbox } from '@/components/tri-checkbox';
import { DocumentRow } from '@/features/merge/DocumentRow';
import { findDuplicates } from '@/features/merge/duplicates';
import { formatBytes } from '@/features/merge/document-meta';
import { useDocumentSelection, usePruneSelection } from '@/features/merge/use-document-selection';
import { useMergeSession } from '@/features/merge/use-merge-session';
import { useSplitSession } from '@/features/split/use-split-session';
import { OrganizerPanel } from '@/features/organizer/OrganizerPanel';
import { ConvertPanel } from '@/features/convert/ConvertPanel';
import { JobsPanel } from '@/features/queue/JobsPanel';
import { RenameDialog } from '@/features/rename/RenameDialog';
import { SearchPanel } from '@/features/search/SearchPanel';
import { useGlobalShortcuts } from '@/lib/hooks/use-global-shortcuts';

type SortMode = 'manual' | 'name' | 'size' | 'pages';

const ROW_HEIGHT = 64;

export default function AppShell() {
  const [outputDir, setOutputDir] = useState('');
  const [outputName, setOutputName] = useState('documentos_unidos.pdf');
  const [overwrite, setOverwrite] = useState(false);
  const [view, setView] = useState<'merge' | 'split' | 'organize' | 'convert' | 'jobs' | 'search'>('merge');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortMode, setSortMode] = useState<SortMode>('manual');
  const [onlyDuplicates, setOnlyDuplicates] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [showRename, setShowRename] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [focusIndex, setFocusIndex] = useState(-1);
  const [previewPage, setPreviewPage] = useState(1);
  const [previewZoom, setPreviewZoom] = useState(1);
  // Región viva: anuncia por lector de pantalla el resultado de las acciones de lote.
  const [liveMessage, setLiveMessage] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const listParentRef = useRef<HTMLDivElement>(null);

  const announce = useCallback((message: string) => setLiveMessage(message), []);

  const session = useMergeSession({ outputDir, outputName, overwrite, announce });
  // Autoguardado y restauración de la sesión.
  useEffect(() => {
    api.autorestoreSession().then((r) => { if (r.restored) void session.refresh(); }).catch(() => {});
    const id = window.setInterval(() => { void api.autosaveSession().catch(() => {}); }, 60000);
    return () => window.clearInterval(id);
  }, [session.refresh]);
  const docs = session.docs;
  const split = useSplitSession({ outputDir, announce });

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const duplicates = useMemo(() => findDuplicates(docs), [docs]);

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

  const selection = useDocumentSelection({
    visibleIds,
    refresh: session.refresh,
    announce,
  });

  usePruneSelection(docs, selection.setSelectedIds, selection.setPreviewId);

  const organizeDocId = selection.previewId || (docs.length ? docs[0].id : null);

  // Si se quitan documentos del lote, la selección y la previsualización se ajustan solas.
  const selectedDoc = docs.find((d) => d.id === selection.previewId) || null;
  useEffect(() => { if (selection.previewId) { setPreviewPage(1); setPreviewZoom(1); } }, [selection.previewId]);

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
      await session.refresh();
      announce(`${toExclude.length} ${toExclude.length === 1 ? 'archivo repetido excluido' : 'archivos repetidos excluidos'} del lote.`);
    } catch (e) { alert('No se pudieron excluir los repetidos: ' + (e as Error).message); }
  };

  const includeAllDuplicates = async () => {
    const toInclude = docs.filter((d) => duplicates.flagged.has(d.id) && !d.included).map((d) => d.id);
    if (!toInclude.length) return;
    try {
      await Promise.all(toInclude.map((id) => api.updateDocument(id, { included: true })));
      await session.refresh();
      announce(`${toInclude.length} ${toInclude.length === 1 ? 'archivo repetido incluido' : 'archivos repetidos incluidos'} de nuevo en el lote.`);
    } catch (e) { alert('No se pudieron incluir los repetidos: ' + (e as Error).message); }
  };

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

  const handleClearLot = async () => {
    const removed = await session.clearLot();
    selection.clearSelection();
    selection.setPreviewId(null);
    setShowClearConfirm(false);
    announce(`Se quitaron ${removed} documentos de la lista.`);
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
    else if (e.key === ' ' || e.key === 'Spacebar') { e.preventDefault(); selection.toggleRowSelection(doc.id); }
    else if (e.key === 'Enter') { e.preventDefault(); selection.handleRowSelect(doc.id, e as unknown as React.MouseEvent); }
  };

  const totalFiles = docs.length;
  const includedCount = docs.filter((d) => d.included).length;
  const totalPages = docs.reduce((a, d) => a + (d.included ? (d.page_count || 0) : 0), 0);
  const totalBytes = docs.reduce((a, d) => a + (d.included ? d.size_bytes : 0), 0);
  const hasInvalid = docs.some((d) => d.included && (d.status === 'invalid' || d.status === 'failed'));
  const destExists = session.result?.errors?.some((e) => /ya existe/i.test(e.message)) ?? false;

  useGlobalShortcuts({
    openFiles: () => fileInputRef.current?.click(),
    selectAll: selection.selectAllVisible,
    clearSelection: selection.clearSelection,
    removeSelected: () => { void selection.bulkRemove(); },
    merge: () => { void session.startMerge(); },
    openShortcuts: () => setShowShortcuts(true),
    canSelectAll: visibleIds.length > 0,
    hasSelection: selection.selectedCount > 0,
    canMerge: includedCount > 0 && session.jobStatus !== 'running',
    dialogOpen: showClearConfirm || session.showResult || showShortcuts,
  });

  const summary = [
    { icon: Files, value: String(totalFiles), label: 'archivos' },
    { icon: FileText, value: String(totalPages), label: 'páginas' },
    { icon: HardDrive, value: formatBytes(totalBytes), label: 'tamaño' },
    { icon: Check, value: String(includedCount), label: 'incluidos', tone: 'text-emerald-600 dark:text-emerald-400' },
  ];

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background text-foreground">
      {/* Anuncios para lectores de pantalla */}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">{liveMessage}</div>

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
      <section aria-labelledby="page-title" className="flex-shrink-0 border-b bg-card/40 px-5 py-3">
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="mb-2 flex gap-1.5">
              <Button size="sm" variant={view === 'merge' ? 'default' : 'outline'} onClick={() => setView('merge')}>Unir</Button>
              <Button size="sm" variant={view === 'split' ? 'default' : 'outline'} onClick={() => setView('split')}>Dividir</Button>
              <Button size="sm" variant={view === 'organize' ? 'default' : 'outline'} onClick={() => setView('organize')}>Organizar</Button>
              <Button size="sm" variant={view === 'convert' ? 'default' : 'outline'} onClick={() => setView('convert')}>Convertir</Button>
              <Button size="sm" variant={view === 'jobs' ? 'default' : 'outline'} onClick={() => setView('jobs')}>Cola</Button>
              <Button size="sm" variant={view === 'search' ? 'default' : 'outline'} onClick={() => setView('search')}>Buscar</Button>
              <Button size="sm" variant="outline" onClick={() => setShowRename(true)}>Renombrar lote</Button>
            </div>
            <h1 id="page-title" className="text-xl font-semibold tracking-tight">{view === 'split' ? 'Dividir PDF' : 'Unir documentos PDF'}</h1>
            <p className="text-sm text-muted-foreground">{view === 'split' ? 'Dividí un PDF en varios archivos por rangos, cada N páginas o página por página.' : 'Organizá tus archivos, revisá su contenido y generá un único documento.'}</p>
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
      </section>

      {/* Workspace */}
      <main className="flex min-h-0 flex-1 flex-col md:flex-row">
        {/* Document panel */}
        <div className="flex w-full flex-col border-r bg-card md:w-[38%] md:min-w-[340px] md:max-w-[500px]">
          <div className="flex-shrink-0 space-y-2 border-b p-3">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Documentos</h2>
              <span className="text-xs text-muted-foreground">{filteredDocs.length} de {docs.length}</span>
            </div>
            <div className="flex gap-2">
              <Button size="sm" className="flex-1" onClick={() => fileInputRef.current?.click()} disabled={session.uploading}>
                {session.uploading ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : <Plus className="mr-1.5 h-3.5 w-3.5" />}
                Agregar PDF
              </Button>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button size="icon" variant="outline" onClick={() => folderInputRef.current?.click()} disabled={session.uploading} aria-label="Agregar carpeta">
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
                  checked={selection.allVisibleSelected}
                  indeterminate={selection.someVisibleSelected}
                  disabled={visibleIds.length === 0}
                  onChange={(e) => (e.target.checked ? selection.selectAllVisible() : selection.clearSelection())}
                  label={selection.allVisibleSelected ? 'Quitar la selección de todos los documentos' : 'Seleccionar todos los documentos visibles'}
                />
                <span>{onlyDuplicates ? 'Seleccionar los repetidos' : 'Seleccionar todo'}</span>
              </label>

              {selection.selectedCount > 0 ? (
                <>
                  <span className="text-xs font-medium text-foreground">{selection.selectedCount} seleccionado{selection.selectedCount === 1 ? '' : 's'}</span>
                  <div className="ml-auto flex items-center gap-1">
                    <Button size="xs" variant="outline" onClick={() => selection.bulkSetIncluded(true)}>Incluir</Button>
                    <Button size="xs" variant="outline" onClick={() => selection.bulkSetIncluded(false)}>Excluir</Button>
                    <Button size="xs" variant="outline" onClick={selection.bulkRemove}>Quitar de la lista</Button>
                    <Button size="xs" variant="ghost" onClick={selection.clearSelection}>Limpiar</Button>
                  </div>
                </>
              ) : (
                <span className="hidden text-[11px] text-muted-foreground xl:inline">
                  Ctrl + clic para sumar · Shift + clic para un rango
                </span>
              )}
            </div>
          )}

          {/* Empty-state dropzone */}
          {docs.length === 0 && (
            <div
              onDragOver={(e: React.DragEvent) => { e.preventDefault(); session.setDragOver(true); }}
              onDragLeave={() => session.setDragOver(false)}
              onDrop={session.onDrop}
              className={`m-3 rounded-xl border-2 border-dashed p-6 text-center transition-colors ${session.dragOver ? 'border-primary bg-primary/5' : 'border-border'}`}
            >
              <Upload className={`mx-auto mb-2 h-8 w-8 ${session.dragOver ? 'text-primary' : 'text-muted-foreground/50'}`} />
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
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={session.onDragEnd}>
                <SortableContext items={filteredDocs.map((d) => d.id)} strategy={verticalListSortingStrategy}>
                  <div
                    role="list"
                    aria-label={onlyDuplicates ? 'Documentos repetidos del lote' : 'Documentos del lote'}
                    aria-busy={session.uploading}
                    style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}
                  >
                    {virtualizer.getVirtualItems().map((vi) => {
                      const doc = filteredDocs[vi.index];
                      return (
                        <div
                          key={doc.id}
                          role="presentation"
                          style={{ position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${vi.start}px)` }}
                        >
                          <div role="presentation" style={{ paddingBottom: 4 }}>
                            <DocumentRow
                              doc={doc}
                              rowIndex={vi.index}
                              tabIndex={vi.index === (focusIndex === -1 ? 0 : focusIndex) ? 0 : -1}
                              selected={selection.selectedIds.has(doc.id)}
                              duplicateGroup={duplicates.groupSize.get(doc.id) ?? null}
                              onSelect={(e) => selection.handleRowSelect(doc.id, e)}
                              onToggleSelect={() => selection.toggleRowSelection(doc.id)}
                              onRemove={() => session.removeDoc(doc.id)}
                              onToggle={() => session.toggleDoc(doc.id)}
                              onKeyDown={(e) => onRowKeyDown(vi.index, doc, e)}
                              onFocus={() => { setFocusIndex(vi.index); selection.setPreviewId(doc.id); }}
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
              <div role="status" className="py-8 text-center text-sm text-muted-foreground">No se encontraron documentos.</div>
            )}
          </div>

          {/* Compact drop hint when there are docs */}
          {docs.length > 0 && (
            <div
              onDragOver={(e: React.DragEvent) => { e.preventDefault(); session.setDragOver(true); }}
              onDragLeave={() => session.setDragOver(false)}
              onDrop={session.onDrop}
              className={`mx-3 mb-2 rounded-lg border border-dashed px-3 py-2 text-center text-xs transition-colors ${session.dragOver ? 'border-primary bg-primary/5 text-primary' : 'border-border text-muted-foreground'}`}
            >
              <Upload className="mr-1 inline h-3 w-3" /> Arrastrá más PDF aquí
            </div>
          )}
        </div>

        {view === 'organize' ? (
        <div className="flex min-w-0 flex-1 flex-col bg-muted/40">
          <OrganizerPanel documentId={organizeDocId} outputDir={outputDir} announce={announce} />
        </div>
        ) : view === 'convert' ? (
        <div className="flex min-w-0 flex-1 flex-col bg-muted/40">
          <ConvertPanel docs={docs} outputDir={outputDir} announce={announce} />
        </div>
        ) : view === 'jobs' ? (
        <div className="flex min-w-0 flex-1 flex-col bg-muted/40">
          <JobsPanel announce={announce} />
        </div>
        ) : view === 'search' ? (
        <div className="flex min-w-0 flex-1 flex-col bg-muted/40">
          <SearchPanel announce={announce} />
        </div>
        ) : (
        <div className="flex min-w-0 flex-1 flex-col bg-muted/40">
          <div className="flex min-h-0 flex-1 flex-col p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-foreground/70">Previsualización</h2>
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
        )}

      </main>

      {view === 'merge' || view === 'organize' ? (
      <footer className="flex-shrink-0 border-t bg-card px-5 py-3">
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
            <Button variant="outline" className="h-9" onClick={saveAs} disabled={session.jobStatus === 'running'}>
              <Save className="mr-1.5 h-4 w-4" /> Guardar como…
            </Button>
            <Button className="h-9" onClick={() => session.startMerge()} disabled={includedCount === 0 || session.jobStatus === 'running'}>
              {session.jobStatus === 'running' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Merge className="mr-2 h-4 w-4" />}
              {session.jobStatus === 'running' ? 'Uniendo…' : `Unir ${includedCount} documento${includedCount === 1 ? '' : 's'}`}
            </Button>
          </div>
        </div>

        {hasInvalid && (
          <div className="mt-2 flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400">
            <AlertTriangle className="h-3.5 w-3.5" /> Hay documentos con problemas incluidos en el lote. Revisá los estados antes de unir.
          </div>
        )}

        {session.jobStatus !== 'idle' && session.jobStatus !== 'completed' && session.jobStatus !== 'completed_with_errors' && (
          <div className="mt-3 space-y-2">
            <Progress value={session.progress} className="h-2" aria-label="Progreso de la unión" />
            <div className="flex items-center justify-between text-xs">
              <span className="truncate text-muted-foreground">
                Etapa: <strong className="text-foreground">{session.stage || 'preparando'}</strong>
                {session.currentFile && <span className="ml-2 text-muted-foreground/70">{session.currentFile}</span>}
              </span>
              <span className="font-semibold tabular-nums text-primary">{Math.round(session.progress)}%</span>
            </div>
            {session.jobStatus === 'running' && (
              <Button variant="destructive" size="sm" onClick={session.cancelMerge}>
                <Square className="mr-1.5 h-3.5 w-3.5" /> Cancelar
              </Button>
            )}
          </div>
        )}
      </footer>
      ) : (
      <footer className="flex-shrink-0 border-t bg-card px-5 py-3 space-y-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[160px] space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Modo</label>
            <Select value={split.mode} onValueChange={(v) => split.setMode(v as 'ranges' | 'every' | 'single')}>
              <SelectTrigger size="sm" className="w-[160px] text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="ranges">Rangos</SelectItem>
                <SelectItem value="every">Cada N páginas</SelectItem>
                <SelectItem value="single">Una página por archivo</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {split.mode === 'ranges' && (
            <div className="min-w-[220px] flex-1 space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Rangos (ej. 1-3, 5, 8-10)</label>
              <Input value={split.ranges} onChange={(e) => split.setRanges(e.target.value)} className="h-9 text-sm" />
            </div>
          )}
          {split.mode === 'every' && (
            <div className="min-w-[120px] space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Cada N páginas</label>
              <Input value={split.every} onChange={(e) => split.setEvery(e.target.value)} className="h-9 text-sm" />
            </div>
          )}
          <div className="min-w-[220px] flex-1 space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Plantilla de nombre</label>
            <Input value={split.template} onChange={(e) => split.setTemplate(e.target.value)} className="h-9 text-sm" />
          </div>
          <div className="min-w-[160px] space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Colisión</label>
            <Select value={split.collisionPolicy} onValueChange={(v) => split.setCollisionPolicy(v as 'suffix' | 'fail' | 'overwrite')}>
              <SelectTrigger size="sm" className="w-[160px] text-xs"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="suffix">Sufijo (_2)</SelectItem>
                <SelectItem value="fail">Fallar</SelectItem>
                <SelectItem value="overwrite">Sobrescribir</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="min-w-[220px] flex-1 space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Carpeta de salida</label>
            <div className="flex gap-2">
              <Input value={outputDir} onChange={(e) => setOutputDir(e.target.value)} placeholder="Vacío = junto al origen" className="h-9 flex-1 text-sm" />
              <Button variant="outline" className="h-9 flex-shrink-0" onClick={pickFolder} aria-label="Elegir carpeta de destino">
                <FolderOpen className="mr-1.5 h-4 w-4" /> Elegir…
              </Button>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={split.preview} disabled={split.previewing || split.docs.length === 0}>
            {split.previewing ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : null} Vista previa
          </Button>
          <Button size="sm" onClick={split.startSplit} disabled={split.docs.length === 0 || split.jobStatus === 'running'}>
            {split.jobStatus === 'running' ? <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" /> : null}
            {split.jobStatus === 'running' ? 'Dividiendo…' : 'Dividir'}
          </Button>
          {split.jobStatus === 'running' && (
            <Button variant="destructive" size="sm" onClick={split.cancelSplit}>
              <Square className="mr-1.5 h-3.5 w-3.5" /> Cancelar
            </Button>
          )}
        </div>
        {split.previewError && <div className="text-xs text-destructive">{split.previewError}</div>}
        {split.plan && (
          <div className="rounded-lg border bg-muted/40 p-3 text-xs space-y-1">
            <div className="font-medium">{split.plan.summary.total_files ?? 0} archivos · {split.plan.summary.total_pages ?? 0} páginas</div>
            {split.plan.warnings.map((w, i) => <div key={i} className="text-amber-700 dark:text-amber-400">{w.message}</div>)}
            {split.plan.errors.map((e, i) => <div key={i} className="text-destructive">{e.message}</div>)}
            <ul className="list-disc pl-4 space-y-0.5">
              {split.plan.items.slice(0, 12).map((item) => (
                <li key={item.index}>{item.label} — {item.pages?.length ?? 0} pág.</li>
              ))}
              {split.plan.items.length > 12 && <li>… y {split.plan.items.length - 12} más</li>}
            </ul>
          </div>
        )}
        {split.jobStatus !== 'idle' && split.jobStatus !== 'completed' && split.jobStatus !== 'completed_with_errors' && split.jobStatus !== 'failed' && split.jobStatus !== 'cancelled' && (
          <div className="space-y-2">
            <Progress value={split.progress} className="h-2" aria-label="Progreso de la división" />
            <div className="flex items-center justify-between text-xs">
              <span className="truncate text-muted-foreground">
                Etapa: <strong className="text-foreground">{split.stage || 'preparando'}</strong>
                {split.currentFile && <span className="ml-2 text-muted-foreground/70">{split.currentFile}</span>}
              </span>
              <span className="font-semibold tabular-nums text-primary">{Math.round(split.progress)}%</span>
            </div>
          </div>
        )}
      </footer>
      )}

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
            <Button variant="destructive" size="sm" onClick={handleClearLot}>Limpiar lote</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Merge result */}
      <Dialog open={session.showResult} onOpenChange={session.setShowResult}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {session.result?.status === 'completed' ? (
                <><CheckCircle className="h-5 w-5 text-emerald-600 dark:text-emerald-400" /> Unión completada</>
              ) : session.result?.status === 'completed_with_errors' ? (
                <><AlertTriangle className="h-5 w-5 text-amber-600 dark:text-amber-400" /> Completado con errores</>
              ) : session.result?.status === 'cancelled' ? (
                <><CircleSlash className="h-5 w-5 text-muted-foreground" /> Unión cancelada</>
              ) : (
                <><AlertTriangle className="h-5 w-5 text-destructive" /> La unión falló</>
              )}
            </DialogTitle>
            <DialogDescription>
              {session.result && (
                <>
                  {session.result.processed_documents} documentos · {session.result.total_pages} páginas · {session.result.elapsed_seconds}s
                </>
              )}
            </DialogDescription>
          </DialogHeader>

          {session.result?.output_path && (
            <div className="rounded-lg border bg-muted/50 px-3 py-2">
              <div className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">Archivo generado</div>
              <div className="mt-0.5 break-all text-xs">{session.result.output_path}</div>
            </div>
          )}

          {session.result && session.result.errors.length > 0 && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              <div className="mb-1 font-medium">{session.result.errors.length} problema(s):</div>
              <ul className="list-disc space-y-0.5 pl-4">
                {session.result.errors.slice(0, 6).map((err, i) => <li key={i}>{err.message}</li>)}
              </ul>
            </div>
          )}

          <DialogFooter>
            {destExists && (
              <Button size="sm" onClick={() => { setOverwrite(true); session.setShowResult(false); session.startMerge(true); }}>
                <Merge className="mr-1.5 h-4 w-4" /> Sobrescribir y unir
              </Button>
            )}
            {session.result?.output_path && (
              <>
                <Button variant="outline" size="sm" onClick={() => reveal(session.result!.output_path!)}>
                  <FolderOpen className="mr-1.5 h-4 w-4" /> Abrir carpeta
                </Button>
                <Button size="sm" onClick={() => reveal(session.result!.output_path!)}>
                  <ExternalLink className="mr-1.5 h-4 w-4" /> Abrir PDF
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Split result */}
      <Dialog open={split.showResult} onOpenChange={split.setShowResult}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>División {String(split.result?.status ?? '')}</DialogTitle>
            <DialogDescription>
              {split.result && (
                <>
                  {String(split.result.total_files ?? 0)} archivos · {String(split.result.total_pages ?? 0)} páginas
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          {Array.isArray(split.result?.outputs) && (split.result!.outputs as string[]).length > 0 && (
            <div className="rounded-lg border bg-muted/50 px-3 py-2 text-xs break-all">
              {(split.result!.outputs as string[]).slice(0, 5).join('\\n')}
            </div>
          )}
          {Array.isArray(split.result?.errors) && (split.result!.errors as unknown[]).length > 0 && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              {(split.result!.errors as Array<{ message?: string }>).length} problema(s)
            </div>
          )}
          <DialogFooter>
            {(split.result as any)?.output_dirs && Array.isArray((split.result as any).output_dirs) && ((split.result as any).output_dirs as string[]).length > 0 && (
              <Button variant="outline" size="sm" onClick={() => reveal((split.result!.output_dirs as string[])[0])}>
                <FolderOpen className="mr-1.5 h-4 w-4" /> Abrir carpeta
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rename dialog */}
      <RenameDialog open={showRename} onOpenChange={setShowRename} onDone={() => { void session.refresh(); }} />

      {/* Hidden inputs */}
      <input ref={fileInputRef} type="file" accept="application/pdf" multiple hidden
        onChange={(e) => { if (e.target.files) session.handleFiles(Array.from(e.target.files)); e.target.value = ''; }} />
      <input ref={folderInputRef} type="file" accept="application/pdf" multiple hidden
        // @ts-ignore
        webkitdirectory=""
        onChange={(e) => { if (e.target.files) session.handleFiles(Array.from(e.target.files)); e.target.value = ''; }} />
    </div>
  );
}
