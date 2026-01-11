# Security Best Practices

**Version:** 1.0
**Last Updated:** 2026-01-10
**Audience:** Developers building with ZeroDB and Agent-402

---

## ⚠️ CRITICAL: Never Use API Keys Client-Side

> **WARNING:** API keys MUST NEVER be exposed in client-side code, mobile apps, or any publicly accessible environment.

### Why This Matters

Exposing your API key client-side creates severe security vulnerabilities:

1. **Unauthorized Access**: Anyone can extract your API key from browser DevTools, mobile app binaries, or source code
2. **Resource Abuse**: Attackers can use your key to consume your quota, incurring costs
3. **Data Breach**: Full access to your project data including vectors, tables, and agent memory
4. **Compliance Violations**: Violates SOC 2, GDPR, PCI DSS, and most regulatory frameworks
5. **Reputation Damage**: Security incidents destroy trust in fintech applications

### Real-World Attack Vectors

```javascript
// ❌ DANGEROUS - API key exposed in frontend JavaScript
const API_KEY = 'zerodb_sk_abc123xyz456';

fetch('https://api.ainative.studio/v1/public/projects', {
  headers: { 'X-API-Key': API_KEY }
});
```

**What happens:**
- User opens browser DevTools → Network tab
- User sees your API key in request headers
- User copies key and uses it maliciously
- Your account is compromised in seconds

```html
<!-- ❌ DANGEROUS - API key in HTML -->
<script>
  const config = {
    apiKey: 'zerodb_sk_abc123xyz456',
    projectId: 'proj_123'
  };
</script>
```

**What happens:**
- View page source reveals API key
- Automated scrapers find and harvest keys
- Your key ends up on public GitHub repos or paste sites

```swift
// ❌ DANGEROUS - API key hardcoded in mobile app
let API_KEY = "zerodb_sk_abc123xyz456"

var request = URLRequest(url: apiURL)
request.addValue(API_KEY, forHTTPHeaderField: "X-API-Key")
```

**What happens:**
- App binary is reverse-engineered
- API key extracted using tools like `strings`, Hopper, or Ghidra
- Key is used to access your entire project

---

## ✅ Secure Authentication Patterns

### Pattern 1: Backend Proxy (Recommended)

**Architecture:**
```
[Client App] → [Your Backend API] → [ZeroDB API]
     ↓              ↓                    ↓
  JWT Token    API Key (secure)    Validated Request
```

**Implementation:**

```javascript
// ✅ SECURE - Frontend sends user JWT, not API key
async function searchVectors(query) {
  const response = await fetch('/api/search', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userJwtToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query })
  });
  return response.json();
}
```

```python
# ✅ SECURE - Backend holds API key securely
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthority
import os

app = FastAPI()
security = HTTPBearer()

# API key stored in environment variable
ZERODB_API_KEY = os.getenv('ZERODB_API_KEY')

@app.post('/api/search')
async def search_vectors(
    query: str,
    credentials: HTTPAuthority = Depends(security)
):
    # Verify user's JWT token first
    user = verify_jwt(credentials.credentials)

    # Make request to ZeroDB with YOUR API key
    response = await httpx.post(
        'https://api.ainative.studio/v1/public/embeddings/search',
        headers={'X-API-Key': ZERODB_API_KEY},
        json={'query': query}
    )

    return response.json()
```

**Benefits:**
- API key never leaves your server
- User authentication handled separately (JWT, OAuth, etc.)
- Fine-grained access control per user
- Rate limiting and monitoring in one place
- API key rotation doesn't affect clients

---

### Pattern 2: Temporary Access Tokens

For advanced use cases, implement short-lived tokens:

```python
# ✅ SECURE - Backend issues temporary tokens
from datetime import datetime, timedelta
import jwt

@app.post('/api/get-temp-token')
async def get_temp_token(user: User = Depends(get_current_user)):
    """Issue a short-lived token for specific operations"""

    # Token valid for 5 minutes
    expiry = datetime.utcnow() + timedelta(minutes=5)

    token = jwt.encode({
        'user_id': user.id,
        'scope': 'search_only',  # Limited permissions
        'project_id': 'proj_abc123',
        'exp': expiry
    }, SECRET_KEY)

    return {'token': token, 'expires_at': expiry}
```

