import { useRef } from 'react';
import { motion, useReducedMotion, useScroll, useTransform } from 'framer-motion';
import { DashboardMockup } from './DashboardMockup';

export function DashboardShowcase() {
  const ref = useRef<HTMLDivElement>(null);
  const reduced = useReducedMotion() ?? false;
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'center center'] });
  const rotateX = useTransform(scrollYProgress, [0, 1], [26, 0]);
  const scale = useTransform(scrollYProgress, [0, 1], [0.9, 1]);
  const y = useTransform(scrollYProgress, [0, 1], [60, 0]);

  return (
    <section id="dashboard" className="border-b border-line py-24 lg:py-32">
      <div className="mx-auto max-w-7xl px-5 md:px-8">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-end">
          <h2 className="max-w-[16ch] text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
            Every red build, and what happened to it
          </h2>
          <p className="max-w-[50ch] text-lg leading-relaxed text-muted">
            One list across every repo: the failure, the cause, the score, and whether it merged, waited,
            or got blocked. Click a run to see the patch.
          </p>
        </div>

        <div ref={ref} className="mt-14" style={{ perspective: 1600 }}>
          <motion.div
            style={reduced ? undefined : { rotateX, scale, y, transformOrigin: 'center top' }}
          >
            <DashboardMockup />
          </motion.div>
        </div>
      </div>
    </section>
  );
}