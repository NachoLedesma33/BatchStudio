import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

import { api } from '@/lib/api';

export function SearchPanel({ announce }: { announce: (m: string) => void }) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Array<{ doc_id: string; page_no: number; name: string; snippet: string }>>([]);
  const [loading, setLoading] = useState(false);
  const [indexing, setIndexing] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const r = await api.search(query, 50);
      setResults(r.results || []);
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
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar en el lote indexado..."
          className="h-9 flex-1 text-sm"
          onKeyDown={(e) => { if (e.key === 'Enter') void search(); }}
        />
        <Button size="sm" onClick={search} disabled={loading}>Buscar</Button>
        <Button size="sm" variant="outline" onClick={rebuild} disabled={indexing}>
          {indexing ? 'Indexando…' : 'Reindexar'}
        </Button>
      </div>
      {loading && <div className="text-xs text-muted-foreground">Buscando…</div>}
      <div className="flex-1 overflow-auto rounded border">
        {results.length === 0 ? (
          <div className="py-8 text-center text-xs text-muted-foreground">Sin resultados.</div>
        ) : (
          <ul className="divide-y text-xs">
            {results.map((r, i) => (
              <li key={i} className="p-2">
                <div className="font-medium">{r.name} — pág. {r.page_no}</div>
                <div className="text-muted-foreground">{r.snippet}</div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