```javascript
// ✅ Client uses temporary token
async function searchWithTempToken() {
  // Get temp token from your backend
  const { token } = await fetch('/api/get-temp-token').then(r => r.json());

  // Use temp token (still through your backend proxy)
  const results = await fetch('/api/search', {
    headers: { 'X-Temp-Token': token }
  });
}
```

---

### Pattern 3: Environment-Based Configuration

**Never commit API keys to version control:**

```bash
# ✅ .env file (add to .gitignore)
ZERODB_API_KEY=zerodb_sk_abc123xyz456
ZERODB_PROJECT_ID=proj_xyz789
DATABASE_URL=postgresql://...
```

```python
# ✅ Load from environment
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('ZERODB_API_KEY')
if not API_KEY:
    raise ValueError('ZERODB_API_KEY environment variable not set')
```

```gitignore
# ✅ .gitignore - Always exclude secrets
.env
.env.local
.env.production
*.pem
*.key
secrets/
```

---

## 🔒 API Key Management Best Practices

### 1. Key Rotation

Rotate API keys regularly (recommended: every 90 days):

```python
# Rotation strategy for zero-downtime
ZERODB_API_KEY_PRIMARY = os.getenv('ZERODB_API_KEY_PRIMARY')
ZERODB_API_KEY_SECONDARY = os.getenv('ZERODB_API_KEY_SECONDARY')

def get_api_key():
    """Use primary key, fall back to secondary during rotation"""
    return ZERODB_API_KEY_PRIMARY or ZERODB_API_KEY_SECONDARY
```

### 2. Key Scoping

Use separate API keys for different environments:

```bash
# Development
ZERODB_API_KEY_DEV=zerodb_sk_dev_...

# Staging
ZERODB_API_KEY_STAGING=zerodb_sk_staging_...

# Production
ZERODB_API_KEY_PROD=zerodb_sk_prod_...
```

### 3. Access Auditing

Log all API key usage:

```python
import logging

logger = logging.getLogger(__name__)

def make_zerodb_request(endpoint, data):
    logger.info(f"ZeroDB request: {endpoint}", extra={
        'user_id': current_user.id,
        'timestamp': datetime.utcnow(),
        'ip_address': request.remote_addr
    })

    # Make request...
```

### 4. Secret Management Tools

Use proper secret management in production:

```python
# ✅ AWS Secrets Manager
import boto3

def get_api_key():
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId='zerodb/api-key')
    return response['SecretString']

# ✅ HashiCorp Vault
import hvac

def get_api_key():
    client = hvac.Client(url='https://vault.example.com')
    secret = client.secrets.kv.v2.read_secret_version(path='zerodb/api-key')
    return secret['data']['data']['key']

# ✅ Google Cloud Secret Manager
from google.cloud import secretmanager

def get_api_key():
    client = secretmanager.SecretManagerServiceClient()
    name = "projects/PROJECT_ID/secrets/zerodb-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode('UTF-8')
```

---

## 🚫 What NOT To Do

### ❌ Never Store Keys in Frontend Code

```javascript
// ❌ DANGER - Visible in source
const API_KEY = 'zerodb_sk_abc123';

// ❌ DANGER - Webpack still exposes this
const API_KEY = process.env.REACT_APP_API_KEY;

// ❌ DANGER - Obfuscation is not security
const API_KEY = atob('emVyb2RiX3NrX2FiYzEyMw==');
```

### ❌ Never Commit Keys to Git

```bash
# ❌ DANGER - Keys in git history are permanent
git add .env
git commit -m "Add config"
git push

# If you did this:
# 1. Immediately revoke the key in ZeroDB dashboard
# 2. Generate new key
# 3. Use git-filter-branch or BFG to remove from history
# 4. Force push (coordinate with team)
```

### ❌ Never Share Keys in Public

```markdown
<!-- ❌ DANGER - Stack Overflow, Discord, Slack -->
"I'm getting a 401 error with this key: zerodb_sk_abc123"

<!-- ✅ CORRECT -->
"I'm getting a 401 error. I've verified my X-API-Key header format is correct."
```

### ❌ Never Use Production Keys in Development

```python
# ❌ DANGER - Production key in dev environment
API_KEY = 'zerodb_sk_prod_...'  # Risks production data

# ✅ CORRECT - Separate keys
API_KEY = os.getenv('ZERODB_API_KEY_DEV')
```

