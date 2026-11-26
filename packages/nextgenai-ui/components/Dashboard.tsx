import type { ReactNode } from 'react';

export function Dashboard({ header, children, className }: {
  header: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return <main className={className}><header>{header}</header>{children}</main>;
}
