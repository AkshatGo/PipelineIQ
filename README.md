# PipelineIQ

PipelineIQ is an AI-powered CI/CD failure intelligence and auto-remediation platform. The
repository now contains the initial working monorepo alongside the original planning documents.

## Current implementation

- FastAPI service with health/readiness endpoints and structured error handling
- GitHub OAuth with signed state, encrypted provider tokens, and HttpOnly cookie sessions
- Deterministic, explainable risk-scoring and policy endpoint
- Verified GitHub webhook signatures with delivery idempotency and event normalization
- MongoDB persistence for all eight planned collections and their indexes
- React + TypeScript dashboard preview using TanStack Query
- Shared TypeScript and Python contracts
- MongoDB and optional Kafka local infrastructure
- CI quality gates for linting, type checking, builds, and tests

### Run locally

```bash
cp .env.example .env.local
make install
make infra-up
make dev
```

The dashboard runs at `http://localhost:5173`, the API at `http://localhost:8000`, and interactive
API documentation at `http://localhost:8000/docs`.

GitHub webhooks are accepted at `POST /api/github/webhooks` after setting
`GITHUB_APP_WEBHOOK_SECRET`. Completed workflow runs are normalized and stored once per
`X-GitHub-Delivery` value.

### Working API slice

```bash
curl -X POST http://localhost:8000/api/risk/assess \
  -H 'Content-Type: application/json' \
  -d '{"signals":{"branch":"main","files_changed":3,"lines_changed":100,"touches_sensitive_files":false,"tests_failed":true,"has_required_review":false,"prior_similar_failures":0}}'
```

## Planning documentation

This directory contains all planning documents for recreating the PipelineIQ project with the exact same core functionality while adding significant improvements.

---

## Document Index

### 📋 Core Planning
| Document | Description |
|----------|-------------|
| **[PROJECT_RECREATION_PLAN.md](./PROJECT_RECREATION_PLAN.md)** | Master plan with architecture analysis, data models, API contracts, improvements, phases, and success criteria |
| **[ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)** | 15 Architecture Decision Records (ADRs) covering monorepo, database, auth, LLM, frontend, deployment, security, observability |
| **[IMPLEMENTATION_PHASES.md](./IMPLEMENTATION_PHASES.md)** | Detailed task breakdown for 6 phases (12 weeks) with definition of done and risk mitigation |

### 🏗️ Technical Specifications
| Document | Description |
|----------|-------------|
| **[API_SPEC.md](./API_SPEC.md)** | Complete OpenAPI 3.1 specification with all endpoints, request/response schemas, error formats, webhook payloads |
| **[DATA_MODELS.md](./DATA_MODELS.md)** | Full MongoDB/Beanie schema for all 8 collections with indexes, relationships, examples, and query patterns |
| **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** | Step-by-step production deployment (Vercel + Render + MongoDB Atlas + GitHub Apps + Kafka) |

### 🔧 Developer Resources
| Document | Description |
|----------|-------------|
| **[DEVELOPER_SETUP_GUIDE.md](./DEVELOPER_SETUP_GUIDE.md)** | Local development setup with prerequisites, GitHub Apps, LLM providers, tunneling, workflows, IDE config |
| **[TESTING_STRATEGY.md](./TESTING_STRATEGY.md)** | Test pyramid with unit/integration/contract/E2E/load testing, tools, CI integration, coverage targets |
| **[SECURITY_CONSIDERATIONS.md](./SECURITY_CONSIDERATIONS.md)** | Threat model, security controls by layer, compliance, secure development practices, vulnerability disclosure |
| **[MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)** | Blue-green migration strategy, data migration scripts, config mapping, rollback procedures, validation |

---

## Quick Reference

### Original Project Structure (Preserved Logic)
```
hacktofuture4-D02/
├── pipelineIQ/              # FastAPI backend → packages/backend
├── pipelineIQ-frontend/     # React + Vite → packages/frontend
├── flask_app/               # Demo service (keep separate)
├── docs/                    # Setup guides
└── scripts/                 # Operational scripts
```

### New Monorepo Structure
```
pipelineiq/
├── packages/
│   ├── backend/             # FastAPI + Beanie + aiokafka
│   ├── frontend/            # React 19 + Vite + TanStack Query
│   ├── shared/              # Python + TypeScript shared types
│   └── docs/                # Docusaurus documentation site
├── turbo.json               # Turborepo config
└── docker-compose.*.yml     # Local/prod infrastructure
```

