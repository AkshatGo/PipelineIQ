import { ScrollProgress } from './components/ScrollProgress';
import { Nav } from './components/Nav';
import { Hero } from './components/hero/Hero';
import { StampBand } from './components/StampBand';
import { TerminalDemo } from './components/terminal/TerminalDemo';
import { ProcessSteps } from './components/ProcessSteps';
import { DashboardShowcase } from './components/dashboard/DashboardShowcase';
import { RiskLab } from './components/risk/RiskLab';
import { SlackApproval } from './components/slack/SlackApproval';
import { ComparisonTable } from './components/ComparisonTable';
import { FinalCta } from './components/FinalCta';
import { Footer } from './components/Footer';

export function App() {
  return (
    <div className="min-h-screen w-full bg-ink font-sans text-paper">
      <ScrollProgress />
      <Nav />
      <main>
        <Hero />
        <StampBand />
        <TerminalDemo />
        <ProcessSteps />
        <DashboardShowcase />
        <RiskLab />
        <SlackApproval />
        <ComparisonTable />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}