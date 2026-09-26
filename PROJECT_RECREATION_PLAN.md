# PipelineIQ - Project Recreation Plan & Documentation

## Executive Summary

This document outlines the complete plan to recreate the **PipelineIQ** project - an AI-powered CI/CD failure intelligence and auto-remediation platform - with the exact same core functionality while adding meaningful improvements.

---

## 1. Project Overview

### 1.1 Original Project
- **Name**: PipelineIQ
- **Type**: AI-powered CI/CD failure intelligence and auto-remediation platform
- **Architecture**: Microservices-ready monolith (FastAPI backend + React frontend)
- **Core Value**: Reduces CI/CD failure resolution latency by converting raw workflow failure events into structured actions

### 1.2 Core Functionality (MUST PRESERVE)
1. **Authentication**: GitHub OAuth 2.0 for user login
2. **Repository Integration**: GitHub App for installation, webhooks, and repository operations
3. **Event Processing**: GitHub Actions workflow completion webhook handling
4. **Failure Detection**: Monitor stage with log analysis and health classification
5. **AI Diagnosis**: Root cause analysis using error snippets + Git diff comparison
6. **Risk Scoring**: Deterministic multi-signal risk assessment (0-100)
7. **Policy Engine**: Three-tier action selection (auto-fix / approval required / block)
8. **Auto-Fix**: AI-generated minimal patches, PR creation, reviewer assignment
9. **Notifications**: Slack webhook integration
10. **Feedback Loop**: Report decision + resolution quality feedback for memory
11. **Dashboard**: React-based UI for workspace management and monitoring

---

## 2. Current Architecture Analysis

### 2.1 Directory Structure
```
hacktofuture4-D02/
├── .env.example              # Environment template
├── .gitignore
├── Dockerfile                # Flask demo app (NOT for main backend)
├── README.md
├── architecture.png          # Architecture diagram
├── deployment.md             # Production deployment guide
├── workflow.png              # Workflow diagram
├── docs/                     # Setup documentation
│   ├── setup.md
│   ├── kafkasetup.md
│   ├── failure-simulation.md
│   └── setupslack.md
├── flask_app/                # Demo service for failure simulation
│   ├── app.py
│   └── requirements.txt
├── pipelineIQ/               # Main FastAPI backend
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Pydantic settings
│   ├── database.py           # MongoDB/Beanie connection
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── auth/                 # JWT + cookie auth
│   ├── models/               # Beanie document models
│   ├── routers/              # API route handlers
│   └── services/             # Business logic services
├── pipelineIQ-frontend/      # React + Vite frontend
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── src/
│   │   ├── api/client.js     # Axios instance
│   │   ├── components/       # Reusable UI components
│   │   ├── context/          # React context providers
│   │   └── pages/            # Page components
│   └── public/
└── scripts/                  # Operational scripts
    ├── reset_backend_state.py
    ├── reset_kafka_topics.ps1
    └── reset_system.ps1
```

### 2.2 Technology Stack

#### Backend
| Component | Technology | Version |
|-----------|------------|---------|
| Framework | FastAPI | 0.115+ |
| ASGI Server | Uvicorn | 0.34+ |
| Database | MongoDB + Beanie ODM | Motor 3.5+, Beanie 1.26+ |
| Message Queue | Apache Kafka | aiokafka 0.10+ |
| Auth | python-jose (JWT) + HttpOnly cookies | 3.4+ |
| HTTP Client | httpx | 0.28+ |
| LLM Gateway | OpenAI-compatible SDK | 1.51+ |
| Config | pydantic-settings + python-dotenv | 2.8+ / 1.1+ |

#### Frontend
| Component | Technology | Version |
|-----------|------------|---------|
| Framework | React | 19.2+ |
| Build Tool | Vite | 8.0+ |
| Styling | Tailwind CSS | 4.2+ |
| Routing | React Router DOM | 7.14+ |
| HTTP Client | Axios | 1.15+ |
| Linting | ESLint | 9.39+ |

