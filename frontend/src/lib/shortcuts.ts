/**
 * Atajos de teclado de la aplicación.
 *
 * Los atajos globales se ignoran cuando el foco está dentro de un control de
 * formulario (campo de texto, selector o casillero), para no pisar la escritura
 * ni el comportamiento nativo de esos controles.
 */

export interface ShortcutDef {
  /** Combinación tal como se muestra en la ayuda. */
  keys: string;
  /** Qué hace, en una frase. */
  description: string;
  /** Agrupación usada en el diálogo de ayuda. */
  group: string;
}

export const SHORTCUT_GROUPS = ['Archivos', 'Selección', 'Unión', 'Ayuda'] as const;

export const SHORTCUTS: ShortcutDef[] = [
  { group: 'Archivos', keys: 'Ctrl + O', description: 'Agregar archivos PDF al lote' },
  { group: 'Selección', keys: 'Ctrl + A', description: 'Seleccionar todos los documentos visibles' },
  { group: 'Selección', keys: 'Flechas ↑ ↓', description: 'Mover el foco entre documentos' },
  { group: 'Selección', keys: 'Inicio / Fin', description: 'Ir al primer o al último documento' },
  { group: 'Selección', keys: 'Espacio', description: 'Sumar o quitar del conjunto el documento enfocado' },
  { group: 'Selección', keys: 'Esc', description: 'Vaciar la selección' },
  { group: 'Selección', keys: 'Supr', description: 'Quitar de la lista los documentos seleccionados' },
  { group: 'Unión', keys: 'Ctrl + Enter', description: 'Unir los documentos incluidos' },
  { group: 'Ayuda', keys: '?', description: 'Mostrar esta lista de atajos' },
];

/** Elementos donde las teclas deben comportarse de forma nativa (escribir, marcar, elegir). */
export function isFormControl(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el || typeof el.tagName !== 'string') return false;
  const tag = el.tagName.toLowerCase();
  if (tag === 'textarea' || tag === 'select') return true;
  if (el.isContentEditable) return true;
  if (tag !== 'input') return false;
  const type = (el as HTMLInputElement).type.toLowerCase();
  // Los casilleros y botones tienen comportamiento propio con Espacio y flechas.
  return !['button', 'submit', 'reset'].includes(type);
}

/** Campos donde se escribe texto: ahí Ctrl+A debe seguir seleccionando el texto. */
export function isTextEntry(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el || typeof el.tagName !== 'string') return false;
  if (el.isContentEditable) return true;
  const tag = el.tagName.toLowerCase();
  if (tag === 'textarea') return true;
  if (tag !== 'input') return false;
  const type = (el as HTMLInputElement).type.toLowerCase();
  return ['text', 'search', 'url', 'tel', 'email', 'password', 'number', ''].includes(type);
}
