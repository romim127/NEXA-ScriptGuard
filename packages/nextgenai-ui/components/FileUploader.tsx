import { useId, useRef, type ReactNode } from 'react';

export function FileUploader({ label, accept, disabled, onSelect, children, buttonLabel }: {
  label: string;
  accept: string;
  disabled: boolean;
  onSelect: (file: File | null) => void;
  children: ReactNode;
  buttonLabel?: string;
}) {
  const id = useId();
  const input = useRef<HTMLInputElement>(null);
  return <>
    <label id={id + '-label'} htmlFor={id}>{label}</label>
    <div className="controls">
      <input ref={input} id={id} type="file" accept={accept} disabled={disabled} hidden={Boolean(buttonLabel)}
        onChange={event => onSelect(event.currentTarget.files?.item(0) ?? null)} />
      {buttonLabel && <button type="button" disabled={disabled} aria-describedby={id + '-label'}
        onClick={() => input.current?.click()}>{buttonLabel}</button>}
      {children}
    </div>
  </>;
}