#### Infrastructure
| Component | Technology |
|-----------|------------|
| Database | MongoDB Atlas (or local) |
| Message Queue | Apache Kafka (optional, KRaft mode) |
| Auth Provider | GitHub OAuth App + GitHub App |
| Notifications | Slack Incoming Webhooks |
| LLM Providers | GitHub Models, Groq, OpenAI-compatible |
| Deployment | Vercel (frontend) + Render (backend) |

---

## 3. Data Model Specification

### 3.1 Core Models (Beanie/MongoDB)

#### User
```python
github_id: int (unique)
username: str
display_name: str?
email: str?
avatar_url: str?
github_access_token: str (encrypted at rest recommended)
organizations: list[GitHubOrganization]
last_login: datetime
created_at: datetime
is_active: bool
```

#### Workspace
```python
name: str
description: str?
owner_id: PydanticObjectId (User)
github_installation_id: int?
github_repository_id: int?
github_repo_full_name: str?
github_default_branch: str?
github_repo_private: bool?
github_repo_html_url: str?
github_account_login: str?
github_account_type: str?
slack_devops_mention: str?
risk_profile: RiskProfile
connected_at: datetime?
last_webhook_event_at: datetime?
created_at: datetime
updated_at: datetime
```

#### RiskProfile (embedded)
```python
production_branch: str = "main"
require_approval_above: int = 60
auto_fix_below: int = 30
```

#### Repository
```python
github_repo_id: int
full_name: str
name: str
private: bool
html_url: str
default_branch: str
workspace_id: PydanticObjectId
connected_at: datetime
connected_by: PydanticObjectId
```

#### WebhookEvent
```python
delivery_id: str (unique)
event_type: str
action: str?
installation_id: int?
repository_full_name: str?
payload: dict
received_at: datetime
```

#### PipelineRun
```python
workspace_id: PydanticObjectId
installation_id: int?
repository_full_name: str
delivery_id: str
event_type: str
action: str?
run_id: int?
workflow_status: str?
workflow_name: str?
workflow_url: str?
branch: str?
commit_sha: str?
triggered_by: str?
conclusion: str?
health_status: str = "unknown"
kafka_status: str = "queued"
monitor_status: str = "pending"
diagnosis_status: str = "pending"
risk_status: str = "pending"
monitor_summary: str?
monitor_report_json: dict
monitor_logs_excerpt: list[str]
diagnosis_report: str?
diagnosis_report_json: dict
diagnosis_error: str?
risk_score: int?
risk_band: str?
risk_report_json: dict
risk_inputs_json: dict
risk_error: str?
risk_provider: str?
risk_model: str?
autofix_status: str = "pending"
autofix_mode: str?
autofix_report_url: str?
autofix_pr_url: str?
autofix_execution_id: str?
autofix_error: str?
autofix_feedback_url: str?
autofix_feedback_status: str?
error_summary: str?
diagnosis_provider: str?
diagnosis_model: str?
monitor_provider: str?
monitor_model: str?
raw_event: dict
enriched_event: dict
created_at: datetime
updated_at: datetime
```

#### AutoFixExecution
```python
workspace_id: PydanticObjectId
pipeline_run_id: PydanticObjectId
repository_full_name: str
target_branch: str
error_signature: str
risk_score: int
policy_action: str
execution_status: str = "pending"
reviewer_username: str?
reviewer_github_id: int?
mode: str = "report_only"
proposed_fix_json: dict
report_json: dict
pr_number: int?
pr_url: str?
pr_state: str?
fix_branch: str?
merge_sha: str?
loop_blocked_reason: str?
signed_report_token: str?
report_feedback_status: str?
report_feedback_note: str?
resolution_feedback_status: str?
resolution_feedback_url: str?
resolution_feedback_requested_at: datetime?
resolution_feedback_submitted_at: datetime?
created_at: datetime
updated_at: datetime
```

#### AutoFixFeedback
```python
workspace_id: PydanticObjectId
execution_id: PydanticObjectId
pipeline_run_id: PydanticObjectId
repository_full_name: str
error_signature: str
target_branch: str
reviewer_username: str?
reviewer_github_id: int?
feedback_token: str
feedback_url: str
status: str = "requested"
outcome: str?
automation_quality: str?
should_auto_apply_similar: bool?
notes: str?
requested_at: datetime
submitted_at: datetime?
created_at: datetime
updated_at: datetime
```

