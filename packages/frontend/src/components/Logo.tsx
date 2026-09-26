
type LogoProps = { className?: string };

export function Logo({ className = 'h-7 w-7' }: LogoProps) {
  return (
    <svg viewBox="0 0 28 28" className={className} aria-hidden="true">
      <rect x="1" y="1" width="26" height="26" rx="5" className="fill-ink-800 stroke-line" strokeWidth="1.5" />
      <path
        d="M4 18h6l3-7h6l2 3h3"
        fill="none"
        className="stroke-copper"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="13" cy="11" r="2.4" className="fill-fail" />
      <circle cx="21" cy="14" r="2.4" className="fill-fix" />
    </svg>
  );
}