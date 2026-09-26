# Implementation Phases - Detailed Task Breakdown

## Phase 1: Foundation (Week 1-2)

### Goals
- Monorepo setup with Turborepo
- Type-safe foundation for both Python and TypeScript
- CI/CD pipeline with quality gates
- Shared types package

### Tasks

#### 1.1 Monorepo Setup
```bash
# Create structure
mkdir pipelineiq && cd pipelineiq
npm init -w packages/backend packages/frontend packages/shared packages/docs
```

**`turbo.json`**:
```json
{
  "$schema": "https://turbo.build/schema.json",
  "pipeline": {
    "build": { "dependsOn": ["^build"], "outputs": ["dist/**"] },
    "test": { "outputs": ["coverage/**"] },
    "lint": {},
    "typecheck": {},
    "dev": { "cache": false, "persistent": true }
  }
}
```

**Root `package.json`**:
```json
{
  "name": "pipelineiq",
  "private": true,
  "workspaces": ["packages/*"],
  "scripts": {
    "dev": "turbo run dev",
    "build": "turbo run build",
    "test": "turbo run test",
    "lint": "turbo run lint",
    "typecheck": "turbo run typecheck",
    "db:push": "turbo run db:push --filter=backend",
    "db:studio": "turbo run db:studio --filter=backend"
  },
  "devDependencies": {
    "turbo": "latest",
    "typescript": "latest"
  }
}
```

#### 1.2 Backend Foundation
**`packages/backend/pyproject.toml`**:
```toml
[project]
name = "pipelineiq-backend"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.34.0",
    "motor>=3.5.0",
    "beanie>=1.26.0",
    "python-jose[cryptography]>=3.4.0",
    "httpx>=0.28.0",
    "pydantic-settings>=2.8.0",
    "python-dotenv>=1.1.0",
    "aiokafka>=0.10.0",
    "openai>=1.51.0",
    "pydantic>=2.7.0",
    "python-multipart>=0.0.9",
    "cryptography>=42.0.0",
    "structlog>=24.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "pytest-mock>=3.12.0",
    "httpx>=0.28.0",
    "ruff>=0.4.0",
    "black>=24.0.0",
    "mypy>=1.10.0",
    "testcontainers>=4.7.0",
    "faker>=24.0.0",
    "factory-boy>=3.3.0",
]

[tool.ruff]
target-version = "py311"
line-length = 100
select = ["E", "F", "I", "UP", "B", "C4", "ANN", "ARG", "PTH", "T20", "SIM", "RET"]
ignore = ["ANN101", "ARG001", "ARG002", "S101", "T201", "T203"]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_unused_ignores = true
disallow_untyped_defs = true
```

