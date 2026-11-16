import { Check, Copy, GripVertical, Trash2, X } from 'lucide-react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import { Badge } from '@/components/ui/badge';
import { IconButton } from '@/components/icon-button';
import type { PdfDocument } from '@/lib/api';
import { formatBytes, STATUS_LABEL, statusVariant } from './document-meta';

export function DocumentRow({ doc, selected, onSelect, onToggleSelect, onRemove, onToggle, duplicateGroup, rowIndex, tabIndex, onKeyDown, onFocus }: {
  doc: PdfDocument; selected: boolean; onSelect: (e: React.MouseEvent) => void;
  onToggleSelect: () => void; onRemove: () => void; onToggle: () => void;
  duplicateGroup: number | null; rowIndex: number;
  tabIndex: number; onKeyDown: (e: React.KeyboardEvent) => void; onFocus: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: doc.id });
  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 20 : undefined,
  };
  const ariaLabel = [
    doc.name,
    doc.page_count ? `${doc.page_count} página${doc.page_count === 1 ? '' : 's'}` : 'páginas sin analizar',
    STATUS_LABEL[doc.status],
    doc.included ? 'incluido en el lote' : 'excluido del lote',
    duplicateGroup ? `archivo repetido, ${duplicateGroup} copias iguales` : null,
  ].filter(Boolean).join(', ');
  return (
    <div
      ref={setNodeRef}
      style={style}
      data-row-index={rowIndex}
      role="listitem"
      aria-label={ariaLabel}
      onClick={onSelect}
      onKeyDown={onKeyDown}
      onFocus={onFocus}
      tabIndex={tabIndex}
      className={`flex h-14 items-center gap-2.5 rounded-lg border px-2.5 transition-colors cursor-pointer outline-none
        focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-card
        ${selected ? 'border-primary/40 bg-accent/5 ring-1 ring-primary/25' : 'border-transparent hover:bg-muted/60'}
        ${doc.included ? '' : 'opacity-55'}
        ${isDragging ? 'shadow-lg bg-card border-primary/40' : ''}`}
    >
      <input
        type="checkbox"
        checked={selected}
        onChange={() => onToggleSelect()}
        onClick={(e) => e.stopPropagation()}
        tabIndex={-1}
        aria-label={`Seleccionar ${doc.name}`}
        className="h-3.5 w-3.5 flex-shrink-0 cursor-pointer accent-primary"
      />
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
      <div className="relative h-11 w-8 flex-shrink-0">
        <div className={`h-11 w-8 overflow-hidden rounded border bg-muted ${duplicateGroup ? 'border-amber-400 ring-1 ring-amber-400/60' : 'border-border/60'}`}>
          <img
            src={`/api/documents/${doc.id}/preview/1`}
            alt=""
            loading="lazy"
            className="h-full w-full object-cover"
            onError={(e) => { (e.target as HTMLImageElement).style.visibility = 'hidden'; }}
          />
        </div>
        {duplicateGroup !== null && (
          <span
            className="absolute -bottom-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-amber-500 text-white shadow ring-2 ring-card"
            title={`Archivo repetido: hay ${duplicateGroup} copias iguales en el lote`}
          >
            <Copy className="h-2.5 w-2.5" />
          </span>
        )}
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
          tabIndex={-1}
          onClick={(e) => { e.stopPropagation(); onToggle(); }}
        >
          {doc.included ? <Check className="h-4 w-4 text-emerald-600 dark:text-emerald-400" /> : <X className="h-4 w-4" />}
        </IconButton>
        <IconButton
          label="Quitar de la lista"
          tabIndex={-1}
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
        >
          <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
        </IconButton>
      </div>
    </div>
  );
}
