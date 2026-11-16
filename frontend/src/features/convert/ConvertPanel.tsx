import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import { api } from '@/lib/api';
import type { PdfDocument } from '@/lib/api';

interface ConvertPanelProps {
  docs: PdfDocument[];
  outputDir: string;
  announce: (message: string) => void;
}

type Mode = 'pdf-to-images' | 'images-to-pdf' | 'extract-text' | 'edit-metadata' | 'compress' | 'watermark' | 'page-numbers';

export function ConvertPanel({ docs, outputDir, announce }: ConvertPanelProps) {
  const [mode, setMode] = useState<Mode>('pdf-to-images');
  const [docId, setDocId] = useState<string>('');
  const [format, setFormat] = useState('png');
  const [dpi, setDpi] = useState('150');
  const [outDir, setOutDir] = useState(outputDir);
  const [imagePaths, setImagePaths] = useState<string[]>([]);
  const [rotation, setRotation] = useState('0');
  const [title, setTitle] = useState('');
  const [author, setAuthor] = useState('');
  const [subject, setSubject] = useState('');
  const [keywords, setKeywords] = useState('');
  const [clearMeta, setClearMeta] = useState(false);
  const [lossy, setLossy] = useState(false);
  const [watermarkText, setWatermarkText] = useState('CONFIDENCIAL');
  const [pageNumberFormat, setPageNumberFormat] = useState('{page}');
  const [jobStatus, setJobStatus] = useState('idle');
  const [progress, setProgress] = useState(0);
  const [stage, setStage] = useState('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = async () => {
    setError(null);
    setResult(null);
    setJobStatus('starting');
    setProgress(0);
    try {
      let params: Record<string, unknown> = { output_dir: outDir || undefined };
      if (mode === 'pdf-to-images') {
        if (!docId) throw new Error('Seleccioná un documento.');
        params = { ...params, document_id: docId, format, dpi: Number(dpi) };
      } else if (mode === 'images-to-pdf') {
        if (!imagePaths.length) throw new Error('Seleccioná imágenes.');
        params = { ...params, images: imagePaths, rotation: Number(rotation), output_path: outDir ? `${outDir}/imagenes.pdf` : undefined };
      } else if (mode === 'extract-text') {
        if (!docId) throw new Error('Seleccioná un documento.');
        params = { ...params, document_id: docId };
      } else if (mode === 'edit-metadata') {
        if (!docId) throw new Error('Seleccioná un documento.');
        params = { ...params, document_id: docId, title: title || undefined, author: author || undefined, subject: subject || undefined, keywords: keywords || undefined, clear: clearMeta };
      } else if (mode === 'compress') {
        if (!docId) throw new Error('Seleccioná un documento.');
        params = { ...params, document_id: docId, lossy };
      } else if (mode === 'watermark') {
        if (!docId) throw new Error('Seleccioná un documento.');
        params = { ...params, document_id: docId, text: watermarkText };
      } else if (mode === 'page-numbers') {
        if (!docId) throw new Error('Seleccioná un documento.');
        params = { ...params, document_id: docId, format: pageNumberFormat };
      }

      const r = await api.createJob(mode, params);
      setJobStatus('running');
      const es = new EventSource(`/api/jobs/${r.job_id}/events`);
      es.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          if (data.type === 'progress') { setProgress(data.progress ?? 0); setStage(data.stage ?? ''); }
          else if (data.type === 'done') {
            setJobStatus(data.status);
            es.close();
            api.jobReport(r.job_id).then((rep) => {
              setResult((rep.result ?? rep) as Record<string, unknown> | null);
              announce(rep.status === 'completed' ? 'Operación completada.' : 'Operación terminada con problemas.');
            }).catch(() => {});
          } else if (data.type === 'error') setJobStatus('failed');
        } catch {}
      };
      es.onerror = () => es.close();
    } catch (e) {
      setJobStatus('failed');
      setError((e as Error).message);
    }
  };

  const pickImages = async () => {
    try {
      const r = await api.pickFiles();
      if (r.paths?.length) setImagePaths(r.paths);
    } catch (e) {
      setError('No se pudieron seleccionar imágenes: ' + (e as Error).message);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="min-w-[200px] space-y-1">
          <label className="text-xs font-medium text-muted-foreground">Operación</label>
          <Select value={mode} onValueChange={(v) => setMode(v as Mode)}>
            <SelectTrigger size="sm" className="w-[200px] text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="pdf-to-images">PDF a imágenes</SelectItem>
              <SelectItem value="images-to-pdf">Imágenes a PDF</SelectItem>
              <SelectItem value="extract-text">Extraer texto</SelectItem>
              <SelectItem value="edit-metadata">Editar metadatos</SelectItem>
              <SelectItem value="compress">Comprimir</SelectItem>
              <SelectItem value="watermark">Marca de agua</SelectItem>
              <SelectItem value="page-numbers">Numerar páginas</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {mode !== 'images-to-pdf' && (
          <div className="min-w-[220px] flex-1 space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Documento</label>
            <Select value={docId} onValueChange={setDocId}>
              <SelectTrigger size="sm" className="w-full text-xs"><SelectValue placeholder="Elegí un documento" /></SelectTrigger>
              <SelectContent>
                {docs.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        )}

        {mode === 'pdf-to-images' && (
          <>
            <div className="min-w-[120px] space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Formato</label>
              <Select value={format} onValueChange={setFormat}>
                <SelectTrigger size="sm" className="w-[120px] text-xs"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="png">PNG</SelectItem>
                  <SelectItem value="jpeg">JPEG</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="min-w-[100px] space-y-1">
              <label className="text-xs font-medium text-muted-foreground">DPI</label>
              <Input value={dpi} onChange={(e) => setDpi(e.target.value)} className="h-9 text-sm" />
            </div>
          </>
        )}

        {mode === 'images-to-pdf' && (
          <>
            <div className="min-w-[200px] space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Imágenes</label>
              <Button variant="outline" size="sm" onClick={pickImages}>Elegir imágenes…</Button>
              <span className="ml-2 text-xs text-muted-foreground">{imagePaths.length} seleccionadas</span>
            </div>
            <div className="min-w-[100px] space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Rotación</label>
              <Input value={rotation} onChange={(e) => setRotation(e.target.value)} className="h-9 text-sm" />
            </div>
          </>
        )}

        {mode === 'edit-metadata' && (
          <>
            <div className="min-w-[160px] flex-1 space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Título</label>
              <Input value={title} onChange={(e) => setTitle(e.target.value)} className="h-9 text-sm" />
            </div>
            <div className="min-w-[160px] flex-1 space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Autor</label>
              <Input value={author} onChange={(e) => setAuthor(e.target.value)} className="h-9 text-sm" />
            </div>
            <div className="min-w-[160px] flex-1 space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Asunto</label>
              <Input value={subject} onChange={(e) => setSubject(e.target.value)} className="h-9 text-sm" />
            </div>
            <div className="min-w-[160px] flex-1 space-y-1">
              <label className="text-xs font-medium text-muted-foreground">Palabras clave</label>
              <Input value={keywords} onChange={(e) => setKeywords(e.target.value)} className="h-9 text-sm" />
            </div>
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <input type="checkbox" checked={clearMeta} onChange={(e) => setClearMeta(e.target.checked)} className="h-3.5 w-3.5 accent-primary" />
              Limpiar metadatos
            </label>
          </>
        )}

        {mode === 'compress' && (
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <input type="checkbox" checked={lossy} onChange={(e) => setLossy(e.target.checked)} className="h-3.5 w-3.5 accent-primary" />
            Compresión con pérdida (rasterizar)
          </label>
        )}
        {mode === 'watermark' && (
          <div className="min-w-[220px] flex-1 space-y-1">
            <Input value={watermarkText} onChange={(e) => setWatermarkText(e.target.value)} className="h-9 text-sm" />
          </div>
        )}

        {mode === 'page-numbers' && (
          <div className="min-w-[220px] flex-1 space-y-1">
            <label className="text-xs font-medium text-muted-foreground">Formato ({"{page}"}, {"{total}"})</label>
            <Input value={pageNumberFormat} onChange={(e) => setPageNumberFormat(e.target.value)} className="h-9 text-sm" />
          </div>
        )}

        <div className="min-w-[220px] flex-1 space-y-1">
          <label className="text-xs font-medium text-muted-foreground">Carpeta de salida</label>
          <Input value={outDir} onChange={(e) => setOutDir(e.target.value)} placeholder="Vacío = Descargas" className="h-9 text-sm" />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button size="sm" onClick={run} disabled={jobStatus === 'running'}>
          {jobStatus === 'running' ? 'Procesando…' : 'Ejecutar'}
        </Button>
        {jobStatus === 'running' && <span className="text-xs text-muted-foreground">{stage} {Math.round(progress)}%</span>}
      </div>

      {error && <div className="text-xs text-destructive">{error}</div>}

      {jobStatus !== 'idle' && jobStatus !== 'completed' && jobStatus !== 'completed_with_errors' && jobStatus !== 'failed' && jobStatus !== 'cancelled' && (
        <Progress value={progress} className="h-2" aria-label="Progreso" />
      )}

      {result && (
        <Card>
          <CardContent className="p-3 text-xs space-y-1">
            <div className="font-medium">Estado: {String(result.status ?? '')}</div>
            <div>Archivos: {String(result.total_files ?? 0)} · Páginas: {String(result.total_pages ?? 0)}</div>
            {Array.isArray(result.outputs) && (result.outputs as string[]).length > 0 && (
              <div className="break-all">{(result.outputs as string[]).slice(0, 5).join(' · ')}</div>
            )}
            {Array.isArray(result.errors) && (result.errors as unknown[]).length > 0 && (
              <div className="text-destructive">{(result.errors as unknown[]).length} problema(s)</div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
