import {
  Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle,
} from '@/components/ui/dialog';
import { SHORTCUTS, SHORTCUT_GROUPS } from '@/lib/shortcuts';

export function ShortcutsDialog({ open, onOpenChange }: {
  open: boolean; onOpenChange: (open: boolean) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Atajos de teclado</DialogTitle>
          <DialogDescription>
            Trabajá el lote sin soltar el teclado. En macOS usá ⌘ en lugar de Ctrl.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {SHORTCUT_GROUPS.map((group) => {
            const items = SHORTCUTS.filter((s) => s.group === group);
            if (!items.length) return null;
            return (
              <div key={group} className="space-y-1.5">
                <h3 className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">{group}</h3>
                <dl className="space-y-1.5">
                  {items.map((s) => (
                    <div key={s.keys} className="flex items-center justify-between gap-4">
                      <dt className="text-sm text-muted-foreground">{s.description}</dt>
                      <dd className="flex-shrink-0">
                        <kbd className="rounded-md border bg-muted px-1.5 py-0.5 font-sans text-[11px] font-medium text-foreground">
                          {s.keys}
                        </kbd>
                      </dd>
                    </div>
                  ))}
                </dl>
              </div>
            );
          })}
        </div>
      </DialogContent>
    </Dialog>
  );
}
