import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Upload, FolderOpen, Eye, Trash2, Check, X, Square, FileText, Loader2,
  Files, HardDrive, ChevronLeft, ChevronRight, Merge, CheckCircle,
  Search, Trash, Settings, HelpCircle, Plus, GripVertical, ExternalLink,
  AlertTriangle, CircleSlash, Save,
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

function IconButton({ label, onClick, disabled, children }: {
  label: string; onClick: (e: React.MouseEvent) => void; disabled?: boolean; children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button size="icon-sm" variant="ghost" onClick={onClick} disabled={disabled} aria-label={label}>
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

function DocumentRow({ doc, selected, onSelect, onRemove, onToggle }: {
  doc: PdfDocument; selected: boolean; onSelect: () => void; onRemove: () => void; onToggle: () => void;
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
      onClick={onSelect}
      className={`flex h-14 items-center gap-2.5 rounded-lg border px-2.5 transition-colors cursor-pointer
        ${selected ? 'border-primary/40 bg-accent/5 ring-1 ring-primary/25' : 'border-transparent hover:bg-muted/60'}
        ${doc.included ? '' : 'opacity-55'}
        ${isDragging ? 'shadow-lg bg-card border-primary/40' : ''}`}
    >
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
      <div className="h-11 w-8 flex-shrink-0 overflow-hidden rounded border border-border/60 bg-muted">
        <img
          src={`/api/documents/${doc.id}/preview/1`}
          alt=""
          loading="lazy"
          className="h-full w-full object-cover"
          onError={(e) => { (e.target as HTMLImageElement).style.visibility = 'hidden'; }}
        />
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
          onClick={(e) => { e.stopPropagation(); onToggle(); }}
        >
          {doc.included ? <Check className="h-4 w-4 text-emerald-600" /> : <X className="h-4 w-4" />}
        </IconButton>
        <IconButton
          label="Quitar de la lista"
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
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [previewPage, setPreviewPage] = useState(1);
  const [previewZoom, setPreviewZoom] = useState(1);
  const [uploading, setUploading] = useState(false);
  const [outputDir, setOutputDir] = useState('');
  const [outputName, setOutputName] = useState('documentos_unidos.pdf');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortMode, setSortMode] = useState<SortMode>('manual');
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<string>('idle');
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState<string>('');
  const [currentFile, setCurrentFile] = useState<string>('');
  const [result, setResult] = useState<MergeResult | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const listParentRef = useRef<HTMLDivElement>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const refresh = useCallback(async () => {
    const r = await api.listDocuments();
    setDocs(r.documents as PdfDocument[]);
  }, []);
  useEffect(() => { refresh(); }, [refresh]);

  const selectedDoc = docs.find((d) => d.id === selectedId) || null;
  useEffect(() => { if (selectedDoc) { setPreviewPage(1); setPreviewZoom(1); } }, [selectedId]);

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

  const removeDoc = async (id: string) => { await api.removeDocument(id); if (selectedId === id) setSelectedId(null); await refresh(); };
  const toggleDoc = async (id: string) => { const d = docs.find((x) => x.id === id); if (!d) return; await api.updateDocument(id, { included: !d.included }); await refresh(); };
  const clearLot = async () => { for (const d of docs) await api.removeDocument(d.id); setDocs([]); setSelectedId(null); setShowClearConfirm(false); await refresh(); };

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

  const startMerge = async () => {
    setResult(null); setShowResult(false); setJobStatus('starting'); setProgress(0);
    try {
      const combined = outputDir.trim()
        ? `${outputDir.trim().replace(/[\\/]+$/, '')}\\${outputName.trim() || 'documentos_unidos.pdf'}`
        : (outputName.trim() || undefined);
      const r = await api.startMerge(combined, false);
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
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter((d) => d.name.toLowerCase().includes(q));
    }
    if (sortMode === 'name') list = [...list].sort((a, b) => a.name.localeCompare(b.name));
    else if (sortMode === 'size') list = [...list].sort((a, b) => b.size_bytes - a.size_bytes);
    else if (sortMode === 'pages') list = [...list].sort((a, b) => (b.page_count || 0) - (a.page_count || 0));
    return list;
  }, [docs, searchQuery, sortMode]);

  const virtualizer = useVirtualizer({
    count: filteredDocs.length,
    getScrollElement: () => listParentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  });

  const totalFiles = docs.length;
  const includedCount = docs.filter((d) => d.included).length;
  const totalPages = docs.reduce((a, d) => a + (d.included ? (d.page_count || 0) : 0), 0);
  const totalBytes = docs.reduce((a, d) => a + (d.included ? d.size_bytes : 0), 0);
  const hasInvalid = docs.some((d) => d.included && (d.status === 'invalid' || d.status === 'failed'));

  const summary = [
    { icon: Files, value: String(totalFiles), label: 'archivos' },
    { icon: FileText, value: String(totalPages), label: 'páginas' },
    { icon: HardDrive, value: formatBytes(totalBytes), label: 'tamaño' },
    { icon: Check, value: String(includedCount), label: 'incluidos', tone: 'text-emerald-600' },
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
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label="Ayuda"><HelpCircle className="h-4 w-4" /></Button>
            </TooltipTrigger>
            <TooltipContent>Ayuda</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon-sm" aria-label="Ajustes"><Settings className="h-4 w-4" /></Button>
            </TooltipTrigger>
            <TooltipContent>Ajustes</TooltipContent>
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
            </div>
          </div>

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
                              selected={doc.id === selectedId}
                              onSelect={() => setSelectedId(doc.id)}
                              onRemove={() => removeDoc(doc.id)}
                              onToggle={() => toggleDoc(doc.id)}
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
          <div className="flex items-center gap-2">
            <Button variant="outline" className="h-9" onClick={saveAs} disabled={jobStatus === 'running'}>
              <Save className="mr-1.5 h-4 w-4" /> Guardar como…
            </Button>
            <Button className="h-9" onClick={startMerge} disabled={includedCount === 0 || jobStatus === 'running'}>
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
                <><CheckCircle className="h-5 w-5 text-emerald-600" /> Unión completada</>
              ) : result?.status === 'completed_with_errors' ? (
                <><AlertTriangle className="h-5 w-5 text-amber-600" /> Completado con errores</>
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

          {result && result.error_count > 0 && (
            <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              <div className="mb-1 font-medium">{result.error_count} documento(s) con errores:</div>
              <ul className="list-disc space-y-0.5 pl-4">
                {result.errors.slice(0, 6).map((err, i) => <li key={i}>{err.message}</li>)}
              </ul>
            </div>
          )}

          <DialogFooter>
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
