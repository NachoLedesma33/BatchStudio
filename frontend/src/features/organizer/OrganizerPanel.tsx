import { useCallback } from 'react';
import { DndContext, closestCenter, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, useSortable, arrayMove } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';

import { usePageOrganizer, type PageState } from './use-page-organizer';

interface SortablePageProps {
  page: PageState;
  documentId: string;
  selected: boolean;
  onSelect: (pageNo: number, e: React.MouseEvent) => void;
}

function SortablePage({ page, documentId, selected, onSelect }: SortablePageProps) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: page.page_no });
  const style = { transform: CSS.Transform.toString(transform), transition };
  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`relative cursor-grab rounded-lg border p-1 ${selected ? 'ring-2 ring-primary' : ''} ${page.excluded ? 'opacity-40' : ''}`}
      onClick={(e) => onSelect(page.page_no, e)}
      {...attributes}
      {...listeners}
    >
      <img
        src={`/api/documents/${documentId}/preview/${page.page_no}`}
        alt={`Página ${page.page_no}`}
        className="h-28 w-full rounded object-contain"
        style={{ transform: `rotate(${page.rotation}deg)` }}
      />
      <div className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground">
        <span>pág. {page.page_no}</span>
        <span>{page.rotation}°</span>
      </div>
    </div>
  );
}

interface OrganizerPanelProps {
  documentId: string | null;
  outputDir: string;
  announce: (message: string) => void;
}

export function OrganizerPanel({ documentId, outputDir, announce }: OrganizerPanelProps) {
  const org = usePageOrganizer({ documentId, announce });
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 4 } }));

  const handleDragEnd = useCallback((event: { active: { id: string | number }; over: { id: string | number } | null }) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const oldIndex = org.pages.findIndex((p) => p.page_no === active.id);
    const newIndex = org.pages.findIndex((p) => p.page_no === over.id);
    if (oldIndex < 0 || newIndex < 0) return;
    const next = arrayMove(org.pages, oldIndex, newIndex);
    org.commit(next);
  }, [org]);

  if (!documentId) {
    return <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">Seleccioná un documento para organizar.</div>;
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="outline" onClick={() => org.rotateSelected(90)} disabled={org.selected.size === 0}>Rotar +90</Button>
        <Button size="sm" variant="outline" onClick={() => org.rotateSelected(-90)} disabled={org.selected.size === 0}>Rotar -90</Button>
        <Button size="sm" variant="outline" onClick={org.toggleExcludedSelected} disabled={org.selected.size === 0}>Incluir/Excluir</Button>
        <Button size="sm" variant="outline" onClick={() => org.extractSelected(outputDir)} disabled={org.selected.size === 0}>Extraer selección</Button>
        <div className="ml-auto flex items-center gap-2">
          <Button size="sm" variant="ghost" onClick={org.undo} disabled={!org.history.length}>Deshacer</Button>
          <Button size="sm" variant="ghost" onClick={org.redo} disabled={!org.future.length}>Rehacer</Button>
          <Button size="sm" onClick={org.persist}>Guardar</Button>
        </div>
      </div>
      {org.loading && <div className="text-xs text-muted-foreground">Cargando páginas…</div>}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={org.pages.map((p) => p.page_no)} strategy={verticalListSortingStrategy}>
          <div className="grid grid-cols-3 gap-2 overflow-auto md:grid-cols-4 lg:grid-cols-6">
            {org.pages.map((page) => (
              <SortablePage
                key={page.page_no}
                page={page}
                documentId={documentId}
                selected={org.selected.has(page.page_no)}
                onSelect={(pageNo, e) => org.selectPage(pageNo, { ctrlKey: e.ctrlKey, shiftKey: e.shiftKey, metaKey: e.metaKey })}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
      {org.jobStatus === 'running' && <Progress value={org.progress} className="h-2" aria-label="Progreso de extracción" />}
    </div>
  );
}