### Core Functionality (MUST PRESERVE)
1. ✅ GitHub OAuth 2.0 authentication
2. ✅ GitHub App installation & webhooks
3. ✅ Workflow failure detection (monitor)
4. ✅ AI diagnosis (error + diff)
5. ✅ Deterministic risk scoring (0-100)
6. ✅ Policy engine (auto-fix/approval/block)
7. ✅ Auto-fix PR generation
8. ✅ Slack notifications
9. ✅ Feedback loop (report + resolution)
10. ✅ Memory for learned patterns
11. ✅ Dashboard for workspace management

### Key Improvements
| Area | Improvement |
|------|-------------|
| **Code Quality** | Type hints, tests, linting, structured logging |
| **Architecture** | Kafka consumer groups, DLQ, caching, circuit breakers |
| **Security** | Field encryption, token rotation, rate limiting, audit logs |
| **Observability** | Prometheus, OpenTelemetry, Grafana, health checks |
| **Features** | Multi-repo, branch policies, custom rules, GitLab support |
| **Frontend** | TanStack Query, error boundaries, accessibility, real-time |
| **DX** | Dev containers, Makefile, LocalStack, MSW, docs site |

---

## Getting Started

### For Architects/Leads
1. Read **[PROJECT_RECREATION_PLAN.md](./PROJECT_RECREATION_PLAN.md)** - Full context
2. Review **[ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)** - Key technical choices
3. Check **[IMPLEMENTATION_PHASES.md](./IMPLEMENTATION_PHASES.md)** - Timeline and tasks

### For Backend Engineers
1. **[DATA_MODELS.md](./DATA_MODELS.md)** - Database schema
2. **[API_SPEC.md](./API_SPEC.md)** - API contracts
3. **[DEVELOPER_SETUP_GUIDE.md](./DEVELOPER_SETUP_GUIDE.md)** - Local dev environment
4. **[TESTING_STRATEGY.md](./TESTING_STRATEGY.md)** - Testing approach

### For Frontend Engineers
1. **[DEVELOPER_SETUP_GUIDE.md](./DEVELOPER_SETUP_GUIDE.md)** - Local dev environment
2. **[API_SPEC.md](./API_SPEC.md)** - API contracts (shared types in `packages/shared`)
3. **[TESTING_STRATEGY.md](./TESTING_STRATEGY.md)** - Frontend testing

### For DevOps/SRE
1. **[DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)** - Production deployment
2. **[SECURITY_CONSIDERATIONS.md](./SECURITY_CONSIDERATIONS.md)** - Security hardening
3. **[TESTING_STRATEGY.md](./TESTING_STRATEGY.md)** - Load testing
4. **[MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md)** - Migration strategy

### For Security Review
1. **[SECURITY_CONSIDERATIONS.md](./SECURITY_CONSIDERATIONS.md)** - Full threat model and controls
2. **[ARCHITECTURE_DECISIONS.md](./ARCHITECTURE_DECISIONS.md)** - ADR-013 Security

---

## Migration Path

```
Original (hacktofuture4-D02)          New (pipelineiq)
├── pipelineIQ/        ──────────▶    ├── packages/backend/
├── pipelineIQ-frontend/ ────────▶    ├── packages/frontend/
├── flask_app/         ──────────▶    (keep as-is or separate repo)
├── docs/              ──────────▶    packages/docs/
└── scripts/           ──────────▶    packages/backend/scripts/
```

**Zero-downtime migration** via blue-green deployment with feature flags.

---

## Success Criteria

### Functional Parity
- [ ] All original API endpoints work identically
- [ ] All original UI flows work identically
- [ ] Same webhook processing behavior
- [ ] Same risk scoring for same inputs
- [ ] Same auto-fix PR generation

### Quality Gates
- [ ] Unit test coverage ≥ 80%
- [ ] Integration test coverage ≥ 60%
- [ ] Zero critical/high vulnerabilities
- [ ] Lighthouse score ≥ 90
- [ ] p95 latency < 500ms
- [ ] Webhook processing < 2s end-to-end

### Operational Readiness
- [ ] Single-command staging deploy
- [ ] Tested rollback procedure
- [ ] Runbooks for top 10 scenarios
- [ ] SLOs defined and measured

---

## Next Steps

1. **Review** all documents with stakeholders
2. **Prioritize** improvements based on team capacity
3. **Initialize** new monorepo with Turborepo
4. **Begin Phase 1** implementation (Foundation)
5. **Weekly sync** to track progress

---

*Generated: 2026-09-26*
*Project: PipelineIQ Recreation*
*Version: 1.0*
