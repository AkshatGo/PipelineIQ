import { useMutation, useQuery } from "@tanstack/react-query";
import type { RiskAssessmentRequest } from "@pipelineiq/shared";
import { FormEvent, useState } from "react";

import { assessRisk } from "./api/risk";
import { getCurrentUser, githubLoginUrl } from "./api/auth";

const initialRequest: RiskAssessmentRequest = {
  signals: {
    branch: "feature/pipeline-fix",
    files_changed: 3,
    lines_changed: 120,
    touches_sensitive_files: false,
    tests_failed: true,
    has_required_review: false,
    prior_similar_failures: 0,
  },
};

export function App() {
  const [request, setRequest] = useState(initialRequest);
  const risk = useMutation({ mutationFn: assessRisk });
  const session = useQuery({ queryKey: ["current-user"], queryFn: getCurrentUser, retry: false });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    risk.mutate(request);
  }

  function updateNumber(field: "files_changed" | "lines_changed", value: string) {
    setRequest((current) => ({
      ...current,
      signals: { ...current.signals, [field]: Math.max(0, Number(value)) },
    }));
  }

  return (
    <main>
      <header className="hero">
        <div className="topbar">
          <div className="brand"><span className="brand-mark">PI</span> PipelineIQ</div>
          {session.data ? (
            <span className="session">Signed in as <strong>{session.data.username}</strong></span>
          ) : (
            <a className="login-link" href={githubLoginUrl}>Sign in with GitHub</a>
          )}
        </div>
        <p className="eyebrow">CI/CD failure intelligence</p>
        <h1>Turn pipeline failures into safe, explainable action.</h1>
        <p className="lede">
          Diagnose failures, measure deployment risk, and automate the fixes that are safe to ship.
        </p>
      </header>

      <section className="workspace" aria-labelledby="risk-heading">
        <div className="section-copy">
          <p className="eyebrow">Foundation preview</p>
          <h2 id="risk-heading">Deterministic risk check</h2>
          <p>Test the first working slice of PipelineIQ. Every score is traceable to its signals.</p>
        </div>

        <form onSubmit={submit} className="risk-form">
          <label>
            Target branch
            <input
              value={request.signals.branch}
              onChange={(event) => setRequest((current) => ({
                ...current,
                signals: { ...current.signals, branch: event.target.value },
              }))}
              required
            />
          </label>
          <div className="form-row">
            <label>
              Files changed
              <input type="number" min="0" value={request.signals.files_changed} onChange={(event) => updateNumber("files_changed", event.target.value)} />
            </label>
            <label>
              Lines changed
              <input type="number" min="0" value={request.signals.lines_changed} onChange={(event) => updateNumber("lines_changed", event.target.value)} />
            </label>
          </div>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={request.signals.touches_sensitive_files}
              onChange={(event) => setRequest((current) => ({
                ...current,
                signals: { ...current.signals, touches_sensitive_files: event.target.checked },
              }))}
            />
            Touches deployment, dependency, or security files
          </label>
          <button type="submit" disabled={risk.isPending}>
            {risk.isPending ? "Assessing…" : "Assess risk"}
          </button>
        </form>

        <div className="result" aria-live="polite">
          {risk.data ? (
            <>
              <div className={`score score-${risk.data.band}`}>{risk.data.score}</div>
              <div>
                <p className="result-label">{risk.data.band} risk · {risk.data.action.replaceAll("_", " ")}</p>
                <ul>{risk.data.factors.map((factor) => <li key={factor.name}>+{factor.points} {factor.reason}</li>)}</ul>
              </div>
            </>
          ) : risk.isError ? (
            <p>Risk service is unavailable. Start the backend and try again.</p>
          ) : (
            <p>Submit a change profile to see its score, policy action, and contributing factors.</p>
          )}
        </div>
      </section>
    </main>
  );
}
