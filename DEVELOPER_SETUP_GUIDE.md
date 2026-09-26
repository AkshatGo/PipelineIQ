# Developer Setup Guide

## Prerequisites

### Required Tools
| Tool | Version | Install Command |
|------|---------|-----------------|
| Python | 3.11+ | `brew install python@3.11` / `apt install python3.11` |
| Node.js | 20+ | `fnm install 20` / `nvm install 20` |
| Docker | 24+ | `brew install docker` / `apt install docker.io` |
| Git | 2.40+ | `brew install git` / `apt install git` |
| Make | 4.4+ | `brew install make` / `apt install make` |

### Optional but Recommended
| Tool | Purpose |
|------|---------|
| VS Code | IDE with extensions |
| ngrok/cloudflared | Local webhook tunneling |
| MongoDB Compass | Database GUI |
| Kafka UI | Kafka topic inspection |
| Postman/Insomnia | API testing |

---

## Quick Start (5 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/your-org/pipelineiq.git
cd pipelineiq

# 2. Copy environment template
cp .env.example .env.local

# 3. Start infrastructure (MongoDB + Kafka)
docker compose -f docker-compose.dev.yml up -d

# 4. Install backend dependencies
cd packages/backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 5. Install frontend dependencies
cd ../frontend
npm install

# 6. Start development servers (in separate terminals)
# Terminal 1 - Backend
cd packages/backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd packages/frontend
npm run dev
```

**Access**: Frontend at `http://localhost:5173`, Backend at `http://localhost:8000`

---

## Detailed Setup

### 1. GitHub OAuth App (User Authentication)

1. Go to GitHub Settings → Developer settings → OAuth Apps → New OAuth App
2. Fill in:
   - **Application name**: `PipelineIQ Local`
   - **Homepage URL**: `http://localhost:5173`
   - **Authorization callback URL**: `http://localhost:8000/api/auth/github/callback`
3. Save and copy **Client ID** and **Client Secret**
4. Update `.env.local`:
   ```env
   GITHUB_CLIENT_ID=your_client_id
   GITHUB_CLIENT_SECRET=your_client_secret
   GITHUB_REDIRECT_URI=http://localhost:8000/api/auth/github/callback
   ```

### 2. GitHub App (Repository Integration)

1. Go to GitHub Settings → Developer settings → GitHub Apps → New GitHub App
2. Fill in:
   - **App name**: `pipelineiq-local` (must be unique)
   - **Homepage URL**: `http://localhost:5173`
   - **Webhook URL**: `https://your-ngrok-url.ngrok-free.app/api/github/webhooks`
   - **Webhook secret**: Generate random string, save to `GITHUB_APP_WEBHOOK_SECRET`
   - **Setup URL**: `http://localhost:8000/api/github/installations/callback`
3. **Repository permissions**:
   - Actions: Read-only
   - Contents: Read & write
   - Pull requests: Read & write
   - Metadata: Read-only
4. **Subscribe to events**:
   - Workflow run
   - Workflow job
   - Push
   - Check run
5. Create the app, then:
   - Copy **App ID** → `GITHUB_APP_ID`
   - Copy **App slug** (from URL) → `GITHUB_APP_SLUG`
   - Generate **Private key** → Save as `GITHUB_APP_PRIVATE_KEY` (escape newlines as `\n`)
   - Build install URL: `https://github.com/apps/{slug}/installations/new` → `GITHUB_APP_INSTALL_URL`

### 3. LLM Provider Setup (At least one required)

#### Option A: GitHub Models (Recommended - Free)
1. Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Create token with **Models: Read** permission
3. Update `.env.local`:
   ```env
   GITHUB_TOKEN=ghp_your_token
   GITHUB_MODELS_API_BASE_URL=https://models.github.ai/inference
   ```

#### Option B: Groq (Fast, Free Tier)
1. Sign up at https://console.groq.com
2. Create API key
3. Update `.env.local`:
   ```env
   GROQ_API_KEY=gsk_your_key
   GROQ_API_BASE_URL=https://api.groq.com/openai/v1
   ```

