import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';

import { request } from '@/lib/api/client';

interface RenameDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onDone: () => void;
}

export function RenameDialog({ open, onOpenChange, onDone }: RenameDialogProps) {
  const [find, setFind] = useState('');
  const [replace, setReplace] = useState('');
  const [regex, setRegex] = useState(false);
  const [preview, setPreview] = useState<Array<{ id: string; old_name: string; new_name: string; conflict: boolean }>>([]);
  const [conflicts, setConflicts] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const doPreview = async () => {
    setError(null);
    try {
      const r = await request<{ items: typeof preview; conflicts: string[] }>('/rename/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ find, replace, use_regex: regex }),
      });
      setPreview(r.items || []);
      setConflicts(r.conflicts || []);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const apply = async () => {
    setError(null);
    try {
      await request('/rename/apply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ find, replace, use_regex: regex }),
      });
      onDone();
      onOpenChange(false);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Renombrar lote</DialogTitle>
        </DialogHeader>
        <div className="space-y-2">
          <Input placeholder="Buscar" value={find} onChange={(e) => setFind(e.target.value)} />
          <Input placeholder="Reemplazar" value={replace} onChange={(e) => setReplace(e.target.value)} />
          <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <input type="checkbox" checked={regex} onChange={(e) => setRegex(e.target.checked)} className="h-3.5 w-3.5 accent-primary" />
            Usar expresión regular
          </label>
          <Button size="sm" variant="outline" onClick={doPreview}>Vista previa</Button>
          {error && <div className="text-xs text-destructive">{error}</div>}
          {conflicts.length > 0 && <div className="text-xs text-amber-700">Conflictos: {conflicts.join(', ')}</div>}
          <div className="max-h-48 overflow-auto rounded border p-2 text-xs">
            {preview.map((p) => (
              <div key={p.id} className={p.conflict ? 'text-destructive' : ''}>{p.old_name} → {p.new_name}</div>
            ))}
            {preview.length === 0 && <div className="text-muted-foreground">Sin vista previa.</div>}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>Cancelar</Button>
          <Button size="sm" onClick={apply} disabled={conflicts.length > 0}>Aplicar</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
