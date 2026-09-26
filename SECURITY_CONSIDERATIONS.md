# Security Considerations

## Threat Model

### Assets to Protect
| Asset | Classification | Impact if Compromised |
|-------|----------------|----------------------|
| GitHub OAuth tokens | Critical | Full user account access |
| GitHub App private key | Critical | Repository read/write, webhook forgery |
| GitHub installation tokens | Critical | Repository access per installation |
| LLM API keys | High | Cost abuse, rate limit exhaustion |
| User session tokens | High | Account takeover |
| Webhook signatures | Medium | Fake pipeline events |
| Auto-fix reports | Medium | Information disclosure |
| Database credentials | Critical | Full data access |

### Threat Actors
1. **External attackers** - Internet-facing attack surface
2. **Malicious insiders** - Compromised developer accounts
3. **Supply chain** - Compromised dependencies
4. **Accidental exposure** - Misconfiguration, logs

---

## Security Controls by Layer

### 1. Network Security

#### TLS Everywhere
- Vercel: Automatic HTTPS
- Render: Automatic HTTPS
- MongoDB Atlas: TLS required
- Kafka: SASL_SSL (production) / PLAINTEXT (dev only)

#### CORS Policy
```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],  # Single origin, no wildcards
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)
```

#### Rate Limiting
```python
# TODO: Implement with slowapi or similar
# Per-IP limits on auth endpoints
# Per-user limits on API endpoints
# Per-installation limits on webhook endpoint
```

### 2. Application Security

#### Authentication & Session Management
- **JWT in HttpOnly cookies** (not localStorage)
- **SameSite=Lax** for CSRF protection
- **Secure flag** in production
- **Short expiry** (15 days) with refresh rotation
- **Token blacklisting** on logout
- **Rotation on privilege change**

```python
# auth/cookies.py - Secure defaults
def set_session_cookie(response: Response, token: str) -> None:
    cookie_kwargs = {
        "key": "piq_session",
        "value": token,
        "httponly": True,
        "secure": settings.COOKIE_SECURE,  # True in prod
        "samesite": "lax",
        "max_age": settings.SESSION_EXPIRY_DAYS * 86400,
    }
    # No domain = host-only cookie
```

#### Input Validation
- **Pydantic v2 strict mode** on all models
- **String length limits** on all text fields
- **Sanitization** for user-controlled data in logs
- **Parameterized queries** via Beanie (no injection)

```python
# Example: Strict model
class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    risk_profile: RiskProfile
```

#### Output Encoding
- **JSON responses** auto-encoded by FastAPI
- **HTML templates** (if any) use auto-escaping
- **Log injection prevention**: structured logging

#### Secrets Management
```python
# config.py - Never log secrets
class Settings(BaseSettings):
    GITHUB_APP_PRIVATE_KEY: str
    JWT_SECRET: str
    
    @property
    def github_app_private_key_pem(self) -> str:
        return self.GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n")

# Use platform secret managers in production:
# - Render: Environment variables (encrypted at rest)
# - Vercel: Environment variables (encrypted at rest)
# - GitHub Actions: Repository/Organization secrets
```

#### Field-Level Encryption (Recommended)
```python
# TODO: Implement with cryptography.fernet
from cryptography.fernet import Fernet

class EncryptedField:
    def __init__(self, key: bytes):
        self.cipher = Fernet(key)
    
    def encrypt(self, value: str) -> str:
        return self.cipher.encrypt(value.encode()).decode()
    
    def decrypt(self, value: str) -> str:
        return self.cipher.decrypt(value.encode()).decode()

# Apply to:
# - User.github_access_token
# - Workspace.github_installation_id (consider)
# - AutoFixExecution.signed_report_token
# - AutoFixFeedback.feedback_token
```

### 3. GitHub Integration Security

#### Webhook Verification
```python
# services/github_app.py
def verify_webhook_signature(body: bytes, signature: str) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    
    expected = hmac.new(
        settings.GITHUB_APP_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected}", signature)
```

#### Installation Token Handling
- **Short-lived** (1 hour) - auto-refreshed before use
- **Scoped to installation** - least privilege
- **Never logged** - masked in logs
- **Cached in memory** with TTL

#### OAuth State Parameter
```python
# auth/jwt.py - Installation state token
def create_installation_state(user_id: str, workspace_id: str) -> str:
    payload = {
        "sub": "installation",
        "user_id": user_id,
        "workspace_id": workspace_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
```

### 4. LLM Provider Security

#### API Key Rotation
- Store in platform secrets (not code)
- Rotate quarterly
- Monitor usage for anomalies

#### Request/Response Logging
```python
# services/llm_gateway.py - Sanitize before logging
def sanitize_for_logging(data: dict) -> dict:
    """Remove sensitive fields from logs"""
    sanitized = data.copy()
    sensitive_keys = ["api_key", "authorization", "token", "secret", "password"]
    for key in list(sanitized.keys()):
        if any(s in key.lower() for s in sensitive_keys):
            sanitized[key] = "***REDACTED***"
    return sanitized
```

#### Provider Failover Security
- Validate fallback provider responses
- Same schema validation for all providers
- Circuit breaker per provider

