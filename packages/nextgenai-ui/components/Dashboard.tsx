import type { ReactNode } from 'react';

export function Dashboard({ header, children }: { header: ReactNode; children: ReactNode }) {
  return <main><header>{header}</header>{children}</main>;
}
