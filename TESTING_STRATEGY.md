# Testing Strategy

## Overview

This document defines the comprehensive testing approach for PipelineIQ, covering all layers of the test pyramid.

---

## Test Pyramid

```
                    ┌─────────────┐
                    │   E2E       │  ← Few, critical user flows
                    │  (Playwright)│
                ┌───┴─────────────┴───┐
                │   Contract          │  ← API schema validation
                │  (Schemathesis)     │
            ┌───┴───────────────────┴───┐
            │   Integration             │  ← Real dependencies
            │  (Testcontainers)         │
        ┌───┴─────────────────────────┴───┐
        │   Unit                          │  ← Fast, isolated
        │  (pytest / vitest)              │
        └─────────────────────────────────┘
```

### Coverage Targets
| Layer | Target | Tools |
|-------|--------|-------|
| Unit | ≥ 80% | pytest, vitest |
| Integration | ≥ 60% | Testcontainers |
| Contract | Key APIs | Schemathesis |
| E2E | Critical flows | Playwright |
| Load | Baseline | Locust |

---

## Backend Testing (Python)

### Unit Tests
```bash
# Run all unit tests
cd packages/backend
pytest tests/unit -v

# With coverage
pytest tests/unit --cov=src --cov-report=html

# Specific module
pytest tests/unit/services/test_risk_classifier.py -v
```

**Structure**:
```
tests/unit/
├── auth/
│   ├── test_jwt.py
│   ├── test_cookies.py
│   └── test_dependencies.py
├── models/
│   ├── test_user.py
│   ├── test_workspace.py
│   └── test_pipeline_run.py
├── routers/
│   ├── test_auth.py
│   ├── test_workspaces.py
│   └── test_github_app.py
└── services/
    ├── test_risk_classifier.py
    ├── test_autofix_service.py
    ├── test_llm_gateway.py
    └── test_pipeline_runtime.py
```

**Patterns**:
- Mock external dependencies (GitHub API, LLM providers, Kafka)
- Use `pytest-mock` for patching
- Test pure functions with parametrize
- Fast execution (< 1s per test)

### Integration Tests
```bash
# Run integration tests (requires Docker)
pytest tests/integration -v

# With specific markers
pytest tests/integration -m "mongodb" -v
pytest tests/integration -m "kafka" -v
```

**Structure**:
```
tests/integration/
├── conftest.py              # Testcontainers fixtures
├── test_database.py         # MongoDB operations
├── test_kafka_flow.py       # Producer/consumer
├── test_github_integration.py # GitHub API (with cassette)
└── test_full_pipeline.py    # End-to-end pipeline
```

**Testcontainers Fixtures** (`conftest.py`):
```python
import pytest
from testcontainers.mongodb import MongoDbContainer
from testcontainers.kafka import KafkaContainer

@pytest.fixture(scope="session")
def mongodb():
    with MongoDbContainer("mongo:7") as mongo:
        yield mongo.get_connection_url()

@pytest.fixture(scope="session")
def kafka():
    with KafkaContainer("apache/kafka:3.9.0") as kafka:
        yield kafka.get_bootstrap_server()
```

### Contract Tests
```bash
# Generate OpenAPI spec first
python -m src.generate_openapi

# Run contract tests
schemathesis run --base-url=http://localhost:8000 openapi.json
```

### Test Utilities

**Factories** (`tests/factories.py`):
```python
import factory
from factory import Faker
from src.models.user import User
from src.models.workspace import Workspace

class UserFactory(factory.Factory):
    class Meta:
        model = User
    
    github_id = factory.Sequence(lambda n: 1000 + n)
    username = factory.LazyAttribute(lambda o: f"user{o.github_id}")
    display_name = Faker("name")
    email = Faker("email")
    avatar_url = Faker("image_url")
    github_access_token = factory.LazyAttribute(lambda _: "gho_test_token")
    organizations = []
    is_active = True

class WorkspaceFactory(factory.Factory):
    class Meta:
        model = Workspace
    
    name = Faker("company")
    description = Faker("sentence")
    owner_id = factory.SubFactory(UserFactory)
```

