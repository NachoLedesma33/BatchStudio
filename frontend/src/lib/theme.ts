import { useCallback, useEffect, useState } from 'react';

export type ThemeMode = 'light' | 'dark';

export const THEME_STORAGE_KEY = 'pdf-batch-studio:theme';

function systemPrefersDark(): boolean {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches;
}

/** Preferencia guardada; si no hay ninguna, se sigue al sistema operativo. */
export function resolveInitialTheme(): ThemeMode {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === 'light' || stored === 'dark') return stored;
  } catch {
    // localStorage puede estar bloqueado; caemos al sistema.
  }
  return systemPrefersDark() ? 'dark' : 'light';
}

export function applyTheme(mode: ThemeMode): void {
  const root = document.documentElement;
  root.classList.toggle('dark', mode === 'dark');
  // Hace que scrollbars y controles nativos acompañen el tema.
  root.style.colorScheme = mode;
}

/** Tema claro/oscuro con preferencia persistida en el navegador. */
export function useTheme() {
  const [mode, setMode] = useState<ThemeMode>(() => resolveInitialTheme());

  useEffect(() => { applyTheme(mode); }, [mode]);

  const toggle = useCallback(() => {
    setMode((current) => {
      const next: ThemeMode = current === 'dark' ? 'light' : 'dark';
      try { localStorage.setItem(THEME_STORAGE_KEY, next); } catch { /* sin persistencia */ }
      return next;
    });
  }, []);

  return { mode, toggle };
}
