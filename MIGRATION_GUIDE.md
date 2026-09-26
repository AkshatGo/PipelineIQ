# Migration Guide

## Overview

This guide covers migrating from the original `hacktofuture4-D02` repository to the new recreated PipelineIQ project with improvements.

---

## Migration Strategy: Blue-Green with Feature Flags

```
Phase 1: Parallel Run (2 weeks)
├── Deploy new version to staging
├── Mirror production traffic (shadow mode)
├── Validate data consistency
└── Load test

Phase 2: Canary (1 week)
├── Route 5% traffic to new version
├── Monitor error rates, latency
├── Gradually increase to 50%

Phase 3: Full Cutover (1 day)
├── Switch DNS / traffic 100%
├── Monitor for 4 hours
├── Rollback if issues

Phase 4: Decommission (1 week)
├── Keep old version for rollback
├── Archive old repository
└── Update documentation
```

---

## Data Migration

### 1. Pre-Migration Checklist
- [ ] Backup MongoDB Atlas (point-in-time snapshot)
- [ ] Export all collections to JSON
- [ ] Verify record counts
- [ ] Document any schema differences

### 2. Schema Changes Mapping

| Original Field | New Field | Transformation |
|----------------|-----------|----------------|
| `User.github_token` | `User.github_access_token` | Rename |
| `Workspace.auto_fix_threshold` | `Workspace.risk_profile.auto_fix_below` | Move to embedded |
| `Workspace.approval_threshold` | `Workspace.risk_profile.require_approval_above` | Move to embedded |
| `PipelineRun.monitor_report` | `PipelineRun.monitor_report_json` | Rename, ensure dict |
| `PipelineRun.diagnosis_report` | `PipelineRun.diagnosis_report_json` | Rename, ensure dict |
| `PipelineRun.risk_report` | `PipelineRun.risk_report_json` | Rename, ensure dict |
| `AutoFixExecution.report` | `AutoFixExecution.report_json` | Rename |
| `AutoFixExecution.proposed_fix` | `AutoFixExecution.proposed_fix_json` | Rename |
| N/A | `Repository` collection | New - populate from workspace |
| N/A | `AutoFixFeedback` collection | New - empty initially |
| N/A | `AutoFixMemory` collection | New - empty initially |

### 3. Migration Script
```python
# scripts/migrate_from_original.py
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from datetime import datetime, timezone

async def migrate():
    # Connect to original DB
    orig_client = AsyncIOMotorClient(ORIG_MONGODB_URI)
    orig_db = orig_client[ORIG_DB_NAME]
    
    # Connect to new DB
    new_client = AsyncIOMotorClient(NEW_MONGODB_URI)
    await init_beanie(database=new_client[NEW_DB_NAME], document_models=[...])
    
    # Migrate Users
    async for user in orig_db.users.find():
        new_user = User(
            github_id=user["github_id"],
            username=user["username"],
            display_name=user.get("display_name"),
            email=user.get("email"),
            avatar_url=user.get("avatar_url"),
            github_access_token=user.get("github_token") or user.get("github_access_token"),
            organizations=user.get("organizations", []),
            last_login=user.get("last_login", datetime.now(timezone.utc)),
            created_at=user.get("created_at", datetime.now(timezone.utc)),
            is_active=user.get("is_active", True),
        )
        await new_user.insert()
    
    # Migrate Workspaces
    async for ws in orig_db.workspaces.find():
        new_ws = Workspace(
            name=ws["name"],
            description=ws.get("description"),
            owner_id=ws["owner_id"],
            github_installation_id=ws.get("github_installation_id"),
            github_repository_id=ws.get("github_repository_id"),
            github_repo_full_name=ws.get("github_repo_full_name"),
            github_default_branch=ws.get("github_default_branch"),
            github_repo_private=ws.get("github_repo_private"),
            github_repo_html_url=ws.get("github_repo_html_url"),
            github_account_login=ws.get("github_account_login"),
            github_account_type=ws.get("github_account_type"),
            slack_devops_mention=ws.get("slack_devops_mention"),
            risk_profile=RiskProfile(
                production_branch=ws.get("production_branch", "main"),
                require_approval_above=ws.get("approval_threshold", 60),
                auto_fix_below=ws.get("auto_fix_threshold", 30),
            ),
            connected_at=ws.get("connected_at"),
            last_webhook_event_at=ws.get("last_webhook_event_at"),
            created_at=ws.get("created_at", datetime.now(timezone.utc)),
            updated_at=ws.get("updated_at", datetime.now(timezone.utc)),
        )
        await new_ws.insert()
        
        # Create Repository record if connected
        if ws.get("github_repository_id"):
            repo = Repository(
                github_repo_id=ws["github_repository_id"],
                full_name=ws["github_repo_full_name"],
                name=ws["github_repo_full_name"].split("/")[-1],
                private=ws.get("github_repo_private", False),
                html_url=ws.get("github_repo_html_url"),
                default_branch=ws.get("github_default_branch", "main"),
                workspace_id=new_ws.id,
                connected_at=ws.get("connected_at", datetime.now(timezone.utc)),
                connected_by=ws["owner_id"],
            )
            await repo.insert()
    
    # Migrate PipelineRuns, WebhookEvents, AutoFixExecutions...
    # (Similar pattern - map fields, handle renames)
    
    print("Migration complete!")

if __name__ == "__main__":
    asyncio.run(migrate())
```

