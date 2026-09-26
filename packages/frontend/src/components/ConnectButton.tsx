import { GitHubMark } from './GitHubMark';

type ConnectButtonProps = {
  href?: string;
  label?: string;
};

export function ConnectButton({ href = '#connect', label = 'Connect GitHub — it\'s free' }: ConnectButtonProps) {
  return (
    <a
      href={href}
      className="inline-flex items-center gap-2.5 whitespace-nowrap rounded-md bg-signal px-5 py-3 text-[16px] font-semibold text-ink transition-[filter,transform] duration-150 ease-out hover:brightness-110 active:scale-[0.98]"
    >
      <GitHubMark className="h-[18px] w-[18px]" />
      {label}
    </a>
  );
}