#### AutoFixMemory
```python
workspace_id: PydanticObjectId
repository_full_name: str
error_signature: str
memory_type: str
reviewer_username: str?
reviewer_github_id: int?
note: str?
approved_for_auto_merge: bool = False
created_at: datetime
updated_at: datetime
```

---

## 4. API Contract Specification

### 4.1 Authentication Routes (`/api/auth`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/github` | Initiate GitHub OAuth flow |
| GET | `/github/callback` | Handle OAuth callback, create session |
| GET | `/me` | Get current authenticated user |
| POST | `/logout` | Clear session cookie |

### 4.2 Workspace Routes (`/api/workspaces`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List user's workspaces |
| POST | `/` | Create new workspace |
| GET | `/{workspace_id}` | Get workspace details |
| PATCH | `/{workspace_id}` | Update workspace |
| DELETE | `/{workspace_id}` | Delete workspace |
| GET | `/{workspace_id}/repositories` | List connected repositories |
| POST | `/{workspace_id}/repositories` | Connect repository |
| DELETE | `/{workspace_id}/repositories/{repo_id}` | Disconnect repository |

### 4.3 GitHub App Routes (`/api/github` + `/api/workspaces/{id}/github`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces/{workspace_id}/github/install` | Start GitHub App installation |
| GET | `/github/installations/callback` | Handle installation callback |
| DELETE | `/workspaces/{workspace_id}/github/installation` | Disconnect GitHub App |
| GET | `/workspaces/{workspace_id}/github/events` | List recent webhook events |
| POST | `/github/webhooks` | Receive GitHub webhook events |
| POST | `/webhook/github` | Legacy webhook endpoint |

### 4.4 Auto-Fix Routes (`/api/autofix`)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/report` | View auto-fix report (signed token) |
| POST | `/report/decision` | Submit approve/reject decision |
| GET | `/feedback` | View resolution feedback form |
| POST | `/feedback` | Submit resolution feedback |

### 4.5 Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check endpoint |
| GET | `/` | Root endpoint |

---

## 5. Core Business Logic Flows

### 5.1 Webhook Processing Flow
```
GitHub Workflow Run Completes
         ↓
GitHub sends webhook to /api/github/webhooks
         ↓
Verify HMAC signature (X-Hub-Signature-256)
         ↓
Store WebhookEvent (audit)
         ↓
Find Workspace by installation_id
         ↓
Create PipelineRun record
         ↓
If KAFKA_ENABLED: push to pipeline-events topic
         ↓
Else: Process inline via pipeline_runtime
```

### 5.2 Monitor Stage (Failure Detection)
```
PipelineRun created
         ↓
Fetch workflow logs from GitHub (using installation token)
         ↓
Extract error snippets (keywords: error, failed, traceback, etc.)
         ↓
Determine health_status: healthy/failed/unknown
         ↓
If failed: push to diagnosis-required topic
         ↓
Update PipelineRun.monitor_* fields
```

### 5.3 Diagnosis Stage
```
Consume from diagnosis-required topic
         ↓
Fetch workflow logs + compare diff (base vs head commit)
         ↓
LLM Analysis → error_type, possible_causes, latest_working_change
         ↓
Store diagnosis_report_json in PipelineRun
         ↓
Push to risk-scoring (inline or via topic)
```

### 5.4 Risk Scoring Stage
```
Inputs: branch, diff size, file categories, API surface, review signals, history
         ↓
Deterministic scoring algorithm (weights defined in risk_classifier.py)
         ↓
Output: risk_score (0-100), risk_band (low/medium/high), risk_report_json
         ↓
Policy Engine: Compare against workspace thresholds
         ↓
Decision: auto_fix / approval_required / block_only
         ↓
Trigger appropriate auto-fix flow
```