---

## Frontend Testing (TypeScript/React)

### Unit Tests
```bash
cd packages/frontend
npm run test              # vitest
npm run test:coverage     # with coverage
npm run test:ui           # vitest UI
```

**Structure**:
```
src/
├── components/
│   ├── __tests__/
│   │   ├── Modal.test.tsx
│   │   ├── Navbar.test.tsx
│   │   └── WorkspaceCard.test.tsx
├── context/
│   ├── __tests__/
│   │   ├── AuthContext.test.tsx
│   │   └── ThemeContext.test.tsx
├── hooks/
│   ├── __tests__/
│   │   └── useWorkspaces.test.ts
└── pages/
    ├── __tests__/
    │   ├── DashboardPage.test.tsx
    │   └── WorkspacePage.test.tsx
```

**Patterns**:
- React Testing Library for component tests
- Mock TanStack Query with `createWrapper`
- Mock API client with MSW
- Test user interactions, not implementation

### E2E Tests
```bash
npm run test:e2e          # Playwright headed
npm run test:e2e:ci       # Playwright headless (CI)
npm run test:e2e:report   # View report
```

**Structure**:
```
tests/e2e/
├── auth.spec.ts           # Login flow
├── workspace.spec.ts      # Create/connect workspace
├── pipeline.spec.ts       # Trigger failure, view diagnosis
├── autofix.spec.ts        # Approve/reject auto-fix
└── utils/
    ├── test-helpers.ts
    └── github-mocks.ts
```

**Critical Flows to Test**:
1. User logs in via GitHub OAuth
2. Creates workspace with risk profile
3. Installs GitHub App on repository
4. Triggers workflow failure (simulated)
5. Views diagnosis and risk score
6. Approves auto-fix report
7. Submits resolution feedback

### MSW (Mock Service Worker) Setup
```typescript
// tests/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/auth/me', () => {
    return HttpResponse.json({
      id: '123',
      username: 'testuser',
      display_name: 'Test User',
      // ...
    })
  }),
  
  http.get('/api/workspaces', () => {
    return HttpResponse.json([{ /* workspace data */ }])
  }),
  
  // ... more handlers
]

// tests/setup.ts
import { setupServer } from 'msw/node'
import { handlers } from './mocks/handlers'

export const server = setupServer(...handlers)

// vitest.setup.ts
import { server } from './tests/setup'

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

---

## Load Testing (Locust)

### Test Scenarios
```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class PipelineIQUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Login and get session cookie
        self.client.get("/api/auth/github")
        # ... handle OAuth flow or set cookie directly
    
    @task(10)
    def view_dashboard(self):
        self.client.get("/api/workspaces")
        self.client.get("/api/auth/me")
    
    @task(5)
    def view_workspace(self):
        self.client.get("/api/workspaces/123")
        self.client.get("/api/workspaces/123/github/events")
    
    @task(1)
    def receive_webhook(self):
        # Simulate GitHub webhook
        self.client.post("/api/github/webhooks", json={
            "action": "completed",
            "workflow_run": {...}
        }, headers={
            "X-GitHub-Event": "workflow_run",
            "X-Hub-Signature-256": "sha256=..."
        })
```

### Running Load Tests
```bash
# Start backend and frontend first
cd packages/backend && uvicorn main:app --host 0.0.0.0 --port 8000

# Run Locust
cd tests/load
locust -f locustfile.py --host=http://localhost:8000

# Web UI at http://localhost:8089
# Or headless for CI:
locust -f locustfile.py --host=http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 5m --headless
```

### Baseline Targets
| Metric | Target |
|--------|--------|
| Webhook processing (p50) | < 500ms |
| Webhook processing (p95) | < 2s |
| API response (p95) | < 500ms |
| Concurrent webhooks | 100 |
| Error rate | < 0.1% |

---

## CI/CD Integration

### GitHub Actions Workflow
```yaml
# .github/workflows/test.yml
name: Test

on: [push, pull_request]

