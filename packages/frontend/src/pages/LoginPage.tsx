import { ConnectButton } from '../components/ConnectButton';

export function LoginPage() {
  return (
    <div className="min-h-screen w-full bg-ink flex items-center justify-center px-5">
      <div className="w-full max-w-md">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-semibold leading-[1.05] tracking-[-0.025em] md:text-5xl">
            Welcome to PipelineIQ
          </h1>
          <p className="mt-6 max-w-[56ch] text-lg leading-relaxed text-muted mx-auto">
            AI-powered CI/CD failure intelligence and auto-remediation.
            Sign in with GitHub to get started.
          </p>
        </div>

        <div className="rounded-lg border border-line bg-ink-900/50 p-8">
          <ConnectButton
            href="/api/auth/github"
            label="Sign in with GitHub"
          />
        </div>

        <p className="mt-8 text-center text-sm text-muted">
          By signing in, you agree to our{' '}
          <a href="#" className="underline hover:text-paper">
            Terms of Service
          </a>{' '}
          and{' '}
          <a href="#" className="underline hover:text-paper">
            Privacy Policy
          </a>
        </p>
      </div>
    </div>
  );
}