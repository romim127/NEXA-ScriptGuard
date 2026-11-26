import type { ReactNode } from 'react';

export function StatusIndicator({ tone, children }: {
  tone: 'idle' | 'loading' | 'success' | 'warning' | 'error';
  children: ReactNode;
}) {
  return <div className={`summary ngi-status-${tone}`} role="status" aria-live="polite">{children}</div>;
}
