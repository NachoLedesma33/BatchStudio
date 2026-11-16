import { useEffect, useRef } from 'react';

import { isFormControl, isTextEntry } from '@/lib/shortcuts';

export interface ShortcutActions {
  openFiles: () => void;
  selectAll: () => void;
  clearSelection: () => void;
  removeSelected: () => void;
  merge: () => void;
  openShortcuts: () => void;
  canSelectAll: boolean;
  hasSelection: boolean;
  canMerge: boolean;
  dialogOpen: boolean;
}

/** Atajos globales: se leen desde un ref para suscribir el listener una sola vez. */
export function useGlobalShortcuts(actions: ShortcutActions) {
  const ref = useRef(actions);
  useEffect(() => { ref.current = actions; });

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      const a = ref.current;
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
}
