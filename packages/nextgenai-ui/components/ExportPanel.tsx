export function ExportPanel<Format extends string>({ label, formats, disabled, onExport }: {
  label: string;
  formats: ReadonlyArray<{ id: Format; label: string }>;
  disabled: boolean;
  onExport: (format: Format) => void;
}) {
  return <div className="controls" role="group" aria-label={label}>
    {formats.map(format => <button key={format.id} type="button" disabled={disabled}
      onClick={() => onExport(format.id)}>{format.label}</button>)}
  </div>;
}
