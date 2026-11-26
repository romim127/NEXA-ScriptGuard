export function Sidebar({ label, links }: {
  label: string;
  links: ReadonlyArray<{ id: string; label: string }>;
}) {
  return <nav aria-label={label} className="ngi-navigation">
    {links.map(link => <a key={link.id} href={`#${link.id}`}>{link.label}</a>)}
  </nav>;
}
