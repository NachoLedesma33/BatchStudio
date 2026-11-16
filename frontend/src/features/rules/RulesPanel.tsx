import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

import { api } from '@/lib/api';

interface Rule { id: string; name: string; kind: string; params: Record<string, unknown>; }
interface Profile { id: string; name: string; params: Record<string, unknown>; }
interface Watched { id: string; path: string; active: boolean; }

export function RulesPanel({ announce }: { announce: (m: string) => void }) {
  const [rules, setRules] = useState<Rule[]>([]);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [watched, setWatched] = useState<Watched[]>([]);
  const [name, setName] = useState('');
  const [kind, setKind] = useState('merge');
  const [paramsText, setParamsText] = useState('{}');
  const [watchPath, setWatchPath] = useState('');

  const load = useCallback(async () => {
    const [r, p, w] = await Promise.all([
      fetch('/api/rules').then((x) => x.json()),
      fetch('/api/profiles').then((x) => x.json()),
      fetch('/api/watched').then((x) => x.json()),
    ]);
    setRules(r.rules || []);
    setProfiles(p.profiles || []);
    setWatched(w.watched || []);
  }, []);

  useEffect(() => { void load(); }, [load]);

  const createRule = async () => {
    let params: Record<string, unknown> = {};
    try { params = JSON.parse(paramsText || '{}'); } catch { alert('JSON inválido'); return; }
    await fetch('/api/rules', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, kind, params }),
    });
    setName('');
    await load();
    announce('Regla creada.');
  };

  const deleteRule = async (id: string) => {
    await fetch(`/api/rules/${id}`, { method: 'DELETE' });
    await load();
  };

  const createProfile = async () => {
    let params: Record<string, unknown> = {};
    try { params = JSON.parse(paramsText || '{}'); } catch { alert('JSON inválido'); return; }
    await fetch('/api/profiles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: name || 'Perfil', params }),
    });
    await load();
    announce('Perfil creado.');
  };

  const addWatched = async () => {
    if (!watchPath.trim()) return;
    await fetch('/api/watched', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: watchPath }),
    });
    setWatchPath('');
    await load();
  };

  const toggleWatched = async (w: Watched) => {
    await fetch(`/api/watched/${w.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ active: !w.active }),
    });
    await load();
  };

  const deleteWatched = async (id: string) => {
    await fetch(`/api/watched/${id}`, { method: 'DELETE' });
    await load();
  };

  const runRule = async (rule: Rule) => {
    try {
      const r = await api.createJob(rule.kind, rule.params || {});
      announce(`Regla ejecutada: trabajo ${r.job_id.slice(0, 8)}.`);
    } catch (e) {
      alert('No se pudo ejecutar la regla: ' + (e as Error).message);
    }
  };

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
      <h2 className="text-sm font-semibold">Automatización y perfiles</h2>
      <div className="flex flex-wrap items-end gap-2">
        <Input placeholder="Nombre" value={name} onChange={(e) => setName(e.target.value)} className="h-9 w-48 text-sm" />
        <Select value={kind} onValueChange={setKind}>
          <SelectTrigger size="sm" className="w-40 text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="merge">Unir</SelectItem>
            <SelectItem value="split">Dividir</SelectItem>
            <SelectItem value="extract">Extraer</SelectItem>
            <SelectItem value="compress">Comprimir</SelectItem>
          </SelectContent>
        </Select>
        <Input placeholder='Params JSON' value={paramsText} onChange={(e) => setParamsText(e.target.value)} className="h-9 flex-1 text-sm font-mono" />
        <Button size="sm" onClick={createRule}>Crear regla</Button>
        <Button size="sm" variant="outline" onClick={createProfile}>Crear perfil</Button>
      </div>

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="rounded border p-2">
          <div className="mb-2 text-xs font-semibold">Reglas</div>
          <ul className="space-y-1 text-xs">
            {rules.map((r) => (
              <li key={r.id} className="flex items-center gap-2">
                <span className="flex-1">{r.name} ({r.kind})</span>
                <Button size="xs" onClick={() => runRule(r)}>Ejecutar</Button>
                <Button size="xs" variant="ghost" onClick={() => deleteRule(r.id)}>Eliminar</Button>
              </li>
            ))}
            {rules.length === 0 && <li className="text-muted-foreground">Sin reglas.</li>}
          </ul>
        </div>
        <div className="rounded border p-2">
          <div className="mb-2 text-xs font-semibold">Perfiles</div>
          <ul className="space-y-1 text-xs">
            {profiles.map((p) => (
              <li key={p.id} className="flex items-center gap-2">
                <span className="flex-1">{p.name}</span>
                <Button size="xs" variant="ghost" onClick={() => { /* apply profile to params */ setParamsText(JSON.stringify(p.params)); }}>Usar</Button>
              </li>
            ))}
            {profiles.length === 0 && <li className="text-muted-foreground">Sin perfiles.</li>}
          </ul>
        </div>
      </div>

      <div className="rounded border p-2">
        <div className="mb-2 text-xs font-semibold">Carpetas vigiladas</div>
        <div className="mb-2 flex gap-2">
          <Input placeholder="Ruta de carpeta" value={watchPath} onChange={(e) => setWatchPath(e.target.value)} className="h-9 flex-1 text-sm" />
          <Button size="sm" onClick={addWatched}>Vigilar</Button>
        </div>
        <ul className="space-y-1 text-xs">
          {watched.map((w) => (
            <li key={w.id} className="flex items-center gap-2">
              <span className="flex-1">{w.path} {w.active ? '(activo)' : '(pausado)'}</span>
              <Button size="xs" variant="outline" onClick={() => toggleWatched(w)}>{w.active ? 'Pausar' : 'Activar'}</Button>
              <Button size="xs" variant="ghost" onClick={() => deleteWatched(w.id)}>Eliminar</Button>
            </li>
          ))}
          {watched.length === 0 && <li className="text-muted-foreground">Sin carpetas vigiladas.</li>}
        </ul>
      </div>
    </div>
  );
}
