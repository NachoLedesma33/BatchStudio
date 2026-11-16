import type { PdfDocument } from '@/lib/api';

export interface DuplicateInfo {
  groupSize: Map<string, number>;
  flagged: Set<string>;
  extras: Set<string>;
  groupCount: number;
}

/**
 * Detección de repetidos: solo comparamos sha256 (mismo contenido byte a byte),
 * así nunca marcamos un archivo distinto por error. Sin hash, no se marca nada.
 */
export function findDuplicates(docs: PdfDocument[]): DuplicateInfo {
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
}