---

## 🛡️ Defense in Depth

Implement multiple security layers:

### 1. Network Security

```nginx
# Rate limiting at nginx/proxy level
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

server {
    location /api/ {
        limit_req zone=api burst=20;
        proxy_pass http://backend;
    }
}
```

### 2. Application Security

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter

# Only allow specific origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=['https://yourapp.com'],
    allow_credentials=True,
    allow_methods=['POST'],
    allow_headers=['Authorization', 'Content-Type'],
)

@app.post('/api/search')
@limiter.limit("5/minute")
async def search(request: Request, query: str):
    # Your logic here
    pass
```

### 3. Monitoring and Alerting

```python
# Alert on suspicious activity
if request_count > 1000 and time_window < 60:
    alert_security_team(
        message="Possible API key compromise",
        details={
            'ip': request.remote_addr,
            'endpoint': request.url,
            'count': request_count
        }
    )
```

---

## 📱 Mobile App Considerations

### iOS Best Practices

```swift
// ✅ SECURE - Use backend proxy
struct APIClient {
    let baseURL = "https://your-backend.com/api"

    func search(query: String) async throws -> SearchResults {
        // User token from secure keychain
        guard let userToken = KeychainHelper.getUserToken() else {
            throw APIError.notAuthenticated
        }

        var request = URLRequest(url: URL(string: "\(baseURL)/search")!)
        request.addValue("Bearer \(userToken)", forHTTPHeaderField: "Authorization")

        // Backend handles ZeroDB API key
        let (data, _) = try await URLSession.shared.data(for: request)
        return try JSONDecoder().decode(SearchResults.self, from: data)
    }
}
```

### Android Best Practices

```kotlin
// ✅ SECURE - Use backend proxy
class ZeroDBClient(private val context: Context) {
    private val baseUrl = "https://your-backend.com/api"

    suspend fun search(query: String): SearchResults {
        // User token from Android Keystore
        val userToken = KeyStoreManager.getUserToken()

        val request = Request.Builder()
            .url("$baseUrl/search")
            .addHeader("Authorization", "Bearer $userToken")
            .post(query.toRequestBody())
            .build()

        // Backend handles ZeroDB API key
        return withContext(Dispatchers.IO) {
            val response = httpClient.newCall(request).execute()
            response.body?.let { parseSearchResults(it.string()) }
                ?: throw APIException("Empty response")
        }
    }
}
```

---

## 🔍 Security Checklist

Before deploying your application:

- [ ] API keys stored in environment variables or secret manager
- [ ] `.env` and secret files in `.gitignore`
- [ ] No API keys in frontend code (JavaScript, mobile apps)
- [ ] Backend proxy implemented for all ZeroDB requests
- [ ] User authentication separate from API key authentication
- [ ] Rate limiting configured
- [ ] CORS configured to allow only your domains
- [ ] HTTPS enforced on all endpoints
- [ ] Monitoring and alerting set up
- [ ] Key rotation schedule established
- [ ] Team trained on security practices
- [ ] Security testing performed (penetration test, code review)

---

## 📚 Additional Resources

### Official Documentation
- [ZeroDB API Specification](/api-spec.md)
- [Developer Guide](/datamodel.md)
- [DX Contract](/DX-Contract.md)

### Security Standards
- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [PCI DSS Requirements](https://www.pcisecuritystandards.org/)

### Tools
- [git-secrets](https://github.com/awslabs/git-secrets) - Prevents committing secrets
- [truffleHog](https://github.com/trufflesecurity/trufflehog) - Scans for secrets in git history
- [Gitleaks](https://github.com/gitleaks/gitleaks) - Scans repositories for secrets

---

## 🆘 What to Do If Your Key Is Compromised

1. **Immediately revoke the key** in ZeroDB dashboard
2. **Generate a new API key**
3. **Update environment variables** in all environments
4. **Review access logs** for suspicious activity
5. **Notify your security team**
6. **Document the incident** for compliance
7. **Review and improve** security practices

---

## 📞 Support

For security concerns or to report a vulnerability:

- **Security Email:** security@ainative.studio (not yet active - contact support)
- **General Support:** [https://ainative.studio](https://ainative.studio)
- **Documentation Issues:** Open an issue on GitHub

---

**Remember:** Security is not optional in fintech applications. One exposed API key can compromise your entire system.
