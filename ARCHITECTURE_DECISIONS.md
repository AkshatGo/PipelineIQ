# Architecture Decision Records (ADRs)

## ADR-001: Monorepo vs Polyrepo
**Status**: Accepted
**Date**: 2026-09-26

### Context
The original project uses a single repository with three main components: Flask demo app, FastAPI backend, and React frontend.

### Decision
Use a **monorepo** structure with clear package boundaries:
- `packages/backend` - FastAPI application
- `packages/frontend` - React application
- `packages/shared` - Shared types, constants, utilities
- `packages/docs` - Documentation site

### Rationale
- Atomic commits across frontend/backend
- Shared TypeScript/Python types via shared package
- Simplified CI/CD (single pipeline)
- Easier refactoring across boundaries
- Tooling: Turborepo for build orchestration

---

## ADR-002: Database - MongoDB with Beanie ODM
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original project uses MongoDB with Beanie ODM. Need to evaluate if this is the right choice for recreation.

### Decision
**Keep MongoDB + Beanie** for the following reasons:
- Document model fits variable pipeline event payloads
- Beanie provides async ODM with Pydantic integration
- Schema flexibility for evolving event structures
- MongoDB Atlas managed service for production

### Alternatives Considered
- PostgreSQL + SQLAlchemy: More rigid schema, better for relational data
- DynamoDB: Vendor lock-in, less query flexibility

---

## ADR-003: Message Queue - Apache Kafka (Optional)
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original project supports Kafka as optional event-driven backbone with inline fallback.

### Decision
**Keep Kafka as optional** with these improvements:
- Use KRaft mode (no ZooKeeper)
- Proper consumer group management
- Dead Letter Queue for failed messages
- Exactly-once semantics where critical

### Rationale
- Decouples monitor/diagnosis/risk stages
- Enables horizontal scaling of consumers
- Replay capability for debugging
- Can be disabled for simple deployments

---

## ADR-004: Authentication - JWT in HttpOnly Cookies
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original uses JWT stored in HttpOnly, SameSite=Lax cookies with GitHub OAuth.

### Decision
**Keep cookie-based sessions** with these enhancements:
- CSRF protection via SameSite=Lax + Double Submit Cookie pattern
- Short-lived access tokens (15 days) with refresh rotation
- Secure flag in production
- Token blacklisting on logout

### Alternatives Considered
- Bearer tokens in localStorage: Vulnerable to XSS
- Server-side sessions: Requires sticky sessions or shared store

---

## ADR-005: LLM Provider Abstraction
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original supports GitHub Models, Groq, OpenAI-compatible endpoints with primary/fallback per agent.

### Decision
**Implement provider-agnostic LLM Gateway** with:
- Unified interface for chat/completion
- Automatic fallback chain per agent type
- Token usage tracking per provider
- Request/response logging for debugging
- Circuit breaker per provider

### Supported Providers (Priority Order)
1. GitHub Models (free tier available)
2. Groq (fast inference)
3. OpenAI-compatible (self-hosted, Azure, etc.)

---

## ADR-006: Frontend State Management - TanStack Query
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original uses React Context + manual fetch in components.

### Decision
**Migrate to TanStack Query (React Query)** for server state:
- Automatic caching, deduplication, background refetch
- Optimistic updates for mutations
- DevTools for debugging
- SSR support if needed

### Local UI State
- React Context for auth, theme, modals
- useReducer for complex form state

---

## ADR-007: API Layer - FastAPI with Pydantic v2
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original uses FastAPI with Pydantic v1-style models.

### Decision
**Upgrade to Pydantic v2** with:
- Strict mode for input validation
- Computed fields for derived data
- Model config for serialization
- TypeAdapter for non-model validation

### Benefits
- 5-10x faster validation
- Better error messages
- Native generic support

---

## ADR-008: Deployment - Vercel + Render
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original deployment guide specifies Vercel (frontend) + Render (backend).

