import { useEffect, useRef } from 'react';

/** Checkbox nativo que además soporta el estado indeterminado (selección parcial). */
export function TriCheckbox({ checked, indeterminate, onChange, disabled, label }: {
  checked: boolean; indeterminate?: boolean; onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean; label: string;
}) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => { if (ref.current) ref.current.indeterminate = Boolean(indeterminate) && !checked; }, [indeterminate, checked]);
  return (
    <input
      ref={ref}
      type="checkbox"
      checked={checked}
      disabled={disabled}
      onChange={onChange}
      aria-label={label}
      className="h-3.5 w-3.5 flex-shrink-0 cursor-pointer accent-primary disabled:cursor-not-allowed"
    />
  );
}
