import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import { api } from '@/lib/api';
import { request } from '@/lib/api/client';
import type { PdfDocument } from '@/lib/api';

interface SearchPanelProps {
  docs: PdfDocument[];
  announce: (m: string) => void;
  onOpen: (docId: string, page: number) => void;
}

export function SearchPanel({ docs, announce, onOpen }: SearchPanelProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Array<{ doc_id: string; page_no: number; name: string; snippet: string }>>([]);
  const [docResults, setDocResults] = useState<Array<{ page: number; snippet: string }>>([]);
  const [selectedDoc, setSelectedDoc] = useState<string>('');
  const [mode, setMode] = useState<'global' | 'document'>('global');
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [indexed, setIndexed] = useState<number | null>(null);

  const loadStatus = async () => {
    try {
      const r = await request<{ indexed: number }>('/search/status', { method: 'GET' });
      setIndexed(r.indexed);
    } catch {}
  };

  useEffect(() => { void loadStatus(); }, []);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      if (mode === 'global') {
        const r = await api.search(query, 50);
        setResults(r.results || []);
        setDocResults([]);
      } else {
        if (!selectedDoc) return;
        const r = await api.searchInDocument(selectedDoc, query);
        setDocResults(r.results || []);
        setResults([]);
      }
    } catch (e) {
      alert('Error al buscar: ' + (e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const rebuild = async () => {
    setIndexing(true);
    try {
      const r = await api.rebuildSearchIndex();
      setIndexed(r.total);
      announce(`Índice reconstruido: ${r.indexed} documentos.`);
    } catch (e) {
      alert('No se pudo indexar: ' + (e as Error).message);
    } finally {
      setIndexing(false);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
      <div className="flex items-center gap-2">
        <Select value={mode} onValueChange={(v) => setMode(v as 'global' | 'document')}>
          <SelectTrigger size="sm" className="w-[140px] text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="global">Global</SelectItem>
            <SelectItem value="document">En documento</SelectItem>
          </SelectContent>
        </Select>
        {mode === 'document' && (
          <Select value={selectedDoc} onValueChange={setSelectedDoc}>
            <SelectTrigger size="sm" className="w-[220px] text-xs"><SelectValue placeholder="Elegí un documento" /></SelectTrigger>
            <SelectContent>
              {docs.map((d) => <SelectItem key={d.id} value={d.id}>{d.name}</SelectItem>)}
            </SelectContent>
          </Select>
        )}
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar..."
          className="h-9 flex-1 text-sm"
          onKeyDown={(e) => { if (e.key === 'Enter') void search(); }}
        />
        <Button size="sm" onClick={search} disabled={loading}>Buscar</Button>
        <Button size="sm" variant="outline" onClick={rebuild} disabled={indexing}>
          {indexing ? 'Indexando…' : 'Reindexar'}
        </Button>
      </div>
      <div className="text-xs text-muted-foreground">
        {indexed !== null ? `${indexed} entradas indexadas.` : 'Sin información de índice.'}
      </div>
      {loading && <div className="text-xs text-muted-foreground">Buscando…</div>}
      <div className="flex-1 overflow-auto rounded border">
        {mode === 'global' ? (
          results.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">Sin resultados.</div>
          ) : (
            <ul className="divide-y text-xs">
              {results.map((r, i) => (
                <li key={i} className="p-2 cursor-pointer hover:bg-muted/40" onClick={() => onOpen(r.doc_id, r.page_no)}>
                  <div className="font-medium">{r.name} — pág. {r.page_no}</div>
                  <div className="text-muted-foreground">{r.snippet}</div>
                </li>
              ))}
            </ul>
          )
        ) : (
          docResults.length === 0 ? (
            <div className="py-8 text-center text-xs text-muted-foreground">Sin resultados.</div>
          ) : (
            <ul className="divide-y text-xs">
              {docResults.map((r, i) => (
                <li key={i} className="p-2 cursor-pointer hover:bg-muted/40" onClick={() => onOpen(selectedDoc, r.page)}>
                  <div className="font-medium">pág. {r.page}</div>
                  <div className="text-muted-foreground">{r.snippet}</div>
                </li>
              ))}
            </ul>
          )
        )}
      </div>
    </div>
  );
}