**`packages/backend/src/config.py`**:
```python
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )
    
    # Core
    MONGODB_URI: str
    MONGODB_DB_NAME: str = "pipelineiq"
    
    # Auth
    JWT_SECRET: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    SESSION_EXPIRY_DAYS: int = 15
    COOKIE_SECURE: bool = False
    COOKIE_DOMAIN: str = ""
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:5173"
    
    # GitHub OAuth
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str
    GITHUB_OAUTH_SCOPES: str = "read:user read:org"
    
    # GitHub App
    GITHUB_APP_ID: str
    GITHUB_APP_SLUG: str
    GITHUB_APP_PRIVATE_KEY: str
    GITHUB_APP_WEBHOOK_SECRET: str
    GITHUB_APP_INSTALL_URL: str | None = None
    
    # LLM Providers
    OPENAI_API_KEY: str | None = None
    OPENAI_API_BASE_URL: str = "https://api.openai.com/v1"
    GROQ_API_KEY: str | None = None
    GROQ_API_BASE_URL: str = "https://api.groq.com/openai/v1"
    GITHUB_TOKEN: str | None = None
    GITHUB_MODELS_API_BASE_URL: str = "https://models.github.ai/inference"
    
    # Agent Configs (use dict for flexibility)
    MONITOR_AGENT_PRIMARY_PROVIDER: str = "github_models"
    MONITOR_AGENT_PRIMARY_MODEL: str = "openai/gpt-4o-mini"
    MONITOR_AGENT_FALLBACK_PROVIDER: str = "groq"
    MONITOR_AGENT_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"
    
    DIAGNOSIS_AGENT_PRIMARY_PROVIDER: str = "groq"
    DIAGNOSIS_AGENT_PRIMARY_MODEL: str = "openai/gpt-oss-120b"
    DIAGNOSIS_AGENT_FALLBACK_PROVIDER: str = "github_models"
    DIAGNOSIS_AGENT_FALLBACK_MODEL: str = "openai/gpt-4.1"
    
    RISK_AGENT_PRIMARY_PROVIDER: str = "github_models"
    RISK_AGENT_PRIMARY_MODEL: str = "gpt-4o-mini"
    RISK_AGENT_FALLBACK_PROVIDER: str = "groq"
    RISK_AGENT_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"
    
    AUTOFIX_AGENT_PRIMARY_PROVIDER: str = "github_models"
    AUTOFIX_AGENT_PRIMARY_MODEL: str = "gpt-4o-mini"
    AUTOFIX_AGENT_FALLBACK_PROVIDER: str = "groq"
    AUTOFIX_AGENT_FALLBACK_MODEL: str = "llama-3.3-70b-versatile"
    AUTOFIX_REPORT_EXPIRY_HOURS: int = 168
    AUTOFIX_FEEDBACK_EXPIRY_HOURS: int = 720
    
    # Slack
    SLACK_ENABLED: bool = False
    SLACK_WEBHOOK_URL: str | None = None
    SLACK_DEFAULT_CHANNEL: str | None = None
    SLACK_DEVOPS_MENTION_DEFAULT: str | None = None
    
    # Kafka
    KAFKA_ENABLED: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_PIPELINE_EVENTS_TOPIC: str = "pipeline-events"
    KAFKA_DIAGNOSIS_REQUIRED_TOPIC: str = "diagnosis-required"
    KAFKA_MONITOR_GROUP_ID: str = "pipelineiq-monitor-agent"
    KAFKA_DIAGNOSIS_GROUP_ID: str = "pipelineiq-diagnosis-agent"
    
    # Security
    ENCRYPTION_KEY: str | None = None  # Fernet key
    RATE_LIMIT_ENABLED: bool = True
    
    # Observability
    LOG_LEVEL: str = "INFO"
    OTEL_EXPORTER_OTLP_ENDPOINT: str | None = None
    
    @property
    def github_app_install_url(self) -> str:
        return self.GITHUB_APP_INSTALL_URL or f"https://github.com/apps/{self.GITHUB_APP_SLUG}/installations/new"
    
    @property
    def github_app_private_key_pem(self) -> str:
        return self.GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n")

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
```

#### 1.3 Frontend Foundation
**`packages/frontend/package.json`**:
```json
{
  "name": "pipelineiq-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "format": "prettier --write \"src/**/*.{ts,tsx,json,css,md}\"",
    "typecheck": "tsc --noEmit",
    "test": "vitest",
    "test:coverage": "vitest --coverage",
    "test:ui": "vitest --ui",
    "test:e2e": "playwright test",
    "test:e2e:ci": "playwright test --reporter=line",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "@tanstack/react-query": "^5.0.0",
    "axios": "^1.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^9.0.0",
    "eslint-plugin-react-hooks": "^5.0.0",
    "eslint-plugin-react-refresh": "^0.4.0",
    "postcss": "^8.4.0",
    "prettier": "^3.2.0",
    "prettier-plugin-tailwindcss": "^0.5.0",
    "tailwindcss": "^3.4.0",
    "typescript": "^5.4.0",
    "vite": "^5.0.0",
    "vitest": "^1.3.0",
    "@vitest/coverage-v8": "^1.3.0",
    "@playwright/test": "^1.42.0",
    "msw": "^2.2.0"
  }
}
```

#### 1.4 Shared Types Package
**`packages/shared/python/pipelineiq_shared/models.py`**:
```python
# Shared Pydantic models for API contracts
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class HealthStatus(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    FAILED = "failed"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class PolicyAction(str, Enum):
    AUTO_FIX = "auto_fix"
    APPROVAL_REQUIRED = "approval_required"
    BLOCK_ONLY = "block_only"

class RiskProfile(BaseModel):
    production_branch: str = "main"
    require_approval_above: int = Field(default=60, ge=0, le=100)
    auto_fix_below: int = Field(default=30, ge=0, le=100)

class GitHubOrganization(BaseModel):
    id: int
    login: str
    avatar_url: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    github_id: int
    username: str
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    organizations: List[GitHubOrganization]
    last_login: datetime
    created_at: datetime
```