### 5.5 Auto-Fix Flow
```
Policy Decision = auto_fix:
    → Generate minimal patch (max 3 files)
    → Create fix branch
    → Create PR with description
    → Optionally request reviewers
    → If auto_merge_allowed + memory_approved: auto-merge

Policy Decision = approval_required:
    → Generate report with signed token
    → Send Slack notification + email with report link
    → Wait for human decision via /api/autofix/report/decision
    → On approve: create PR (same as above)
    → On reject: close/discard

Policy Decision = block_only:
    → Create report only
    → Notify via Slack
    → No PR created
```

---

## 6. Improvements Plan

### 6.1 Code Quality & Maintainability
| Priority | Improvement | Description |
|----------|-------------|-------------|
| HIGH | Type Hints | Add comprehensive type annotations across all modules |
| HIGH | Unit Tests | Add pytest suite for services, routers, models |
| HIGH | Integration Tests | Testcontainers for MongoDB + Kafka integration tests |
| MEDIUM | Linting/Format | Ruff + Black + mypy in CI pipeline |
| MEDIUM | API Documentation | OpenAPI/Swagger with examples |
| MEDIUM | Structured Logging | JSON logging with correlation IDs |
| LOW | Pre-commit Hooks | Husky/lint-staged for frontend, pre-commit for backend |

### 6.2 Architecture Improvements
| Priority | Improvement | Description |
|----------|-------------|-------------|
| HIGH | Kafka Consumer Groups | Proper partition assignment, rebalance handling |
| HIGH | Graceful Shutdown | Signal handling for in-flight message completion |
| HIGH | Retry/Dead Letter | Exponential backoff + DLQ for failed processing |
| MEDIUM | Caching Layer | Redis for GitHub API responses, LLM responses |
| MEDIUM | Rate Limiting | Token bucket for GitHub API, LLM API |
| MEDIUM | Circuit Breaker | Hystrix-style for external dependencies |
| LOW | Event Sourcing | Full event store for audit/replay |

### 6.3 Security Hardening
| Priority | Improvement | Description |
|----------|-------------|-------------|
| CRITICAL | Secret Encryption | Encrypt GitHub tokens, LLM keys at rest (Fernet/AES-GCM) |
| HIGH | Token Rotation | Automatic GitHub installation token refresh |
| HIGH | Input Validation | Pydantic v2 strict mode, sanitize all inputs |
| HIGH | CORS Policy | Strict origin validation, no wildcards in prod |
| MEDIUM | Audit Logging | Immutable audit trail for sensitive operations |
| MEDIUM | Dependency Scanning | Dependabot + pip-audit + npm audit in CI |
| LOW | mTLS | Service-to-service encryption for future microservices |

### 6.4 Observability
| Priority | Improvement | Description |
|----------|-------------|-------------|
| HIGH | Metrics | Prometheus metrics (latency, throughput, errors, business KPIs) |
| HIGH | Distributed Tracing | OpenTelemetry + Jaeger/Tempo |
| HIGH | Health Checks | Liveness/readiness probes with dependency checks |
| MEDIUM | Alerting | PrometheusRule for critical paths |
| MEDIUM | Dashboard | Grafana dashboard for pipeline health |
| LOW | Profiling | Continuous profiling (PySpy) |

### 6.5 Feature Enhancements
| Priority | Improvement | Description |
|----------|-------------|-------------|
| HIGH | Multi-repo per Workspace | Support monitoring multiple repos per workspace |
| HIGH | Branch Policies | Per-branch risk profiles (main vs feature vs hotfix) |
| HIGH | Custom Risk Rules | DSL for org-specific risk scoring rules |
| MEDIUM | GitLab/Bitbucket Support | Abstract SCM provider interface |
| MEDIUM | Slack Bot | Interactive Slack app (not just webhooks) |
| MEDIUM | Webhook Replay | UI to replay failed webhook events |
| LOW | Multi-tenancy | True multi-org with RBAC |
| LOW | Plugin System | Custom diagnosis/fix agents |

