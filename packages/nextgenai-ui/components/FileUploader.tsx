import { useId, type ReactNode } from 'react';

export function FileUploader({ label, accept, disabled, onSelect, children }: {
  label: string;
  accept: string;
  disabled: boolean;
  onSelect: (file: File | null) => void;
  children: ReactNode;
}) {
  const id = useId();
  return <>
    <label htmlFor={id}>{label}</label>
    <div className="controls">
      <input id={id} type="file" accept={accept} disabled={disabled}
        onChange={event => onSelect(event.currentTarget.files?.item(0) ?? null)} />
      {children}
    </div>
  </>;
}
