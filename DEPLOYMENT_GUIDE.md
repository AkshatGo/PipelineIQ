# Deployment Guide

## Overview

This guide covers deploying PipelineIQ to production using the recommended architecture:
- **Frontend**: Vercel (React + Vite)
- **Backend**: Render (FastAPI + Docker)
- **Database**: MongoDB Atlas
- **Message Queue**: External Kafka (optional) or disabled
- **Secrets**: Platform secret managers

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Vercel    │────▶│   Render    │────▶│ MongoDB     │
│  (Frontend) │     │  (Backend)  │     │  Atlas      │
└─────────────┘     └─────────────┘     └─────────────┘
       ▲                   │
       │                   ▼
       │            ┌─────────────┐
       │            │   Kafka     │
       │            │  (Optional) │
       │            └─────────────┘
       │                   │
       ▼                   ▼
┌─────────────┐     ┌─────────────┐
│   GitHub    │     │   Slack     │
│  OAuth/App  │     │  Webhooks   │
└─────────────┘     └─────────────┘
```

### Key Principle
**All browser traffic goes to Vercel domain.** Vercel rewrites `/api/*` to Render backend. This keeps cookies, OAuth redirects, and signed URLs on single origin.

---

## Prerequisites

### Accounts Required
- [ ] GitHub Organization (for OAuth App + GitHub App)
- [ ] MongoDB Atlas account
- [ ] Vercel account
- [ ] Render account
- [ ] Slack workspace (optional)
- [ ] LLM provider account (GitHub Models, Groq, or OpenAI-compatible)

### DNS (Optional but Recommended)
- `app.yourdomain.com` → Vercel (frontend)
- `api.yourdomain.com` → Render (backend, if not using Vercel rewrites)

---

## Step 1: MongoDB Atlas

### 1.1 Create Cluster
1. Go to https://cloud.mongodb.com
2. Create project: `pipelineiq`
3. Create cluster: `M0` (free) or `M10+` (production)
4. Provider: AWS/GCP/Azure, Region: closest to Render region

### 1.2 Database User
1. Database Access → Add New Database User
2. Authentication: Password
3. Username: `pipelineiq`
4. Password: Generate strong password (save securely)
5. Privileges: `readWrite` on `pipelineiq` database

### 1.3 Network Access
1. Network Access → Add IP Address
2. For Render: Add `0.0.0.0/0` (or use VPC peering for production)
3. For local dev: Add your IP

### 1.4 Connection String
1. Clusters → Connect → Drivers
2. Copy connection string
3. Replace `<username>`, `<password>`, database name with `pipelineiq`

```env
MONGODB_URI=mongodb+srv://pipelineiq:PASSWORD@cluster0.abcde.mongodb.net/pipelineiq?retryWrites=true&w=majority
MONGODB_DB_NAME=pipelineiq
```

---

## Step 2: GitHub OAuth App (User Login)

### 2.1 Create OAuth App
1. GitHub Settings → Developer settings → OAuth Apps → New OAuth App
2. Fill in:
   - **Application name**: `PipelineIQ`
   - **Homepage URL**: `https://app.yourdomain.com` (or Vercel URL)
   - **Authorization callback URL**: `https://app.yourdomain.com/api/auth/github/callback`
3. Save

### 2.2 Save Credentials
1. Copy **Client ID** → `GITHUB_CLIENT_ID`
2. Generate **Client Secret** → `GITHUB_CLIENT_SECRET`
3. Scopes: `read:user read:org` (already in code)

```env
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret
GITHUB_REDIRECT_URI=https://app.yourdomain.com/api/auth/github/callback
GITHUB_OAUTH_SCOPES=read:user read:org
```

---

## Step 3: GitHub App (Repository Integration)

### 3.1 Create GitHub App
1. GitHub Settings → Developer settings → GitHub Apps → New GitHub App
2. Fill in:
   - **App name**: `pipelineiq` (must be globally unique)
   - **Homepage URL**: `https://app.yourdomain.com`
   - **Webhook URL**: `https://app.yourdomain.com/api/github/webhooks`
   - **Webhook secret**: Generate random 32+ char string → `GITHUB_APP_WEBHOOK_SECRET`
   - **Setup URL**: `https://app.yourdomain.com/api/github/installations/callback`
   - **Redirect on update**: Enabled

### 3.2 Permissions
**Repository permissions**:
| Permission | Access |
|------------|--------|
| Actions | Read-only |
| Checks | Read & write |
| Contents | Read & write |
| Metadata | Read-only |
| Pull requests | Read & write |

**Organization permissions**: None required

**Subscribe to events**:
- [x] Workflow run
- [x] Workflow job
- [x] Push
- [x] Check run

### 3.3 Save Credentials
1. **App ID** → `GITHUB_APP_ID`
2. **App slug** (from URL) → `GITHUB_APP_SLUG`
3. Generate **Private key** → Download `.pem`, convert to single line:
   ```bash
   awk '{printf "%s\\n", $0}' private-key.pem
   ```
   → `GITHUB_APP_PRIVATE_KEY` (with escaped `\n`)
4. **Install URL**: `https://github.com/apps/{slug}/installations/new` → `GITHUB_APP_INSTALL_URL`

```env
GITHUB_APP_ID=1234567
GITHUB_APP_SLUG=pipelineiq
GITHUB_APP_INSTALL_URL=https://github.com/apps/pipelineiq/installations/new
GITHUB_APP_WEBHOOK_SECRET=your_webhook_secret
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

---

## Step 4: LLM Providers

Configure at least one provider per agent type.

### 4.1 GitHub Models (Recommended - Free)
```env
GITHUB_TOKEN=ghp_your_fine_grained_token
GITHUB_MODELS_API_BASE_URL=https://models.github.ai/inference
```

### 4.2 Groq (Fast)
```env
GROQ_API_KEY=gsk_your_key
GROQ_API_BASE_URL=https://api.groq.com/openai/v1
```

### 4.3 OpenAI-Compatible (Azure, Self-hosted, etc.)
```env
OPENAI_API_KEY=your_key
OPENAI_API_BASE_URL=https://your-endpoint.openai.azure.com/v1
```

### 4.4 Agent Configuration
```env
# Monitor Agent
MONITOR_AGENT_PRIMARY_PROVIDER=github_models
MONITOR_AGENT_PRIMARY_MODEL=openai/gpt-4o-mini
MONITOR_AGENT_FALLBACK_PROVIDER=groq
MONITOR_AGENT_FALLBACK_MODEL=llama-3.3-70b-versatile

# Diagnosis Agent
DIAGNOSIS_AGENT_PRIMARY_PROVIDER=groq
DIAGNOSIS_AGENT_PRIMARY_MODEL=openai/gpt-oss-120b
DIAGNOSIS_AGENT_FALLBACK_PROVIDER=github_models
DIAGNOSIS_AGENT_FALLBACK_MODEL=openai/gpt-4.1

# Risk Agent
RISK_AGENT_PRIMARY_PROVIDER=github_models
RISK_AGENT_PRIMARY_MODEL=gpt-4o-mini
RISK_AGENT_FALLBACK_PROVIDER=groq
RISK_AGENT_FALLBACK_MODEL=llama-3.3-70b-versatile

# Auto-fix Agent
AUTOFIX_AGENT_PRIMARY_PROVIDER=github_models
AUTOFIX_AGENT_PRIMARY_MODEL=gpt-4o-mini
AUTOFIX_AGENT_FALLBACK_PROVIDER=groq
AUTOFIX_AGENT_FALLBACK_MODEL=llama-3.3-70b-versatile

AUTOFIX_REPORT_EXPIRY_HOURS=168
AUTOFIX_FEEDBACK_EXPIRY_HOURS=720
```

---

## Step 5: Slack Notifications (Optional)

### 5.1 Create Slack App
1. https://api.slack.com/apps → Create New App → From scratch
2. Name: `PipelineIQ`, Workspace: your workspace
3. Features → Incoming Webhooks → On
4. Add New Webhook to Workspace → Select channel → Allow

### 5.2 Configure
```env
SLACK_ENABLED=true
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
SLACK_DEFAULT_CHANNEL=#devops-alerts
SLACK_DEVOPS_MENTION_DEFAULT=@channel
```

---

## Step 6: Backend Deployment (Render)

### 6.1 Create Render Web Service
1. Dashboard → New → Web Service
2. Connect GitHub repo
3. Settings:
   - **Name**: `pipelineiq-backend`
   - **Runtime**: Docker
   - **Root Directory**: `packages/backend` (or `pipelineIQ` in original)
   - **Dockerfile Path**: `Dockerfile`
   - **Health Check Path**: `/health`
   - **Instance Type**: Start with `Starter` (512MB RAM)

### 6.2 Environment Variables (Render Dashboard)
Add all variables from `.env.example` plus:

```env
# Core
MONGODB_URI=mongodb+srv://...
MONGODB_DB_NAME=pipelineiq

JWT_SECRET=your_64_char_random_secret
JWT_ALGORITHM=HS256
SESSION_EXPIRY_DAYS=15

FRONTEND_URL=https://app.yourdomain.com
COOKIE_SECURE=true
COOKIE_DOMAIN=

RESET_CI_CD_STATE_ON_STARTUP=false

# GitHub OAuth (from Step 2)
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GITHUB_REDIRECT_URI=https://app.yourdomain.com/api/auth/github/callback
GITHUB_OAUTH_SCOPES=read:user read:org

# GitHub App (from Step 3)
GITHUB_APP_ID=...
GITHUB_APP_SLUG=...
GITHUB_APP_INSTALL_URL=...
GITHUB_APP_WEBHOOK_SECRET=...
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"

# LLM (from Step 4)
# ... all provider keys and agent configs

# Slack (from Step 5)
SLACK_ENABLED=true
SLACK_WEBHOOK_URL=...
SLACK_DEFAULT_CHANNEL=#devops-alerts
SLACK_DEVOPS_MENTION_DEFAULT=@channel

# Kafka - DISABLE for first deployment
KAFKA_ENABLED=false
```

### 6.3 Deploy
1. Click **Create Web Service**
2. Wait for build + deploy (5-10 min)
3. Verify health: `https://pipelineiq-backend.onrender.com/health`

### 6.4 Custom Domain (Optional)
1. Settings → Custom Domains → Add `api.yourdomain.com`
2. Configure DNS CNAME to Render URL

---

## Step 7: Frontend Deployment (Vercel)

### 7.1 Create Vercel Project
1. Vercel Dashboard → Add New → Project
2. Import GitHub repo
3. Settings:
   - **Framework Preset**: Vite
   - **Root Directory**: `packages/frontend` (or `pipelineIQ-frontend`)
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### 7.2 Environment Variables (Vercel Dashboard)
```env
# No backend env vars needed in frontend - all API calls proxied
```

### 7.3 Vercel Rewrites (Critical!)
1. Project Settings → Rewrites → Add:
   ```
   Source: /api/(.*)
   Destination: https://pipelineiq-backend.onrender.com/api/$1
   ```
2. Add legacy webhook route:
   ```
   Source: /webhook/github
   Destination: https://pipelineiq-backend.onrender.com/webhook/github
   ```

### 7.4 Deploy
1. Click **Deploy**
2. Wait for build (2-3 min)
3. Verify: `https://app.yourdomain.com` loads

### 7.5 Custom Domain
1. Settings → Domains → Add `app.yourdomain.com`
2. Configure DNS per Vercel instructions

---

## Step 8: Update GitHub Apps with Production URLs

### 8.1 OAuth App
- Homepage URL: `https://app.yourdomain.com`
- Callback URL: `https://app.yourdomain.com/api/auth/github/callback`

### 8.2 GitHub App
- Homepage URL: `https://app.yourdomain.com`
- Webhook URL: `https://app.yourdomain.com/api/github/webhooks`
- Setup URL: `https://app.yourdomain.com/api/github/installations/callback`

---

## Step 9: Enable Kafka (Optional, After Validation)

### 9.1 Provision Kafka
Options:
- **Managed**: Confluent Cloud, Redpanda Cloud, Upstash
- **Self-hosted**: EC2/VM with Docker Compose (see `docker-compose.prod.yml`)

### 9.2 Create Topics
```bash
# pipeline-events (3 partitions)
# diagnosis-required (3 partitions)
```

### 9.3 Update Backend Env (Render)
```env
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=your-kafka-host:9092
KAFKA_PIPELINE_EVENTS_TOPIC=pipeline-events
KAFKA_DIAGNOSIS_REQUIRED_TOPIC=diagnosis-required
KAFKA_MONITOR_GROUP_ID=pipelineiq-monitor-agent
KAFKA_DIAGNOSIS_GROUP_ID=pipelineiq-diagnosis-agent
```

### 9.4 Redeploy Backend
Render will auto-redeploy on env change.

---

## Step 10: Post-Deploy Smoke Test

Run in order:

1. **Frontend loads**: `https://app.yourdomain.com`
2. **GitHub Login**: Click "Continue with GitHub" → lands on `/dashboard`
3. **Create Workspace**: Fill form, submit
4. **Install GitHub App**: From workspace, click connect → GitHub → select repo
5. **Verify Callback**: Returns to workspace page with success
6. **Trigger Failure**: Push failing workflow to connected repo
7. **Check Webhook**: Backend logs show 202 response
8. **Check PipelineRun**: MongoDB has new document
9. **Check Diagnosis**: Diagnosis tab populates
10. **Check Risk Score**: Risk tab shows score + breakdown
11. **Check Auto-fix**: PR created if policy allows
12. **Check Slack**: Notification in configured channel
13. **Test Report Link**: Open signed URL from Slack → loads on Vercel domain

---

## Environment Variable Reference

### Required for All Environments
| Variable | Description | Example |
|----------|-------------|---------|
| `MONGODB_URI` | MongoDB connection string | `mongodb+srv://...` |
| `MONGODB_DB_NAME` | Database name | `pipelineiq` |
| `JWT_SECRET` | 64+ char random string | `openssl rand -base64 48` |
| `FRONTEND_URL` | Public Vercel URL | `https://app.yourdomain.com` |
| `GITHUB_CLIENT_ID` | OAuth App Client ID | `Iv1.xxx` |
| `GITHUB_CLIENT_SECRET` | OAuth App Secret | `xxx` |
| `GITHUB_REDIRECT_URI` | OAuth callback | `https://app.yourdomain.com/api/auth/github/callback` |
| `GITHUB_APP_ID` | GitHub App ID | `1234567` |
| `GITHUB_APP_SLUG` | GitHub App slug | `pipelineiq` |
| `GITHUB_APP_PRIVATE_KEY` | PEM with escaped newlines | `"-----BEGIN...\n...\n-----END..."` |
| `GITHUB_APP_WEBHOOK_SECRET` | Webhook HMAC secret | `xxx` |

### Required for LLM (At Least One Provider)
| Variable | Description |
|----------|-------------|
| `GITHUB_TOKEN` | GitHub Models PAT |
| `GROQ_API_KEY` | Groq API key |
| `OPENAI_API_KEY` | OpenAI-compatible key |

### Optional
| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_ENABLED` | `false` | Enable Kafka |
| `SLACK_ENABLED` | `false` | Enable Slack |
| `COOKIE_SECURE` | `true` (prod) | Secure cookies |
| `COOKIE_DOMAIN` | `` | Cookie domain |
| `SESSION_EXPIRY_DAYS` | `15` | Session lifetime |

---

## Rollback Procedure

### Backend (Render)
1. Render Dashboard → Deployments
2. Click **Rollback** on previous successful deployment
3. Or: Re-deploy specific commit: `git push render <commit-hash>:main --force`

### Frontend (Vercel)
1. Vercel Dashboard → Deployments
2. Click **...** on previous deployment → **Promote to Production**

### Database
- MongoDB Atlas: Point-in-time recovery (paid tiers)
- Always backup before migrations

---

## Monitoring & Alerts

### Health Checks
- Backend: `GET /health` (Render built-in)
- Frontend: Vercel automatic
- Database: MongoDB Atlas alerts
- Kafka: Consumer lag alerts

### Key Metrics to Alert On
| Metric | Warning | Critical |
|--------|---------|----------|
| Webhook processing latency (p95) | > 5s | > 15s |
| Auto-fix success rate | < 80% | < 50% |
| LLM API error rate | > 5% | > 20% |
| Kafka consumer lag | > 100 | > 1000 |
| MongoDB connection errors | > 1/min | > 10/min |

---

## Security Checklist

- [ ] `COOKIE_SECURE=true` in production
- [ ] `JWT_SECRET` is 64+ chars, rotated periodically
- [ ] GitHub App private key stored only in Render secrets
- [ ] MongoDB Atlas: IP whitelist (not 0.0.0.0/0)
- [ ] Render: Private networking if VPC available
- [ ] Slack webhook URL treated as secret
- [ ] LLM API keys in platform secrets, not repo
- [ ] Dependabot/security scanning enabled
- [ ] CSP headers configured (Vercel auto)

---

## Cost Optimization

| Component | Free Tier | Paid Estimate (Monthly) |
|-----------|-----------|-------------------------|
| Vercel (Frontend) | ✅ Generous | $20 (Pro) |
| Render (Backend) | ✅ 750 hrs | $7-25 (Starter/Standard) |
| MongoDB Atlas | ✅ M0 (512MB) | $57 (M10) |
| Kafka | ❌ | $15-100+ (managed) |
| GitHub Models | ✅ Free | N/A |
| Groq | ✅ Free tier | $0-50 |
| Slack | ✅ Free | $0 |

**Start with all free tiers**, enable paid only when needed.

---

## Troubleshooting

### "Invalid webhook signature"
- Verify `GITHUB_APP_WEBHOOK_SECRET` matches exactly in GitHub App settings and Render env
- Check no extra whitespace in env var

### "Cookie not set / CORS error"
- Verify `FRONTEND_URL` matches Vercel domain exactly
- Check Vercel rewrites for `/api/*` are configured
- Ensure `COOKIE_SECURE=true` and `COOKIE_DOMAIN=` empty

### "GitHub App installation fails"
- Verify Setup URL matches Vercel domain + `/api/github/installations/callback`
- Check GitHub App permissions include required repo permissions
- Verify private key format (escaped newlines)

### "LLM calls failing"
- Check API keys valid and have quota
- Verify model names match provider (e.g., `gpt-4o-mini` not `gpt-4`)
- Check fallback chain in logs

### "Pipeline runs stuck in pending"
- Check Kafka consumer logs (if enabled)
- Verify `pipeline_runtime` service started in backend logs
- Check MongoDB for error fields

---

*Update this guide as infrastructure evolves. Last reviewed: 2026-09-26*