### 6.6 Frontend Improvements
| Priority | Improvement | Description |
|----------|-------------|-------------|
| HIGH | State Management | TanStack Query / React Query for server state |
| HIGH | Error Boundaries | Graceful error UI, retry mechanisms |
| HIGH | Accessibility | WCAG 2.1 AA compliance |
| MEDIUM | Real-time Updates | WebSocket/SSE for live pipeline status |
| MEDIUM | Dark Mode Polish | Complete theme system with CSS variables |
| MEDIUM | Mobile Responsive | Full responsive design |
| LOW | PWA Support | Service worker, offline capability |

### 6.7 Developer Experience
| Priority | Improvement | Description |
|----------|-------------|-------------|
| HIGH | Dev Container | VS Code devcontainer.json for consistent env |
| HIGH | Makefile/Taskfile | Common commands (dev, test, lint, build, deploy) |
| HIGH | LocalStack | Local AWS/GCP emulation for CI |
| MEDIUM | Seed Data | Deterministic test fixtures |
| MEDIUM | API Mocking | MSW for frontend development |
| LOW | Documentation Site | Docusaurus/MkDocs for auto-generated docs |

---

## 7. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Set up monorepo structure with proper tooling
- [ ] Configure TypeScript + Python type checking
- [ ] Set up CI/CD pipeline (GitHub Actions)
- [ ] Implement database models with full type hints
- [ ] Create shared constants/enums package
- [ ] Set up structured logging + correlation IDs

### Phase 2: Core Backend (Week 3-4)
- [ ] Implement auth system (JWT + cookies) with tests
- [ ] Build GitHub OAuth + App integration
- [ ] Implement webhook receiver with signature verification
- [ ] Create PipelineRun processing pipeline (monitor → diagnosis → risk)
- [ ] Build risk classifier with deterministic scoring
- [ ] Unit test all services with mocking

### Phase 3: Auto-Fix Engine (Week 5-6)
- [ ] Implement LLM gateway with provider fallback
- [ ] Build auto-fix service (patch generation, PR creation)
- [ ] Create policy engine with configurable thresholds
- [ ] Implement feedback loop (report + resolution)
- [ ] Build memory system for learned patterns
- [ ] Integration tests for full pipeline

### Phase 4: Frontend (Week 7-8)
- [ ] Set up React + TypeScript + Tailwind + React Query
- [ ] Build authentication flow + protected routes
- [ ] Create Dashboard with workspace management
- [ ] Build Workspace detail page with pipeline runs
- [ ] Implement Auto-fix Report + Feedback pages
- [ ] Add real-time updates via SSE
- [ ] E2E tests with Playwright

### Phase 5: Operations & Observability (Week 9-10)
- [ ] Kafka consumer optimization + DLQ
- [ ] Prometheus metrics + Grafana dashboards
- [ ] OpenTelemetry tracing
- [ ] Health checks + readiness probes
- [ ] Deployment configs (Docker, Render, Vercel)
- [ ] Secrets management integration
- [ ] Load testing + performance baselines

### Phase 6: Polish & Hardening (Week 11-12)
- [ ] Security audit + penetration testing
- [ ] Accessibility audit
- [ ] Documentation site
- [ ] Migration scripts from original
- [ ] Runbook creation
- [ ] Release preparation

---

## 8. Development Standards

### 8.1 Code Style
- **Python**: Ruff (lint) + Black (format) + mypy (type check)
- **TypeScript**: ESLint + Prettier + tsc --noEmit
- **Commits**: Conventional Commits (feat/fix/docs/refactor/chore)
- **Branches**: feature/, fix/, chore/, release/

### 8.2 Testing Strategy
```
Unit Tests (fast, isolated)
    ↓
Integration Tests (Testcontainers: MongoDB, Kafka)
    ↓
Contract Tests (API schema validation)
    ↓
E2E Tests (Playwright: critical user flows)
    ↓
Load Tests (Locust: 100 concurrent webhooks)
```

### 8.3 Git Workflow
- `main`: Production-ready, protected
- `develop`: Integration branch
- Feature branches from `develop`
- PRs require: CI pass, 1 approval, up-to-date with develop
- Release tags: `v{major}.{minor}.{patch}`

---

## 9. Migration Strategy

### 9.1 Data Migration
1. Export original MongoDB collections
2. Transform to new schema (if changed)
3. Import to new database
4. Verify record counts + sample data