### 5. Data Protection

#### Data Retention
| Data Type | Retention | Deletion Method |
|-----------|-----------|-----------------|
| Webhook events | 30 days | TTL index |
| Pipeline runs | 1 year | TTL index |
| Auto-fix executions | 2 years | Manual cleanup |
| Feedback | 2 years | Manual cleanup |
| User sessions | 15 days | JWT expiry |
| Audit logs | 7 years | Archive to cold storage |

#### PII Handling
- **Minimize collection**: Only GitHub profile data
- **No sensitive PII**: No SSN, credit card, health data
- **Right to deletion**: Implement `/api/auth/me/delete`
- **Data portability**: Export endpoint for user data

#### Database Security
```javascript
// MongoDB Atlas - Network
// 1. VPC Peering (preferred) or IP whitelist
// 2. Database user with readWrite only on pipelineiq DB
// 3. Encryption at rest: Enabled by default
// 4. Backup encryption: Enabled
// 5. Auditing: Enabled for paid tiers
```

### 6. Infrastructure Security

#### Container Security
```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser
USER appuser

# No unnecessary packages
# Multi-stage build for smaller image
# Scan with: docker scout cves <image>
```

#### Dependency Scanning
```yaml
# .github/workflows/security.yml
- name: Python dependency scan
  run: |
    pip install pip-audit
    pip-audit -r requirements.txt --format=json > pip-audit.json
    
- name: Node dependency scan
  run: |
    cd packages/frontend
    npm audit --json > npm-audit.json
```

#### SBOM Generation
```bash
# Generate Software Bill of Materials
syft packages/backend:latest -o spdx-json=sbom-backend.spdx.json
syft packages/frontend:latest -o spdx-json=sbom-frontend.spdx.json
```

### 7. Operational Security

#### Logging & Monitoring
```python
# Structured logging with correlation IDs
import structlog

logger = structlog.get_logger()

# Middleware adds request_id
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    structlog.contextvars.bind_contextvars(request_id=request_id)
    response = await call_next(request)
    return response

# Log format: JSON with timestamp, level, request_id, message, context
```

#### Alerting Rules
```yaml
# PrometheusRule examples
groups:
- name: security
  rules:
  - alert: HighFailedLoginRate
    expr: rate(auth_failures_total[5m]) > 10
    labels:
      severity: warning
    annotations:
      summary: "High authentication failure rate"
      
  - alert: WebhookSignatureFailures
    expr: rate(webhook_signature_failures_total[5m]) > 5
    labels:
      severity: critical
    annotations:
      summary: "Webhook signature verification failures"
      
  - alert: LLMAPIErrors
    expr: rate(llm_errors_total[5m]) > 0.1
    labels:
      severity: warning
    annotations:
      summary: "LLM provider error rate elevated"
```

#### Incident Response
1. **Detection**: Alerting + log analysis
2. **Containment**: Rotate affected credentials immediately
3. **Investigation**: Correlation IDs for tracing
4. **Recovery**: Deploy patched version, verify
5. **Postmortem**: Blameless, documented, action items

---

## Compliance Considerations

### SOC 2 Type II (Future)
- Access controls documented
- Audit logging implemented
- Encryption at rest/transit
- Incident response plan
- Vendor risk assessment

### GDPR (If EU Users)
- Lawful basis: Legitimate interest / Consent
- Data minimization
- Right to access/rectification/erasure
- Data processing agreement with subprocessors
- DPIA for high-risk processing

---

## Security Checklist for Releases

### Pre-Deployment
- [ ] All dependencies scanned (pip-audit, npm audit)
- [ ] Container image scanned (docker scout, trivy)
- [ ] Secrets not in code (trufflehog, git-secrets)
- [ ] SAST scan (bandit, semgrep)
- [ ] DAST scan on staging (OWASP ZAP)
- [ ] Penetration test (annual)

### Post-Deployment
- [ ] Health checks passing
- [ ] Error rates normal
- [ ] Webhook processing latency normal
- [ ] No new vulnerabilities in dependencies
- [ ] Audit logs reviewable

### Quarterly
- [ ] Rotate all API keys/secrets
- [ ] Review access permissions
- [ ] Update threat model
- [ ] Security training for team
- [ ] Dependency update sprint

---

## Vulnerability Disclosure

### Responsible Disclosure
- Email: security@pipelineiq.io
- PGP key: [link]
- Scope: pipelineiq.io, *.pipelineiq.io
- Safe harbor: Good faith research protected

### Bug Bounty (Future)
- Platform: HackerOne / GitHub Security Advisories
- Scope: Production domains
- Rewards: Based on severity

---

## Secure Development Practices

### Code Review Requirements
- Security-focused review for auth/crypto changes
- No secrets in PR diffs
- Dependency changes require approval

### Secure Defaults
- Deny by default (CORS, permissions)
- Principle of least privilege
- Fail closed (not open)

### Security Testing in CI
```yaml
# Every PR
- bandit -r src/           # Python SAST
- semgrep --config=auto src/  # Pattern-based SAST
- npm audit --audit-level=high  # Node deps
```

---

*Last updated: 2026-09-26*
*Review quarterly or after security incidents*
