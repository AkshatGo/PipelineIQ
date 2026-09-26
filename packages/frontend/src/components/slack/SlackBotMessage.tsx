import { Logo } from '../Logo';

type SlackBotMessageProps = {
  time: string;
  children: React.ReactNode;
};

export function SlackBotMessage({ time, children }: SlackBotMessageProps) {
  return (
    <div className="flex gap-3">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md border border-line bg-ink-800">
        <Logo className="h-6 w-6" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="flex items-baseline gap-2">
          <span className="font-semibold text-paper">PipelineIQ</span>
          <span className="rounded-sm bg-ink-700 px-1 text-[10px] font-medium text-muted">App</span>
          <span className="text-[12px] text-muted">{time}</span>
        </p>
        <div className="mt-0.5 text-[15px] leading-relaxed text-paper">{children}</div>
      </div>
    </div>
  );
}