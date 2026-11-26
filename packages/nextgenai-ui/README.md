# NextGenAI UI

Biblioteca interna de presentación React 19 y TypeScript. Importá los
componentes desde `@nextgenai/ui` y el tema desde `@nextgenai/ui/theme.css`.
Los tokens CSS se exponen en `@nextgenai/ui/tokens.css`.

```tsx
import { EvidenceViewer, FindingCard } from '@nextgenai/ui';
import '@nextgenai/ui/theme.css';

<FindingCard severity="LOW" rule="EXAMPLE-01" title="Revisión de ejemplo">
  <EvidenceViewer label="Evidencia" value="Texto compartible" expandable />
</FindingCard>
```

El consumidor aporta etiquetas y datos de dominio. `InfinityShield` requiere
una URL al recurso aprobado y un texto alternativo. `FileUploader` entrega
un archivo al consumidor. `ExportPanel` entrega el formato seleccionado.
Ninguno de los dos realiza solicitudes de red. El tema define tokens de
color y los controles conservan semántica nativa y foco visible.

El [consumidor independiente](../../frontend/demo/index.html) usa fixtures
sintéticos y la API pública. El workspace permanece privado.
