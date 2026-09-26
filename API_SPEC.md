# API Specification (OpenAPI 3.1)

## Overview

This document defines the complete API contract for PipelineIQ. All endpoints are prefixed with `/api` unless otherwise noted.

**Base URL**: `http://localhost:8000` (development) / `https://api.pipelineiq.io` (production)

**Authentication**: HttpOnly cookie (`piq_session`) with JWT

**Content-Type**: `application/json`

---

## Error Response Format

All error responses follow this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": {},
    "request_id": "uuid-v4",
    "timestamp": "2026-09-26T12:00:00Z"
  }
}
```

### HTTP Status Codes
| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async processing) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid/expired session) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 409 | Conflict (duplicate resource) |
| 422 | Unprocessable Entity (semantic error) |
| 429 | Too Many Requests (rate limited) |
| 500 | Internal Server Error |
| 503 | Service Unavailable (dependency down) |

---

## Authentication Endpoints

### GET /api/auth/github
Initiate GitHub OAuth 2.0 flow.

**Response**: `302 Redirect` to GitHub authorization page

**Query Parameters** (handled server-side):
- `client_id`: GitHub OAuth App Client ID
- `redirect_uri`: Configured callback URL
- `scope`: `read:user read:org`
- `state`: CSRF protection token

---

### GET /api/auth/github/callback
Handle GitHub OAuth callback.

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `code` | string | Yes | Authorization code from GitHub |
| `state` | string | No | CSRF state parameter |

**Response**: `302 Redirect` to `/dashboard` with `piq_session` cookie set

**Error Redirect**: `302 Redirect` to `/?error=oauth_failed`

---

### GET /api/auth/me
Get current authenticated user.

**Headers**: `Cookie: piq_session=<jwt>`

**Response** (200):
```json
{
  "id": "user_object_id",
  "github_id": 12345678,
  "username": "octocat",
  "display_name": "The Octocat",
  "email": "octocat@github.com",
  "avatar_url": "https://avatars.githubusercontent.com/u/583231",
  "organizations": [
    {
      "id": 12345,
      "login": "github",
      "avatar_url": "https://avatars.githubusercontent.com/u/12345",
      "description": "GitHub organization",
      "url": "https://api.github.com/orgs/github"
    }
  ],
  "last_login": "2026-09-26T12:00:00Z",
  "created_at": "2026-01-15T10:00:00Z"
}
```

**Errors**: 401 (Not authenticated), 401 (Invalid/expired session)

---

### POST /api/auth/logout
Clear session cookie.

**Headers**: `Cookie: piq_session=<jwt>`

**Response** (200):
```json
{ "detail": "Logged out" }
```

---

## Workspace Endpoints

### GET /api/workspaces
List all workspaces owned by the authenticated user.

**Headers**: `Cookie: piq_session=<jwt>`

**Response** (200):
```json
[
  {
    "id": "workspace_object_id",
    "name": "My Project",
    "description": "Main production workspace",
    "owner_id": "user_object_id",
    "github_installation_id": 987654321,
    "github_repository_id": 123456789,
    "github_repo_full_name": "org/repo",
    "github_default_branch": "main",
    "github_repo_private": true,
    "github_repo_html_url": "https://github.com/org/repo",
    "github_account_login": "org",
    "github_account_type": "Organization",
    "slack_devops_mention": "@devops-oncall",
    "risk_profile": {
      "production_branch": "main",
      "require_approval_above": 60,
      "auto_fix_below": 30
    },
    "connected_at": "2026-09-01T10:00:00Z",
    "last_webhook_event_at": "2026-09-26T08:30:00Z",
    "created_at": "2026-09-01T10:00:00Z",
    "updated_at": "2026-09-26T08:30:00Z",
    "connected": true
  }
]
```

---

### POST /api/workspaces
Create a new workspace.

**Headers**: `Cookie: piq_session=<jwt>`, `Content-Type: application/json`

**Request Body**:
```json
{
  "name": "My Project",
  "description": "Main production workspace",
  "risk_profile": {
    "production_branch": "main",
    "require_approval_above": 60,
    "auto_fix_below": 30
  }
}
```

**Validation**:
- `name`: Required, 1-100 chars
- `description`: Optional, max 500 chars
- `risk_profile.production_branch`: Required, 1-50 chars
- `risk_profile.require_approval_above`: Integer 0-100
- `risk_profile.auto_fix_below`: Integer 0-100
- Must satisfy: `auto_fix_below <= require_approval_above`

**Response** (201):
```json
{
  "id": "new_workspace_object_id",
  "name": "My Project",
  "description": "Main production workspace",
  "owner_id": "user_object_id",
  "github_installation_id": null,
  "github_repository_id": null,
  "github_repo_full_name": null,
  "github_default_branch": null,
  "github_repo_private": null,
  "github_repo_html_url": null,
  "github_account_login": null,
  "github_account_type": null,
  "slack_devops_mention": null,
  "risk_profile": {
    "production_branch": "main",
    "require_approval_above": 60,
    "auto_fix_below": 30
  },
  "connected_at": null,
  "last_webhook_event_at": null,
  "created_at": "2026-09-26T12:00:00Z",
  "updated_at": "2026-09-26T12:00:00Z"
}
```

---

### GET /api/workspaces/{workspace_id}
Get workspace details.

**Headers**: `Cookie: piq_session=<jwt>`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `workspace_id` | string | Workspace ObjectId |

**Response** (200): Same as array item in GET /api/workspaces

**Errors**: 404 (Workspace not found or not owned by user)

---

### PATCH /api/workspaces/{workspace_id}
Update workspace.

**Headers**: `Cookie: piq_session=<jwt>`, `Content-Type: application/json`

**Path Parameters**: `workspace_id` (string)

**Request Body** (all optional):
```json
{
  "name": "Updated Name",
  "description": "Updated description",
  "risk_profile": {
    "production_branch": "main",
    "require_approval_above": 65,
    "auto_fix_below": 25
  },
  "slack_devops_mention": "@new-mention"
}
```

**Response** (200): Updated workspace object

**Errors**: 404, 422 (validation error)

---

### DELETE /api/workspaces/{workspace_id}
Delete workspace and all associated data.

**Headers**: `Cookie: piq_session=<jwt>`

**Path Parameters**: `workspace_id` (string)

**Response** (200):
```json
{ "detail": "Workspace deleted" }
```

**Errors**: 404

---

### GET /api/workspaces/{workspace_id}/repositories
List repositories connected to workspace.

**Headers**: `Cookie: piq_session=<jwt>`

**Path Parameters**: `workspace_id` (string)

**Response** (200):
```json
[
  {
    "id": "repo_object_id",
    "github_repo_id": 123456789,
    "full_name": "org/repo",
    "name": "repo",
    "private": true,
    "html_url": "https://github.com/org/repo",
    "default_branch": "main",
    "workspace_id": "workspace_object_id",
    "connected_at": "2026-09-01T10:00:00Z",
    "connected_by": "user_object_id"
  }
]
```

---

### POST /api/workspaces/{workspace_id}/repositories
Connect a repository to workspace.

**Headers**: `Cookie: piq_session=<jwt>`, `Content-Type: application/json`

**Path Parameters**: `workspace_id` (string)

**Request Body**:
```json
{
  "github_repo_id": 123456789,
  "full_name": "org/repo",
  "name": "repo",
  "private": true,
  "html_url": "https://github.com/org/repo",
  "default_branch": "main"
}
```

**Response** (201): Repository object

---

### DELETE /api/workspaces/{workspace_id}/repositories/{repo_id}
Disconnect repository from workspace.

**Headers**: `Cookie: piq_session=<jwt>`

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `workspace_id` | string | Workspace ObjectId |
| `repo_id` | string | Repository ObjectId |

**Response** (200):
```json
{ "detail": "Repository disconnected" }
```

---

## GitHub App Endpoints

### GET /api/workspaces/{workspace_id}/github/install
Initiate GitHub App installation flow.

**Headers**: `Cookie: piq_session=<jwt>`

**Path Parameters**: `workspace_id` (string)

**Response**: `302 Redirect` to GitHub App installation page with encoded state

---

### GET /api/github/installations/callback
Handle GitHub App installation callback.

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `installation_id` | integer | Yes | GitHub App installation ID |
| `setup_action` | string | No | Action performed (install, request) |
| `state` | string | Yes | Encoded state with workspace_id + user_id |

**Response**: `302 Redirect` to `/workspace/{workspace_id}?installation=success`

**Error Redirects**:
- `?installation=invalid_state` - Invalid/expired state
- `?installation=workspace_missing` - Workspace not found
- `?installation=github_lookup_failed` - GitHub API error

---

### DELETE /api/workspaces/{workspace_id}/github/installation
Disconnect GitHub App installation.

**Headers**: `Cookie: piq_session=<jwt>`

**Path Parameters**: `workspace_id` (string)

**Response** (200):
```json
{ "detail": "GitHub App disconnected" }
```

---

### GET /api/workspaces/{workspace_id}/github/events
List recent webhook events for workspace.

**Headers**: `Cookie: piq_session=<jwt>`

**Path Parameters**: `workspace_id` (string)

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | integer | 10 | Number of events (1-50) |

**Response** (200):
```json
[
  {
    "delivery_id": "abc123",
    "event_type": "workflow_run",
    "action": "completed",
    "repository_full_name": "org/repo",
    "received_at": "2026-09-26T08:30:00Z"
  }
]
```

---

### POST /api/github/webhooks
Receive GitHub webhook events (primary endpoint).

**Headers**:
- `X-GitHub-Event`: Event type (e.g., `workflow_run`)
- `X-Hub-Signature-256`: HMAC-SHA256 signature
- `X-GitHub-Delivery`: Unique delivery ID
- `Content-Type`: `application/json`

**Request Body**: GitHub webhook payload (varies by event type)

**Response** (202):
```json
{
  "received": true,
  "event_type": "workflow_run",
  "delivery_id": "abc123",
  "workspace_id": "workspace_object_id",
  "repo": "org/repo",
  "run_id": 12345,
  "conclusion": "failure",
  "branch": "feature/xyz",
  "commit_sha": "abcdef123456",
  "triggered_by": "octocat",
  "kafka_topic": "pipeline-events"
}
```

**Ignored Events** (202 with `ignored` field):
- `installation`, `installation_repositories`, `installation_target` - Not CI events
- Non-completed `workflow_run` - Only completed runs tracked

**Errors**: 401 (Invalid signature), 404 (No workspace for installation)

---

### POST /webhook/github
Legacy webhook endpoint (same as above).

---

## Auto-Fix Endpoints

### GET /api/autofix/report
View auto-fix report (public, signed token).

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | Signed JWT report token |

**Response** (200):
```json
{
  "execution": {
    "id": "execution_object_id",
    "mode": "approval_pr",
    "policy_action": "approval_required",
    "execution_status": "awaiting_approval",
    "pr_number": 42,
    "pr_url": "https://github.com/org/repo/pull/42",
    "fix_branch": "pipelineiq/fix/abc123",
    "report_feedback_status": "requested",
    "report_feedback_note": null,
    "reviewer_username": "octocat",
    "reviewer_github_id": 12345678,
    "target_branch": "main",
    "loop_blocked_reason": null,
    "resolution_feedback_status": null,
    "resolution_feedback_url": "https://app.pipelineiq.io/autofix/feedback?token=xyz",
    "report": {
      "fix_summary": "Fix null pointer in user service",
      "possible_fix_steps": [
        "Add null check before accessing user.profile",
        "Add unit test for null profile case"
      ],
      "risk": {
        "plain_english_summary": "Low risk: Single file change, well-tested area"
      }
    },
    "proposed_fix": {
      "summary": "Add null check in user_service.py",
      "files": [
        {
          "path": "src/user_service.py",
          "original_content": "...",
          "new_content": "..."
        }
      ]
    },
    "created_at": "2026-09-26T08:35:00Z",
    "updated_at": "2026-09-26T08:35:00Z"
  },
  "pipeline_run": {
    "workflow_name": "CI Pipeline",
    "branch": "feature/xyz",
    "commit_sha": "abcdef123456",
    "diagnosis": {
      "error_type": "NullPointerException",
      "possible_causes": [
        "User profile not loaded before access",
        "Race condition in profile loading"
      ],
      "latest_working_change": "Refactored user service (commit abc123)"
    },
    "risk": {
      "risk_score": 25,
      "risk_band": "low",
      "plain_english_summary": "Low risk: Single file change..."
    }
  }
}
```

**Errors**: 404 (Invalid/expired token)

---

### POST /api/autofix/report/decision
Submit approve/reject decision on auto-fix report.

**Query Parameters**: `token` (string, required)

**Headers**: `Content-Type: application/json`

**Request Body**:
```json
{
  "decision": "approve",
  "note": "Looks good, please merge"
}
```

**Decision Values**: `approve` | `reject`

**Response** (200):
```json
{
  "detail": "Approved. PR available at https://github.com/org/repo/pull/42",
  "pr_url": "https://github.com/org/repo/pull/42",
  "execution_status": "approved_create_pr"
}
```

**Errors**: 400 (Invalid token), 403 (GitHub API forbidden), 500 (Internal error)

---

### GET /api/autofix/feedback
View resolution feedback form (public, signed token).

**Query Parameters**: `token` (string, required)

**Response** (200):
```json
{
  "feedback": {
    "id": "feedback_object_id",
    "status": "requested",
    "outcome": null,
    "automation_quality": null,
    "should_auto_apply_similar": null,
    "notes": null,
    "feedback_url": "https://app.pipelineiq.io/autofix/feedback?token=xyz",
    "requested_at": "2026-09-26T10:00:00Z",
    "submitted_at": null
  },
  "execution": {
    "id": "execution_object_id",
    "execution_status": "approved_and_merged",
    "mode": "approval_pr",
    "pr_url": "https://github.com/org/repo/pull/42",
    "target_branch": "main",
    "reviewer_username": "octocat",
    "risk_score": 25,
    "fix_summary": "Fix null pointer in user service"
  },
  "pipeline_run": {
    "repository_full_name": "org/repo",
    "workflow_name": "CI Pipeline",
    "branch": "feature/xyz",
    "commit_sha": "abcdef123456",
    "diagnosis": { ... },
    "risk": { ... }
  }
}
```

---

### POST /api/autofix/feedback
Submit resolution feedback.

**Query Parameters**: `token` (string, required)

**Headers**: `Content-Type: application/json`

**Request Body**:
```json
{
  "outcome": "resolved",
  "automation_quality": "excellent",
  "should_auto_apply_similar": true,
  "notes": "Fix was perfect, saved hours of debugging"
}
```

**Outcome Values**: `resolved` | `partially_resolved` | `not_resolved`
**Quality Values**: `excellent` | `acceptable` | `poor`

**Response** (200):
```json
{
  "detail": "Feedback submitted successfully",
  "feedback_id": "feedback_object_id"
}
```

**Errors**: 400 (Invalid token), 500 (Internal error)

---

## Health Endpoint

### GET /health
Health check for load balancers.

**Response** (200):
```json
{ "status": "ok" }
```

---

### GET /
Root endpoint.

**Response** (200):
```json
{ "message": "PipelineIQ API is running" }
```

---

## Webhook Payload Examples

### workflow_run (completed)
```json
{
  "action": "completed",
  "workflow_run": {
    "id": 12345,
    "name": "CI Pipeline",
    "head_branch": "feature/xyz",
    "head_sha": "abcdef1234567890",
    "conclusion": "failure",
    "html_url": "https://github.com/org/repo/actions/runs/12345",
    "triggering_actor": { "login": "octocat" },
    "run_number": 42,
    "event": "push"
  },
  "repository": {
    "id": 123456789,
    "full_name": "org/repo",
    "private": true,
    "html_url": "https://github.com/org/repo",
    "default_branch": "main"
  },
  "installation": { "id": 987654321 },
  "sender": { "login": "octocat" }
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/api/auth/*` | 10 req/min per IP |
| `/api/workspaces*` | 100 req/min per user |
| `/api/github/webhooks` | 1000 req/min per installation |
| `/api/autofix/*` | 50 req/min per token |

---

## Versioning

- API version in URL: `/api/v1/...` (future)
- Current version: `v1` (implicit)
- Breaking changes require new version
- Deprecation notice: 3 months minimum

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-09-26 | Initial specification |

---

*Generated from source of truth in code. Update code first, then regenerate this document.*