#### Option C: OpenAI-Compatible (Self-hosted, Azure, etc.)
```env
OPENAI_API_KEY=your_key
OPENAI_API_BASE_URL=https://your-endpoint.com/v1
```

### 4. Slack Notifications (Optional)

1. Create Slack App at https://api.slack.com/apps
2. Enable **Incoming Webhooks**
3. Add webhook to workspace, select channel
4. Copy webhook URL → `SLACK_WEBHOOK_URL`
5. Update `.env.local`:
   ```env
   SLACK_ENABLED=true
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
   SLACK_DEFAULT_CHANNEL=#devops-alerts
   SLACK_DEVOPS_MENTION_DEFAULT=@channel
   ```

### 5. MongoDB Setup

#### Local (Docker)
```bash
docker run -d \
  --name pipelineiq-mongo \
  -p 27017:27017 \
  -e MONGO_INITDB_DATABASE=pipelineiq \
  mongo:7
```
```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=pipelineiq
```

#### MongoDB Atlas (Cloud)
1. Create cluster at https://cloud.mongodb.com
2. Create database user
3. Allow network access (0.0.0.0/0 for dev)
4. Get connection string
5. Update `.env.local`:
   ```env
   MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/pipelineiq?retryWrites=true&w=majority
   MONGODB_DB_NAME=pipelineiq
   ```

### 6. Kafka Setup (Optional - for full event-driven flow)

```bash
# Using provided docker-compose.dev.yml
docker compose -f docker-compose.dev.yml up -d kafka

# Or manually:
docker run -d --name pipelineiq-kafka \
  -p 9092:9092 \
  -e KAFKA_NODE_ID=1 \
  -e KAFKA_PROCESS_ROLES=broker,controller \
  -e KAFKA_LISTENERS=PLAINTEXT://:9092,CONTROLLER://:9093 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  -e KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER \
  -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT \
  -e KAFKA_CONTROLLER_QUORUM_VOTERS=1@localhost:9093 \
  apache/kafka:3.9.0

# Create topics
docker exec pipelineiq-kafka /opt/kafka/bin/kafka-topics.sh \
  --create --topic pipeline-events --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1

docker exec pipelineiq-kafka /opt/kafka/bin/kafka-topics.sh \
  --create --topic diagnosis-required --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
```
```env
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### 7. Local Webhook Tunneling (Required for GitHub App)

```bash
# Option 1: ngrok
ngrok http 8000

# Option 2: cloudflared (free, no account needed)
cloudflared tunnel --url http://localhost:8000
```
Copy the HTTPS URL and update GitHub App **Webhook URL** to:
`https://your-tunnel.ngrok-free.app/api/github/webhooks`

---

## Development Workflow

### Running Tests

```bash
# Backend tests
cd packages/backend
pytest                    # Unit tests
pytest -m integration     # Integration tests (requires Docker)
pytest --cov              # With coverage

# Frontend tests
cd packages/frontend
npm run test              # Unit tests (vitest)
npm run test:e2e          # E2E tests (Playwright)

# All tests
make test
```

### Code Quality

```bash
# Backend
cd packages/backend
ruff check .              # Lint
ruff format .             # Format
mypy .                    # Type check

# Frontend
cd packages/frontend
npm run lint              # ESLint
npm run format            # Prettier
npm run typecheck         # tsc --noEmit
```

### Database Operations

```bash
# Reset database (careful!)
cd packages/backend
python scripts/reset_db.py

# Seed test data
python scripts/seed.py

# Run migrations (if using)
python -m beanie migrate
```

### Git Workflow

```bash
# Create feature branch
git checkout develop
git pull
git checkout -b feature/your-feature-name

# Make changes, commit with conventional commits
git add .
git commit -m "feat: add new risk scoring factor"

# Push and create PR
git push origin feature/your-feature-name
# Create PR via GitHub UI targeting 'develop'
```