**`packages/shared/typescript/pipelineiq-shared/src/api.ts`**:
```typescript
// Shared TypeScript types matching backend
export enum HealthStatus {
  Unknown = "unknown",
  Healthy = "healthy",
  Failed = "failed"
}

export enum ProcessingStatus {
  Pending = "pending",
  Running = "running",
  Completed = "completed",
  Failed = "failed"
}

export enum RiskBand {
  Low = "low",
  Medium = "medium",
  High = "high"
}

export interface RiskProfile {
  production_branch: string;
  require_approval_above: number;
  auto_fix_below: number;
}

export interface GitHubOrganization {
  id: number;
  login: string;
  avatar_url?: string;
  description?: string;
  url?: string;
}

export interface UserResponse {
  id: string;
  github_id: number;
  username: string;
  display_name?: string;
  email?: string;
  avatar_url?: string;
  organizations: GitHubOrganization[];
  last_login: string;
  created_at: string;
}

export interface WorkspaceResponse {
  id: string;
  name: string;
  description?: string;
  owner_id: string;
  github_installation_id?: number;
  github_repository_id?: number;
  github_repo_full_name?: string;
  github_default_branch?: string;
  github_repo_private?: boolean;
  github_repo_html_url?: string;
  github_account_login?: string;
  github_account_type?: string;
  slack_devops_mention?: string;
  risk_profile: RiskProfile;
  connected_at?: string;
  last_webhook_event_at?: string;
  created_at: string;
  updated_at: string;
  connected: boolean;
}
```

---

## Phase 2: Core Backend (Week 3-4)

### Goals
- Complete auth system
- GitHub OAuth + App integration
- Webhook receiver
- Pipeline processing pipeline

### Tasks

#### 2.1 Auth System
- [ ] `src/auth/jwt.py` - Token create/verify with rotation
- [ ] `src/auth/cookies.py` - Secure cookie handling
- [ ] `src/auth/dependencies.py` - `get_current_user` with refresh
- [ ] `src/routers/auth.py` - OAuth flow endpoints
- [ ] Unit tests for all auth components

#### 2.2 Database Models
- [ ] All models from DATA_MODELS.md
- [ ] Indexes and TTL configuration
- [ ] Field-level encryption for secrets

#### 2.3 GitHub Integration
- [ ] `src/services/github_app.py` - Installation tokens, API calls
- [ ] `src/routers/github_app.py` - Install callback, webhook receiver
- [ ] Webhook signature verification
- [ ] Installation token caching with TTL

#### 2.4 Pipeline Runtime
- [ ] `src/services/pipeline_runtime.py` - Stage orchestration
- [ ] Inline processing (KAFKA_ENABLED=false)
- [ ] Kafka producer/consumer (KAFKA_ENABLED=true)
- [ ] Graceful shutdown handling

#### 2.5 Monitor Stage
- [ ] `src/services/error_detection.py` - Log parsing
- [ ] GitHub workflow logs fetching
- [ ] Error snippet extraction

---

## Phase 3: Auto-Fix Engine (Week 5-6)

### Goals
- LLM gateway with fallback
- Risk classifier
- Auto-fix service
- Feedback loop

### Tasks

#### 3.1 LLM Gateway
- [ ] `src/services/llm_gateway.py` - Unified interface
- [ ] Provider implementations (GitHub Models, Groq, OpenAI)
- [ ] Fallback chain per agent
- [ ] Token usage tracking
- [ ] Circuit breaker

#### 3.2 Diagnosis Stage
- [ ] `src/services/diagnosis.py` - LLM-based diagnosis
- [ ] Diff fetching and processing
- [ ] Structured output parsing

#### 3.3 Risk Classifier
- [ ] `src/services/risk_classifier.py` - Deterministic scoring
- [ ] Signal extraction (branch, diff, files, reviews)
- [ ] Weighted scoring algorithm
- [ ] Policy engine

#### 3.4 Auto-Fix Service
- [ ] `src/services/autofix_service.py` - Patch generation
- [ ] GitHub PR creation
- [ ] Branch management
- [ ] Reviewer assignment
- [ ] Auto-merge logic with memory check

#### 3.5 Feedback & Memory
- [ ] Report feedback endpoint
- [ ] Resolution feedback endpoint
- [ ] Memory system for learned patterns
- [ ] Signed URL generation/validation

---

## Phase 4: Frontend (Week 7-8)

### Goals
- Complete React application
- TanStack Query integration
- All pages functional
- E2E tests passing

### Tasks