### Decision
**Keep Vercel + Render** with these improvements:
- Preview deployments for PRs
- Environment-specific configs
- Health checks on Render
- Vercel rewrites for `/api/*` proxy

### Future Consideration
- Kubernetes for multi-region
- Cloudflare Workers for edge functions

---

## ADR-009: Error Handling - Structured Errors with Codes
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original uses generic HTTPException with string details.

### Decision
**Implement structured error responses**:
```json
{
  "error": {
    "code": "GITHUB_WEBHOOK_INVALID_SIGNATURE",
    "message": "Invalid webhook signature",
    "details": {},
    "request_id": "uuid",
    "timestamp": "ISO8601"
  }
}
```

### Error Code Categories
- `AUTH_*`: Authentication/authorization
- `GITHUB_*`: GitHub API errors
- `LLM_*`: LLM provider errors
- `KAFKA_*`: Message queue errors
- `DB_*`: Database errors
- `VALIDATION_*`: Input validation
- `INTERNAL_*`: Unexpected errors

---

## ADR-010: Configuration - Pydantic Settings + .env
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original uses pydantic-settings with single `.env` file.

### Decision
**Keep pydantic-settings** with environment-specific files:
- `.env.local` - Local development (gitignored)
- `.env.staging` - Staging environment
- `.env.production` - Production (injected via platform)
- `.env.example` - Template with documentation

### Secret Management
- Production: Platform secrets (Render, Vercel)
- Local: `.env.local` with gitignore
- CI: GitHub Actions secrets

---

## ADR-011: Testing - Pyramid Strategy
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original has no tests.

### Decision
**Implement comprehensive test pyramid**:

| Layer | Tools | Coverage Target |
|-------|-------|-----------------|
| Unit | pytest, vitest | 80% |
| Integration | Testcontainers (MongoDB, Kafka) | 60% |
| Contract | schemathesis, pact | Key APIs |
| E2E | Playwright | Critical flows |
| Load | Locust | 100 concurrent webhooks |

---

## ADR-012: Observability - OpenTelemetry + Prometheus
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original has basic logging only.

### Decision
**Implement three pillars**:

1. **Metrics** (Prometheus)
   - RED metrics (Rate, Errors, Duration) per endpoint
   - Business metrics (pipeline runs, fix success rate)
   - Custom buckets for latency histograms

2. **Logs** (Structured JSON)
   - Correlation IDs via middleware
   - Structured fields for querying
   - Log levels: DEBUG, INFO, WARN, ERROR

3. **Traces** (OpenTelemetry)
   - Auto-instrumentation for FastAPI, HTTPX, Motor
   - Custom spans for LLM calls, GitHub API
   - Export to Jaeger/Tempo

---

## ADR-013: Security - Defense in Depth
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original has basic security (webhook verification, JWT auth).

### Decision
**Implement layered security**:

| Layer | Measures |
|-------|----------|
| Network | CORS restrict, Rate limiting, WAF (future) |
| Application | Input validation, Output encoding, CSP headers |
| Data | Encryption at rest (MongoDB), Field-level encryption for secrets |
| Identity | Short-lived tokens, MFA ready, Audit logging |
| Supply Chain | Dependency scanning, SBOM, Signed containers |

---

## ADR-014: Frontend Build - Vite + TypeScript
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original uses Vite with JavaScript.

### Decision
**Migrate to TypeScript** with:
- Strict mode enabled
- Path aliases for clean imports
- React 19 + Vite 8
- Tailwind CSS v4 (new engine)

---

## ADR-015: GitHub App vs OAuth App Separation
**Status**: Accepted
**Date**: 2026-09-26

### Context
Original correctly separates GitHub OAuth App (user auth) from GitHub App (repo integration).

### Decision
**Maintain strict separation**:
- OAuth App: Only `read:user`, `read:org` scopes
- GitHub App: Repository permissions (Actions, Contents, PRs)
- Different client IDs/secrets
- Different callback URLs

---

*End of ADRs*