### 4. Verification Queries
```javascript
// Run in both old and new databases
db.users.countDocuments()
db.workspaces.countDocuments()
db.pipeline_runs.countDocuments()
db.autofix_executions.countDocuments()
db.webhook_events.countDocuments()

// Spot check
db.workspaces.findOne({name: "Production Pipeline"})
db.pipeline_runs.findOne({run_id: 12345})
```

---

## Configuration Migration

### Environment Variables Mapping
All variables map 1:1. New variables added:

| New Variable | Default | Description |
|--------------|---------|-------------|
| `ENCRYPTION_KEY` | Required | Fernet key for field encryption |
| `RATE_LIMIT_ENABLED` | `true` | Enable rate limiting |
| `CORS_ALLOWED_ORIGINS` | `FRONTEND_URL` | Additional allowed origins |
| `LOG_LEVEL` | `INFO` | Structured log level |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Optional | OpenTelemetry collector |

### Secret Rotation (Required)
Generate new values for:
- `JWT_SECRET` (64+ chars)
- `GITHUB_APP_WEBHOOK_SECRET` (32+ chars)
- `ENCRYPTION_KEY` (Fernet: `Fernet.generate_key()`)

---

## Frontend Migration

### No Data Migration Needed
Frontend is stateless - all state in backend or browser storage.

### Deployment
1. Deploy new frontend to Vercel preview
2. Test against new backend staging
3. Update Vercel rewrites to new backend
4. Promote to production

---

## GitHub App Reconfiguration

### Critical: Update URLs
| Setting | Old Value | New Value |
|---------|-----------|-----------|
| Homepage URL | `http://localhost:5173` | `https://app.yourdomain.com` |
| Webhook URL | `https://tunnel.ngrok.io/api/github/webhooks` | `https://app.yourdomain.com/api/github/webhooks` |
| Setup URL | `http://localhost:8000/api/github/installations/callback` | `https://app.yourdomain.com/api/github/installations/callback` |

### Private Key
- Generate new private key in GitHub App settings
- Update `GITHUB_APP_PRIVATE_KEY` in new backend
- Old key automatically revoked

---

## Rollback Procedure

### If Issues During Canary
```bash
# Vercel: Instant rollback
vercel rollback [deployment-url]

# Render: Re-deploy previous
# Dashboard -> Deployments -> Rollback

# DNS: Switch back (if using custom domains)
# Update CNAME to old backend
```

### If Issues After Full Cutover
1. **Immediate**: Route traffic back via Vercel rewrites / DNS
2. **Database**: Restore from pre-migration snapshot
3. **Secrets**: Old secrets still valid (not rotated yet)
4. **Investigate**: Use correlation IDs from logs

---

## Post-Migration Validation

### Automated Checks
```bash
# scripts/post_migration_validate.py
async def validate():
    checks = [
        ("Users migrated", lambda: User.count() == ORIG_USER_COUNT),
        ("Workspaces migrated", lambda: Workspace.count() == ORIG_WS_COUNT),
        ("Pipeline runs migrated", lambda: PipelineRun.count() == ORIG_PR_COUNT),
        ("Auto-fix executions migrated", lambda: AutoFixExecution.count() == ORIG_AF_COUNT),
        ("Webhook events (30d) migrated", lambda: WebhookEvent.count() == ORIG_WE_COUNT),
        ("Risk profiles valid", lambda: all(ws.risk_profile.auto_fix_below <= ws.risk_profile.require_approval_above for ws in await Workspace.all())),
        ("Repositories created", lambda: Repository.count() >= Workspace.count()),
    ]
    
    for name, check in checks:
        result = await check()
        status = "✅" if result else "❌"
        print(f"{status} {name}")
```

### Manual Smoke Test
1. Login with existing GitHub account
2. Verify workspaces visible
3. Verify GitHub App still connected
4. Trigger test workflow failure
5. Verify end-to-end pipeline
6. Test auto-fix report/feedback links

---

## Timeline

| Week | Activity |
|------|----------|
| 1 | Set up new repos, CI/CD, staging env |
| 2 | Implement core backend with tests |
| 3 | Implement auto-fix engine |
| 4 | Implement frontend |
| 5 | Observability, hardening |
| 6 | Data migration script development |
| 7 | Staging deployment, shadow traffic |
| 8 | Canary release |
| 9 | Full cutover |
| 10 | Decommission old |

---

## Communication Plan

### Internal
- Weekly sync during development
- Daily standups during migration week
- Incident channel for cutover day

### External (If applicable)
- Blog post: "PipelineIQ 2.0: Faster, Safer, Smarter"
- Changelog in GitHub releases
- Migration guide for self-hosters

---

*Last updated: 2026-09-26*