jobs:
  backend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: cd packages/backend && pip install -e ".[dev]"
      - run: cd packages/backend && pytest tests/unit --cov=src
      - uses: codecov/codecov-action@v3
  
  backend-integration:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:7
        ports: [27017:27017]
      kafka:
        image: apache/kafka:3.9.0
        ports: [9092:9092]
        env:
          KAFKA_NODE_ID: 1
          KAFKA_PROCESS_ROLES: broker,controller
          KAFKA_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
          KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
          KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
          KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
          KAFKA_CONTROLLER_QUORUM_VOTERS: 1@localhost:9093
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: cd packages/backend && pip install -e ".[dev]"
      - run: cd packages/backend && pytest tests/integration -m "mongodb or kafka"
  
  frontend-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd packages/frontend && npm ci
      - run: cd packages/frontend && npm run test:coverage
  
  frontend-e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
      - run: cd packages/frontend && npm ci
      - run: cd packages/frontend && npx playwright install --with-deps
      - run: cd packages/frontend && npm run build
      - run: cd packages/frontend && npm run test:e2e:ci
  
  contract:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
      - run: cd packages/backend && pip install -e ".[dev]"
      - run: cd packages/backend && python -m src.generate_openapi
      - run: schemathesis run --base-url=http://localhost:8000 openapi.json
```

---

## Test Data Management

### Database Seeding
```python
# scripts/seed_test_data.py
async def seed_test_data():
    # Create test user
    user = await UserFactory().insert()
    
    # Create workspace
    workspace = await WorkspaceFactory(owner_id=user.id).insert()
    
    # Create pipeline runs with various states
    for i in range(10):
        await PipelineRunFactory(
            workspace_id=workspace.id,
            health_status=random.choice(["healthy", "failed"]),
            conclusion=random.choice(["success", "failure"]),
        ).insert()
    
    print(f"Seeded: 1 user, 1 workspace, 10 pipeline runs")
```

### Test Fixtures (Pytest)
```python
# tests/conftest.py
@pytest.fixture
async def test_user(db):
    user = await UserFactory().insert()
    yield user
    await user.delete()

@pytest.fixture
async def test_workspace(db, test_user):
    ws = await WorkspaceFactory(owner_id=test_user.id).insert()
    yield ws
    await ws.delete()

@pytest.fixture
async def authenticated_client(test_user):
    # Create test client with session cookie
    client = TestClient(app)
    token = create_access_token(str(test_user.id))
    client.cookies.set("piq_session", token)
    return client
```

---

## Quality Gates

### Pre-commit (Local)
```bash
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
      - id: ruff-format
  - repo: https://github.com/psf/black
    rev: 24.4.0
    hooks:
      - id: black
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.10.0
    hooks:
      - id: mypy
  - repo: https://github.com/pre-commit/pre-commit-hooks
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
```

### CI Required Checks
- [ ] Backend unit tests pass
- [ ] Backend integration tests pass
- [ ] Backend type check (mypy) passes
- [ ] Backend lint (ruff) passes
- [ ] Frontend unit tests pass
- [ ] Frontend type check (tsc) passes
- [ ] Frontend lint (eslint) passes
- [ ] E2E tests pass
- [ ] Contract tests pass
- [ ] Coverage thresholds met

---

## Debugging Failed Tests

### Common Issues

**Flaky E2E Tests**:
- Add explicit waits: `await expect(locator).toBeVisible()`
- Use `test.retry(2)` for known flaky tests
- Isolate test data with unique identifiers

**Integration Test Failures**:
- Ensure Testcontainers started before tests
- Check port conflicts (use random ports)
- Clean up between tests

**Mock Mismatches**:
- Update MSW handlers when API changes
- Verify request/response shapes match OpenAPI spec

---

## Test Reporting

### Coverage Reports
- Backend: `htmlcov/index.html` (pytest-cov)
- Frontend: `coverage/index.html` (vitest)
- Combined: Codecov dashboard

### Test Reports
- JUnit XML for CI: `pytest --junitxml=report.xml`
- Playwright HTML: `npx playwright show-report`

---

*Last updated: 2026-09-26*
