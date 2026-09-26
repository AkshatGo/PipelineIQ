import { Logo } from './Logo';

const links = [
  { label: 'Docs', href: 'https://github.com/AkshatGo/PipelineIQ#readme' },
  { label: 'GitHub', href: 'https://github.com/AkshatGo/PipelineIQ' },
  { label: 'Security', href: 'https://github.com/AkshatGo/PipelineIQ/blob/main/SECURITY_CONSIDERATIONS.md' },
  { label: 'API', href: 'https://github.com/AkshatGo/PipelineIQ/blob/main/API_SPEC.md' },
];

export function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-10 md:flex-row md:items-center md:justify-between md:px-8">
        <div className="flex items-center gap-2.5">
          <Logo className="h-6 w-6" />
          <span className="font-semibold">PipelineIQ</span>
          <span className="ml-3 font-mono text-[12px] text-muted">© 2026</span>
        </div>
        <ul className="flex flex-wrap gap-x-7 gap-y-2">
          {links.map((l) => (
            <li key={l.label}>
              <a href={l.href} className="text-[14px] text-muted transition-colors duration-150 hover:text-paper">
                {l.label}
              </a>
            </li>
          ))}
        </ul>
      </div>
    </footer>
  );
}