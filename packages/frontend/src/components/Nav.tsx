import { Logo } from './Logo';
import { GitHubMark } from './GitHubMark';

const links = [
  { href: '#how-it-works', label: 'How it works' },
  { href: '#live-fix', label: 'Live fix' },
  { href: '#dashboard', label: 'Dashboard' },
  { href: '#risk-lab', label: 'Risk lab' },
];

export function Nav() {
  return (
    <header className="sticky top-0 z-40 border-b border-line bg-ink/90 backdrop-blur-md">
      <nav
        aria-label="Main"
        className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-5 md:px-8"
      >
        <a href="#top" className="flex items-center gap-2.5 rounded-md">
          <Logo />
          <span className="text-[17px] font-semibold tracking-tight">PipelineIQ</span>
        </a>
        <ul className="hidden items-center gap-8 md:flex">
          {links.map((link) => (
            <li key={link.href}>
              <a
                href={link.href}
                className="whitespace-nowrap text-[15px] text-muted transition-colors duration-150 hover:text-paper"
              >
                {link.label}
              </a>
            </li>
          ))}
        </ul>
        <a
          href="#connect"
          className="inline-flex items-center gap-2 whitespace-nowrap rounded-md bg-copper px-4 py-2 text-sm font-semibold text-ink transition-[filter,transform] duration-150 ease-out hover:brightness-110 active:scale-[0.98]"
        >
          <GitHubMark />
          Connect GitHub
        </a>
      </nav>
    </header>
  );
}