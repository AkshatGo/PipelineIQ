import { useEffect, useRef, useState } from 'react';
import { useInView, useReducedMotion } from 'framer-motion';
import { RotateCcwIcon } from 'lucide-react';
import { terminalTranscript, TranscriptLine } from '@/data/terminalTranscript';

export function Terminal() {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, amount: 0.4 });
  const reduced = useReducedMotion() ?? false;
  const [lineIdx, setLineIdx] = useState(0);
  const [charIdx, setCharIdx] = useState(0);

  const total = terminalTranscript.length;
  const done = lineIdx >= total;

  useEffect(() => {
    if (!inView) return;
    if (reduced) {
      setLineIdx(total);
      return;
    }
    if (lineIdx >= total) return;
    const line = terminalTranscript[lineIdx];
    if (line.kind === 'cmd' && charIdx < line.text.length) {
      const t = window.setTimeout(() => setCharIdx((c) => c + 1), 32);
      return () => window.clearTimeout(t);
    }
    const t = window.setTimeout(() => {
      setLineIdx((i) => i + 1);
      setCharIdx(0);
    }, line.delay ?? 220);
    return () => window.clearTimeout(t);
  }, [inView, reduced, lineIdx, charIdx, total]);

  const replay = () => {
    setLineIdx(0);
    setCharIdx(0);
  };

  return (
    <div
      ref={ref}
      className="overflow-hidden rounded-lg border border-line bg-ink-900 shadow-[0_40px_80px_-30px_rgba(0,0,0,0.7)]"
    >
      <div className="flex items-center justify-between border-b border-line bg-ink-800 px-4 py-2.5">
        <span className="font-mono text-[12px] text-muted">pipelineiq — acme/checkout-api</span>
        <button
          type="button"
          onClick={replay}
          disabled={!done}
          className="inline-flex items-center gap-1.5 rounded px-2 py-1 font-mono text-[12px] text-muted transition-colors duration-150 hover:text-paper disabled:opacity-40 disabled:hover:text-muted"
        >
          <RotateCcwIcon className="h-3.5 w-3.5" aria-hidden="true" />
          Replay
        </button>
      </div>
      <div
        className="min-h-[520px] space-y-1.5 overflow-x-auto px-5 py-5 font-mono text-[12.5px] leading-[1.6] md:text-[13px]"
        role="log"
        aria-label="Diagnose and fix transcript"
      >
        {terminalTranscript.slice(0, lineIdx).map((line, i) => (
          <LineView key={i} line={line} />
        ))}
        {!done && inView && terminalTranscript[lineIdx].kind === 'cmd' && (
          <div className="whitespace-pre text-paper">
            <span className="text-copper">$ </span>
            {terminalTranscript[lineIdx].text.slice(0, charIdx)}
            <Caret />
          </div>
        )}
        {!done && inView && terminalTranscript[lineIdx].kind !== 'cmd' && <Caret />}
        {done && (
          <div className="pt-1 text-paper">
            <span className="text-copper">$ </span>
            <Caret />
          </div>
        )}
      </div>
    </div>
  );
}

function Caret() {
  return (
    <span
      aria-hidden="true"
      className="ml-0.5 inline-block h-[1.05em] w-[0.55em] translate-y-[2px] bg-paper/80 animate-caret motion-reduce:animate-none"
    />
  );
}

function LineView({ line }: { line: TranscriptLine }) {
  switch (line.kind) {
    case 'cmd':
      return (
        <div className="whitespace-pre text-paper">
          <span className="text-copper">$ </span>
          {line.text}
        </div>
      );
    case 'info':
      return (
        <div className="whitespace-pre text-muted">
          <span className="text-line">› </span>
          {line.text}
        </div>
      );
    case 'error':
      return <div className="whitespace-pre text-fail-soft">{line.text}</div>;
    case 'trace':
      return <div className="whitespace-pre pl-4 text-muted">{line.text}</div>;
    case 'step':
      return (
        <div className="flex items-baseline gap-3 whitespace-pre text-paper">
          <span className="inline-block w-[74px] shrink-0 rounded-sm bg-teal px-1.5 text-center text-[11.5px] text-paper">
            {line.label}
          </span>
          {line.text}
        </div>
      );
    case 'ok':
      return <div className="whitespace-pre text-fix">{line.text}</div>;
    case 'pr':
      return (
        <div className="whitespace-pre rounded-sm border border-fix/40 bg-fix/10 px-2 py-1 font-medium text-fix">
          {line.text}
        </div>
      );
  }
}