### Pre-commit Hooks (Auto-installed)

```bash
# Install once
cd packages/backend && pre-commit install
cd packages/frontend && npx husky install

# Run manually
pre-commit run --all-files
```

---

## Project Structure (Monorepo)

```
pipelineiq/
├── .github/workflows/        # CI/CD pipelines
├── docker-compose.dev.yml    # Local infrastructure
├── docker-compose.prod.yml   # Production-like stack
├── Makefile                  # Common commands
├── turbo.json                # Turborepo config
├── package.json              # Root package.json
├── .env.example              # Environment template
├── packages/
│   ├── backend/              # FastAPI application
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── auth/
│   │   │   ├── models/
│   │   │   ├── routers/
│   │   │   └── services/
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── frontend/             # React + Vite application
│   │   ├── src/
│   │   │   ├── api/
│   │   │   ├── components/
│   │   │   ├── context/
│   │   │   ├── pages/
│   │   │   ├── hooks/
│   │   │   └── types/
│   │   ├── tests/
│   │   ├── package.json
│   │   ├── vite.config.ts
│   │   └── Dockerfile
│   └── shared/               # Shared types, constants
│       ├── python/
│       │   └── pipelineiq_shared/
│       └── typescript/
│           └── pipelineiq-shared/
└── docs/                     # Documentation site (Docusaurus)
```

---

## Common Issues & Solutions

### Issue: "MongoDB connection refused"
```bash
# Check if MongoDB is running
docker ps | grep mongo

# Check logs
docker logs pipelineiq-mongo

# Verify connection string in .env.local
```

### Issue: "GitHub webhook not received"
1. Verify ngrok/cloudflared is running
2. Check GitHub App webhook URL matches tunnel URL + `/api/github/webhooks`
3. Check backend logs for signature verification errors
4. Verify `GITHUB_APP_WEBHOOK_SECRET` matches GitHub App settings

### Issue: "CORS error in frontend"
```bash
# Check FRONTEND_URL in backend .env.local matches frontend URL
# Check CORS middleware in backend/main.py allows FRONTEND_URL
```

### Issue: "LLM provider rate limited"
- Check provider dashboard for quota
- Verify fallback providers configured
- Check `llm_gateway.py` for proper fallback logic

### Issue: "Kafka consumer not processing"
```bash
# Check consumer group lag
docker exec pipelineiq-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group pipelineiq-monitor-agent \
  --describe

# Reset consumer group (careful!)
docker exec pipelineiq-kafka /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --group pipelineiq-monitor-agent \
  --reset-offsets --to-earliest --all-topics --execute
```

---

## Useful Commands

```bash
# Start all dev infrastructure
make dev-up

# Stop all dev infrastructure
make dev-down

# View backend logs
make logs-backend

# View frontend logs
make logs-frontend

# Run full test suite
make test

# Build all packages
make build

# Clean build artifacts
make clean

# Generate OpenAPI spec
cd packages/backend && python -m src.generate_openapi
```

---

## IDE Configuration (VS Code)

### Recommended Extensions
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "ms-python.mypy-type-checker",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "ms-vscode.vscode-typescript-next",
    "github.vscode-github-actions",
    "ms-azuretools.vscode-docker"
  ]
}
```

### Settings (`.vscode/settings.json`)
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/packages/backend/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": "explicit",
    "source.fixAll.ruff": "explicit"
  },
  "typescript.tsdk": "${workspaceFolder}/packages/frontend/node_modules/typescript/lib",
  "eslint.enable": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode"
}
```

---

## Next Steps

1. Read [Architecture Decisions](./ARCHITECTURE_DECISIONS.md)
2. Review [API Specification](./API_SPEC.md)
3. Understand [Data Models](./DATA_MODELS.md)
4. Start with [Phase 1 Implementation](./IMPLEMENTATION_PHASES.md)
5. Join team sync for task assignment