#### 4.1 Core Setup
- [ ] Vite + React + TypeScript + Tailwind
- [ ] TanStack Query provider + query client
- [ ] Axios instance with interceptors
- [ ] React Router with protected routes
- [ ] AuthContext + ThemeContext

#### 4.2 Components
- [ ] Layout: Navbar, ThemeToggle
- [ ] Feedback: Modal, Toast
- [ ] Data: WorkspaceCard, RepoCard
- [ ] Forms: Validated inputs
- [ ] Loading/Error states

#### 4.3 Pages
- [ ] LoginPage - GitHub OAuth
- [ ] DashboardPage - Workspaces + Orgs
- [ ] WorkspacePage - Pipeline runs, tabs (Monitor/Diagnosis/Risk/Auto-fix)
- [ ] AutoFixReportPage - Approve/Reject
- [ ] AutoFixFeedbackPage - Resolution feedback

#### 4.4 Real-time Updates
- [ ] SSE endpoint for pipeline run updates
- [ ] React Query subscription
- [ ] Optimistic updates

#### 4.5 Testing
- [ ] Unit tests (vitest + RTL)
- [ ] E2E tests (Playwright) - critical flows
- [ ] Accessibility audit (axe-core)

---

## Phase 5: Operations & Observability (Week 9-10)

### Goals
- Production-ready observability
- Deployment configs
- Performance baselines

### Tasks

#### 5.1 Metrics & Tracing
- [ ] Prometheus metrics (RED + business)
- [ ] OpenTelemetry instrumentation
- [ ] Custom spans for LLM calls
- [ ] Grafana dashboards

#### 5.2 Logging
- [ ] Structured JSON logging (structlog)
- [ ] Correlation ID middleware
- [ ] Log levels per environment
- [ ] PII redaction

#### 5.3 Health & Readiness
- [ ] Liveness probe (`/health`)
- [ ] Readiness probe (`/ready`) with dependency checks
- [ ] Startup probe for slow initialization

#### 5.4 Deployment
- [ ] `packages/backend/Dockerfile` (multi-stage)
- [ ] `packages/frontend/Dockerfile` (nginx)
- [ ] `docker-compose.prod.yml`
- [ ] Render/Vercel configuration docs
- [ ] GitHub Actions workflows

#### 5.5 Security Hardening
- [ ] Rate limiting (slowapi)
- [ ] CSP headers
- [ ] Dependency scanning in CI
- [ ] Secret scanning in CI
- [ ] Container scanning

#### 5.6 Load Testing
- [ ] Locust test scenarios
- [ ] Baseline measurements
- [ ] Bottleneck identification

---

## Phase 6: Polish & Hardening (Week 11-12)

### Goals
- Security audit
- Accessibility compliance
- Documentation
- Release preparation

### Tasks

#### 6.1 Security
- [ ] Penetration testing (internal)
- [ ] Dependency audit
- [ ] Secret rotation procedure
- [ ] Incident response drill

#### 6.2 Accessibility
- [ ] WCAG 2.1 AA audit
- [ ] Keyboard navigation
- [ ] Screen reader testing
- [ ] Color contrast fixes

#### 6.3 Documentation
- [ ] API docs (auto-generated from OpenAPI)
- [ ] Architecture docs
- [ ] Runbooks for top 10 scenarios
- [ ] Developer onboarding guide

#### 6.4 Migration
- [ ] Data migration script (tested)
- [ ] Config migration guide
- [ ] Rollback procedures tested

#### 6.5 Release
- [ ] Version tagging strategy
- [ ] Changelog generation
- [ ] Release notes
- [ ] Post-release monitoring plan

---

## Definition of Done per Phase

| Phase | Criteria |
|-------|----------|
| 1 | Monorepo builds, CI passes, shared types published |
| 2 | Auth works, webhook received, pipeline runs created in DB |
| 3 | End-to-end: failure → diagnosis → risk → auto-fix PR created |
| 4 | All UI flows work, E2E tests pass, accessible |
| 5 | Metrics visible, deployed to staging, load test passes |
| 6 | Security audit clean, docs complete, ready for production |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| LLM provider changes | Abstract interface, version pinning, fallback chain |
| GitHub API breaking | Integration tests with recorded cassettes |
| Kafka complexity | Start with inline, enable Kafka late |
| Migration data loss | Automated verification, rollback tested |
| Performance issues | Continuous profiling, load test early |

---

*Updated: 2026-09-26*