### 9.2 Zero-Downtime Cutover
1. Deploy new version alongside old (blue-green)
2. Route traffic via feature flag
3. Monitor error rates + latency
4. Full cutover after validation
5. Keep old version for 1 week rollback

### 9.3 Configuration Migration
- Map `.env` variables 1:1
- Document any new required variables
- Provide migration script for config validation

---

## 10. Success Criteria

### 10.1 Functional Parity
- [ ] All original API endpoints work identically
- [ ] All original UI flows work identically
- [ ] Same webhook processing behavior
- [ ] Same risk scoring outputs for same inputs
- [ ] Same auto-fix PR generation

### 10.2 Quality Gates
- [ ] Unit test coverage ≥ 80%
- [ ] Integration test coverage ≥ 60%
- [ ] Zero critical/high vulnerabilities
- [ ] Lighthouse score ≥ 90 (perf, accessibility, SEO)
- [ ] p95 latency < 500ms for API endpoints
- [ ] Webhook processing < 2s end-to-end

### 10.3 Operational Readiness
- [ ] Deployable to staging with single command
- [ ] Rollback procedure documented + tested
- [ ] Runbooks for top 10 failure scenarios
- [ ] On-call rotation defined
- [ ] SLOs defined and measured

---

## 11. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GitHub API changes | Medium | High | Abstract provider, version pinning |
| LLM provider rate limits | High | Medium | Fallback chain, caching, quota mgmt |
| Kafka data loss | Low | High | Acknowledgment config, replication |
| MongoDB connection issues | Medium | High | Connection pooling, retry logic |
| Token expiration | High | Medium | Auto-refresh, monitoring alerts |
| Schema drift | Medium | Medium | Migration scripts, schema registry |

---

## 12. Appendix: Key Files Reference

### Original Files to Preserve Logic From
```
pipelineIQ/
├── config.py                 # Settings management
├── database.py               # Beanie init
├── main.py                   # App + lifespan
├── auth/
│   ├── jwt.py                # Token create/decode
│   ├── cookies.py            # Session cookie mgmt
│   └── dependencies.py       # get_current_user
├── models/
│   ├── user.py
│   ├── workspace.py
│   ├── repository.py
│   ├── webhook_event.py
│   ├── pipeline_run.py
│   ├── autofix_execution.py
│   ├── autofix_feedback.py
│   └── autofix_memory.py
├── routers/
│   ├── auth.py
│   ├── workspaces.py
│   ├── github_app.py
│   ├── autofix.py
│   └── repositories.py
└── services/
    ├── pipeline_runtime.py   # Event queue + stage orchestration
    ├── risk_classifier.py    # Deterministic scoring
    ├── autofix_service.py    # Patch gen + PR mgmt
    ├── llm_gateway.py        # Multi-provider LLM client
    ├── github_app.py         # GitHub App operations
    ├── error_detection.py    # Log parsing
    ├── slack_notifier.py
    └── state_reset.py
```

### Frontend Key Files
```
pipelineIQ-frontend/src/
├── api/client.js             # Axios + interceptors
├── context/
│   ├── AuthContext.jsx       # User session
│   └── ThemeContext.jsx      # Dark/light mode
├── components/
│   ├── Navbar.jsx
│   ├── Modal.jsx
│   ├── ProtectedRoute.jsx
│   ├── WorkspaceCard.jsx
│   ├── RepoCard.jsx
│   └── ThemeToggle.jsx
└── pages/
    ├── LoginPage.jsx
    ├── DashboardPage.jsx
    ├── WorkspacePage.jsx
    ├── AutoFixReportPage.jsx
    └── AutoFixFeedbackPage.jsx
```

---

## 13. Next Steps

1. **Review this plan** with stakeholders
2. **Prioritize improvements** based on team capacity
3. **Set up new repository** with monorepo tooling (Turborepo/Nx)
4. **Begin Phase 1** implementation
5. **Weekly sync** to track progress against milestones

---

*Document Version: 1.0*
*Created: 2026-09-26*
*Project: PipelineIQ Recreation*
