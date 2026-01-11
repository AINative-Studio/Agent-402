# API Key Security Guide

**Version:** 1.0
**Last Updated:** 2026-01-10
**Audience:** Developers integrating with Agent-402 and ZeroDB APIs

---

## Table of Contents

1. [Critical Warning](#critical-warning)
2. [Why API Keys Must Never Be Client-Side](#why-api-keys-must-never-be-client-side)
3. [Vulnerable Patterns (WRONG)](#vulnerable-patterns-wrong)
4. [Secure Backend Proxy Pattern (RIGHT)](#secure-backend-proxy-pattern-right)
5. [Mobile Application Security](#mobile-application-security)
6. [Environment Configuration](#environment-configuration)
7. [Secret Management](#secret-management)
8. [Compliance Considerations](#compliance-considerations)
9. [Security Checklist](#security-checklist)
10. [Incident Response](#incident-response)

---

## Critical Warning

> **WARNING: API KEYS MUST NEVER BE EXPOSED IN CLIENT-SIDE CODE**
>
> This includes:
> - JavaScript running in browsers
> - React, Vue, Angular, or any frontend framework
> - iOS and Android mobile applications
> - Desktop applications distributed to end users
> - Any code that can be inspected by end users
>
> **Violating this principle will result in immediate security compromise.**

For the full security policy, see [SECURITY.md](/SECURITY.md) in the project root.

---

## Why API Keys Must Never Be Client-Side

### The Fundamental Problem

Client-side code is **inherently untrusted**. Any code running on a user's device can be:

1. **Inspected** - Browser DevTools, View Source, APK decompilers
2. **Extracted** - Automated tools harvest secrets from public code
3. **Abused** - Stolen keys enable unauthorized access to your entire system

### Risk Assessment

| Risk | Impact | Likelihood | Severity |
|------|--------|------------|----------|
| API Key Theft | Full account compromise | HIGH | CRITICAL |
| Data Exfiltration | All project data exposed | HIGH | CRITICAL |
| Resource Abuse | Quota exhaustion, financial loss | HIGH | HIGH |
| Regulatory Violation | Fines, legal action | MEDIUM | CRITICAL |
| Reputation Damage | Loss of customer trust | HIGH | HIGH |

### What Attackers Can Do With Your API Key

Once an attacker obtains your API key, they can:

- **Read all data** in your ZeroDB projects (vectors, tables, files)
- **Write malicious data** to your databases
- **Delete your data** causing irreversible loss
- **Consume your quota** resulting in service disruption and charges
- **Access agent memory** containing sensitive conversation data
- **Impersonate your application** to your users

---

## Vulnerable Patterns (WRONG)

### Pattern 1: Hardcoded in React/JavaScript

```javascript
// WRONG - API key visible in browser DevTools and source code
const API_KEY = 'zerodb_sk_abc123xyz456';

async function fetchProjects() {
  const response = await fetch('https://api.ainative.studio/v1/public/projects', {
    headers: {
      'X-API-Key': API_KEY  // Exposed in Network tab
    }
  });
  return response.json();
}
```

**Why this fails:**
- Open browser DevTools > Network tab
- Click on any request to the API
- API key visible in request headers
- Anyone can copy and misuse it

---

### Pattern 2: Environment Variables in Frontend Builds

```javascript
// WRONG - Build-time env vars are still embedded in the bundle
const API_KEY = process.env.REACT_APP_API_KEY;
const API_KEY = import.meta.env.VITE_API_KEY;

// The bundled JavaScript will contain the actual key value
fetch('/api', { headers: { 'X-API-Key': API_KEY } });
```

**Why this fails:**
- Webpack/Vite replace env vars at **build time**
- The actual key string ends up in `bundle.js`
- Anyone can find it with: `grep -r "zerodb_sk" dist/`

---

### Pattern 3: Obfuscation or Encoding

```javascript
// WRONG - Obfuscation is NOT security
const API_KEY = atob('emVyb2RiX3NrX2FiYzEyMw==');  // Base64
const API_KEY = rot13('mrebqo_fx_nop123');          // ROT13
const API_KEY = decrypt('encrypted_key', 'key');    // Client-side decrypt

// All of these can be trivially reversed
```

**Why this fails:**
- Attackers are not fooled by obfuscation
- Automated tools decode common patterns instantly
- Security through obscurity is no security at all

---

### Pattern 4: HTML Meta Tags or Data Attributes

```html
<!-- WRONG - Visible in page source -->
<meta name="api-key" content="zerodb_sk_abc123xyz456">

<!-- WRONG - Visible in DOM inspector -->
<div data-api-key="zerodb_sk_abc123xyz456"></div>

<script>
  // WRONG - Inline scripts are fully visible
  window.CONFIG = {
    apiKey: 'zerodb_sk_abc123xyz456'
  };
</script>
```

**Why this fails:**
- View Page Source reveals everything
- DOM inspection shows all data attributes
- Web crawlers index exposed secrets

---

### Pattern 5: Mobile App Hardcoding

```swift
// WRONG - iOS app binary can be decompiled
let apiKey = "zerodb_sk_abc123xyz456"

var request = URLRequest(url: apiURL)
request.addValue(apiKey, forHTTPHeaderField: "X-API-Key")
```

```kotlin
// WRONG - Android APK can be reverse-engineered
val apiKey = "zerodb_sk_abc123xyz456"

val request = Request.Builder()
    .addHeader("X-API-Key", apiKey)
    .build()
```

```dart
// WRONG - Flutter apps compile to readable JavaScript (web) or decompilable binaries
const String apiKey = "zerodb_sk_abc123xyz456";
```

**Why this fails:**
- iOS: Use `strings` command or Hopper Disassembler
- Android: Use `apktool` or jadx to decompile
- Flutter: Dart AOT still contains string literals

---

### Pattern 6: Configuration Files in Public Repositories

```json
// WRONG - config.json committed to git
{
  "apiKey": "zerodb_sk_abc123xyz456",
  "projectId": "proj_123"
}
```

```yaml
# WRONG - config.yml with secrets
api:
  key: zerodb_sk_abc123xyz456
```

**Why this fails:**
- Git history is permanent (even after deletion)
- GitHub/GitLab crawlers detect exposed secrets
- Attackers actively scan public repositories

---

## Secure Backend Proxy Pattern (RIGHT)

### Architecture Overview

```
+------------------+        +------------------+        +------------------+
|   Client App     |  JWT   |   Your Backend   | API Key|   ZeroDB API     |
|  (Browser/Mobile)|------->|   (FastAPI/Node) |------->| (ainative.studio)|
+------------------+        +------------------+        +------------------+
        |                          |                          |
   User Token              API Key (secure)           Authenticated Request
   (expires, revocable)    (env var, never exposed)   (validated, logged)
```

### Implementation: Python/FastAPI Backend

```python
# RIGHT - Backend proxy with secure API key handling

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import httpx
import os
import jwt
from datetime import datetime

app = FastAPI()
security = HTTPBearer()

# API key loaded from environment - NEVER hardcoded
ZERODB_API_KEY = os.getenv('ZERODB_API_KEY')
ZERODB_BASE_URL = os.getenv('ZERODB_BASE_URL', 'https://api.ainative.studio')
JWT_SECRET = os.getenv('JWT_SECRET')

if not ZERODB_API_KEY:
    raise RuntimeError('ZERODB_API_KEY environment variable is required')


class SearchRequest(BaseModel):
    query: str
    limit: int = 10


def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify the user's JWT token (your auth system, not ZeroDB)"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            JWT_SECRET,
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token has expired'
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid token'
        )


@app.post('/api/v1/search')
async def search_vectors(
    request: SearchRequest,
    user: dict = Depends(verify_user_token)
):
    """
    Proxy endpoint for vector search.

    - Client sends their JWT token (your auth)
    - Backend verifies user identity
    - Backend makes ZeroDB request with YOUR API key
    - API key never leaves the server
    """

    # Log the request for audit trail
    print(f"Search request from user {user.get('user_id')} at {datetime.utcnow()}")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f'{ZERODB_BASE_URL}/v1/public/embeddings/search',
            headers={
                'X-API-Key': ZERODB_API_KEY,  # Your API key - secure on server
                'Content-Type': 'application/json'
            },
            json={
                'query_text': request.query,
                'limit': request.limit
            },
            timeout=30.0
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail='Search failed'
            )

        return response.json()


@app.get('/api/v1/projects')
async def list_projects(user: dict = Depends(verify_user_token)):
    """
    Proxy endpoint for listing projects.
    Backend handles API key authentication to ZeroDB.
    """

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f'{ZERODB_BASE_URL}/v1/public/projects',
            headers={'X-API-Key': ZERODB_API_KEY},
            timeout=30.0
        )

        return response.json()
```

### Implementation: Node.js/Express Backend

```javascript
// RIGHT - Node.js backend proxy

const express = require('express');
const axios = require('axios');
const jwt = require('jsonwebtoken');

const app = express();
app.use(express.json());

// API key from environment - NEVER hardcoded
const ZERODB_API_KEY = process.env.ZERODB_API_KEY;
const ZERODB_BASE_URL = process.env.ZERODB_BASE_URL || 'https://api.ainative.studio';
const JWT_SECRET = process.env.JWT_SECRET;

if (!ZERODB_API_KEY) {
  throw new Error('ZERODB_API_KEY environment variable is required');
}

// Middleware to verify user JWT
const authenticateUser = (req, res, next) => {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing authorization token' });
  }

  const token = authHeader.substring(7);

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid token' });
  }
};

// Proxy endpoint for vector search
app.post('/api/v1/search', authenticateUser, async (req, res) => {
  const { query, limit = 10 } = req.body;

  console.log(`Search request from user ${req.user.userId} at ${new Date().toISOString()}`);

  try {
    const response = await axios.post(
      `${ZERODB_BASE_URL}/v1/public/embeddings/search`,
      { query_text: query, limit },
      {
        headers: {
          'X-API-Key': ZERODB_API_KEY,  // Your API key - secure on server
          'Content-Type': 'application/json'
        },
        timeout: 30000
      }
    );

    res.json(response.data);
  } catch (error) {
    console.error('ZeroDB request failed:', error.message);
    res.status(error.response?.status || 500).json({ error: 'Search failed' });
  }
});

// Proxy endpoint for listing projects
app.get('/api/v1/projects', authenticateUser, async (req, res) => {
  try {
    const response = await axios.get(
      `${ZERODB_BASE_URL}/v1/public/projects`,
      {
        headers: { 'X-API-Key': ZERODB_API_KEY },
        timeout: 30000
      }
    );

    res.json(response.data);
  } catch (error) {
    res.status(error.response?.status || 500).json({ error: 'Failed to fetch projects' });
  }
});

app.listen(3000, () => console.log('Backend proxy running on port 3000'));
```

### Frontend Code (Correct Pattern)

```javascript
// RIGHT - Frontend sends user JWT, NOT API key

async function searchVectors(query) {
  // Get user's JWT from your auth system (cookie, localStorage, etc.)
  const userToken = await getAuthToken();

  // Send request to YOUR backend (not directly to ZeroDB)
  const response = await fetch('/api/v1/search', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userToken}`,  // User's token, not API key
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ query, limit: 10 })
  });

  if (!response.ok) {
    throw new Error('Search failed');
  }

  return response.json();
}

async function listProjects() {
  const userToken = await getAuthToken();

  const response = await fetch('/api/v1/projects', {
    headers: {
      'Authorization': `Bearer ${userToken}`
    }
  });

  return response.json();
}
```

---

## Mobile Application Security

### iOS - Secure Implementation

```swift
// RIGHT - iOS app communicates with YOUR backend, not ZeroDB directly

import Foundation

class APIClient {
    private let baseURL = "https://your-backend.com/api/v1"

    /// Get user token from secure Keychain storage
    private func getUserToken() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: "userToken",
            kSecReturnData as String: true
        ]

        var result: AnyObject?
        SecItemCopyMatching(query as CFDictionary, &result)

        guard let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            return nil
        }

        return token
    }

    /// Search vectors through your backend proxy
    func searchVectors(query: String) async throws -> SearchResults {
        guard let token = getUserToken() else {
            throw APIError.notAuthenticated
        }

        var request = URLRequest(url: URL(string: "\(baseURL)/search")!)
        request.httpMethod = "POST"
        request.addValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        request.addValue("application/json", forHTTPHeaderField: "Content-Type")

        let body = ["query": query, "limit": 10] as [String: Any]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        // Request goes to YOUR backend - API key stays on YOUR server
        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw APIError.requestFailed
        }

        return try JSONDecoder().decode(SearchResults.self, from: data)
    }
}
```

### Android - Secure Implementation

```kotlin
// RIGHT - Android app communicates with YOUR backend, not ZeroDB directly

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.security.KeyStore

class APIClient(private val context: Context) {
    private val baseUrl = "https://your-backend.com/api/v1"
    private val httpClient = OkHttpClient()

    /**
     * Get user token from Android Keystore (encrypted storage)
     */
    private fun getUserToken(): String? {
        val sharedPrefs = context.getSharedPreferences("auth", Context.MODE_PRIVATE)
        return sharedPrefs.getString("userToken", null)
    }

    /**
     * Search vectors through your backend proxy
     * API key NEVER leaves your server
     */
    suspend fun searchVectors(query: String): SearchResults {
        val token = getUserToken() ?: throw AuthException("Not authenticated")

        val jsonBody = JSONObject().apply {
            put("query", query)
            put("limit", 10)
        }

        val request = Request.Builder()
            .url("$baseUrl/search")
            .addHeader("Authorization", "Bearer $token")  // User token, NOT API key
            .addHeader("Content-Type", "application/json")
            .post(jsonBody.toString().toRequestBody("application/json".toMediaType()))
            .build()

        // Request goes to YOUR backend
        val response = httpClient.newCall(request).execute()

        if (!response.isSuccessful) {
            throw APIException("Search failed: ${response.code}")
        }

        return parseSearchResults(response.body?.string() ?: "")
    }
}
```

---

## Environment Configuration

### Server-Side Environment Setup

```bash
# .env file (add to .gitignore - NEVER commit)

# ZeroDB API credentials
ZERODB_API_KEY=zerodb_sk_your_actual_key_here
ZERODB_PROJECT_ID=proj_your_project_id
ZERODB_BASE_URL=https://api.ainative.studio

# Your application secrets
JWT_SECRET=your_jwt_signing_secret_here
DATABASE_URL=postgresql://user:pass@localhost/db

# Environment
NODE_ENV=production
DEBUG=false
```

### .gitignore Configuration

```gitignore
# Environment files - ALWAYS exclude
.env
.env.local
.env.development
.env.production
.env.*.local

# Secret files
*.pem
*.key
*.p12
secrets/
credentials/

# IDE configurations that may contain secrets
.idea/
.vscode/settings.json

# Build artifacts that may contain embedded secrets
dist/
build/
*.bundle.js
```

### Loading Environment Variables

```python
# Python - using python-dotenv
import os
from dotenv import load_dotenv

# Load from .env file in development
load_dotenv()

# Access with validation
API_KEY = os.getenv('ZERODB_API_KEY')
if not API_KEY:
    raise ValueError('ZERODB_API_KEY environment variable is required')
```

```javascript
// Node.js - using dotenv
require('dotenv').config();

const API_KEY = process.env.ZERODB_API_KEY;
if (!API_KEY) {
  throw new Error('ZERODB_API_KEY environment variable is required');
}
```

---

## Secret Management

### Production Secret Management Solutions

For production deployments, use dedicated secret management:

#### AWS Secrets Manager

```python
import boto3
from botocore.exceptions import ClientError

def get_api_key():
    """Retrieve API key from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='us-east-1')

    try:
        response = client.get_secret_value(SecretId='zerodb/api-key')
        return response['SecretString']
    except ClientError as e:
        raise RuntimeError(f'Failed to retrieve secret: {e}')
```

#### HashiCorp Vault

```python
import hvac

def get_api_key():
    """Retrieve API key from HashiCorp Vault"""
    client = hvac.Client(url='https://vault.example.com')
    client.token = os.getenv('VAULT_TOKEN')

    secret = client.secrets.kv.v2.read_secret_version(
        path='zerodb/api-key',
        mount_point='secret'
    )

    return secret['data']['data']['key']
```

#### Google Cloud Secret Manager

```python
from google.cloud import secretmanager

def get_api_key():
    """Retrieve API key from Google Cloud Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()

    name = "projects/YOUR_PROJECT/secrets/zerodb-api-key/versions/latest"
    response = client.access_secret_version(request={"name": name})

    return response.payload.data.decode('UTF-8')
```

#### Azure Key Vault

```python
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

def get_api_key():
    """Retrieve API key from Azure Key Vault"""
    credential = DefaultAzureCredential()
    client = SecretClient(
        vault_url="https://your-vault.vault.azure.net/",
        credential=credential
    )

    secret = client.get_secret("zerodb-api-key")
    return secret.value
```

---

## Compliance Considerations

### OWASP API Security Top 10

This guide addresses several OWASP API Security risks:

| OWASP Risk | How This Guide Addresses It |
|------------|----------------------------|
| API1: Broken Object Level Authorization | Backend proxy enforces user-level access control |
| API2: Broken Authentication | API keys isolated from user authentication |
| API3: Broken Object Property Level Authorization | Backend filters response data per user |
| API5: Broken Function Level Authorization | Proxy endpoints enforce function-level access |

Reference: [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)

### SOC 2 Compliance

SOC 2 Trust Service Criteria addressed:

- **CC6.1**: Logical and physical access controls - API keys stored securely
- **CC6.6**: Security for transmission - HTTPS enforced, keys never in transit to clients
- **CC6.7**: Disposal of data - Key rotation and revocation procedures

### GDPR Compliance

- **Article 32**: Security of processing - API keys protected with appropriate measures
- **Article 33**: Breach notification - Incident response procedures documented
- **Article 5(1)(f)**: Integrity and confidentiality - Data protected by secure authentication

### PCI DSS Requirements

For applications handling payment data:

- **Requirement 3**: Protect stored cardholder data - Secrets management required
- **Requirement 4**: Encrypt transmission - HTTPS and secure key handling
- **Requirement 8**: Identify and authenticate access - Proper authentication separation

---

## Security Checklist

Before deploying your application, verify:

### API Key Protection

- [ ] API keys stored in environment variables or secret manager
- [ ] API keys NEVER present in frontend/client code
- [ ] API keys NEVER committed to version control
- [ ] `.env` files added to `.gitignore`
- [ ] No API keys in build artifacts or bundles

### Backend Proxy

- [ ] Backend proxy implemented for all ZeroDB API calls
- [ ] User authentication separate from API key authentication
- [ ] Request validation and sanitization in place
- [ ] Error responses do not leak API keys or internal details

### Access Control

- [ ] Rate limiting configured on proxy endpoints
- [ ] CORS configured to allow only your domains
- [ ] User-level authorization enforced
- [ ] Audit logging enabled for all API requests

### Infrastructure

- [ ] HTTPS enforced on all endpoints
- [ ] TLS 1.2+ required
- [ ] Security headers configured (CSP, HSTS, etc.)
- [ ] Secrets rotated regularly (90-day maximum)

### Monitoring

- [ ] Alerting configured for unusual API usage patterns
- [ ] Failed authentication attempts logged
- [ ] API key usage audited
- [ ] Incident response plan documented

---

## Incident Response

### If Your API Key Is Compromised

**Immediate Actions (within 15 minutes):**

1. **Revoke the compromised key** in the ZeroDB dashboard immediately
2. **Generate a new API key**
3. **Update your backend** environment variables with the new key
4. **Restart your application** to pick up the new key

**Investigation (within 24 hours):**

5. **Review access logs** for unauthorized activity
6. **Check data integrity** - look for unexpected modifications
7. **Identify the leak source** - git history, logs, error messages
8. **Document the timeline** of the incident

**Remediation (within 48 hours):**

9. **Notify affected users** if their data may have been accessed
10. **Report to compliance** team for regulatory requirements
11. **Implement additional controls** to prevent recurrence
12. **Update security documentation** with lessons learned

### Git History Cleanup

If you accidentally committed an API key:

```bash
# 1. Immediately revoke the key (do this FIRST)
# Go to ZeroDB dashboard and revoke

# 2. Remove from git history using BFG Repo-Cleaner
bfg --replace-text passwords.txt repo.git

# 3. Or use git-filter-branch (slower)
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch path/to/secret-file" \
  --prune-empty --tag-name-filter cat -- --all

# 4. Force push (coordinate with team first)
git push origin --force --all

# 5. All team members must re-clone
```

---

## Additional Resources

### Project Documentation

- [SECURITY.md](/SECURITY.md) - Main security policy
- [API Quick Reference](/docs/quick-reference/API_KEY_SAFETY_CHECKLIST.md) - Quick checklist

### External Resources

- [OWASP API Security Project](https://owasp.org/www-project-api-security/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [CWE-798: Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html)

### Tools for Secret Detection

- [git-secrets](https://github.com/awslabs/git-secrets) - Prevents committing secrets
- [truffleHog](https://github.com/trufflesecurity/trufflehog) - Scans git history
- [Gitleaks](https://github.com/gitleaks/gitleaks) - Fast secret scanner
- [detect-secrets](https://github.com/Yelp/detect-secrets) - Enterprise secret detection

---

**Remember:** Security is not optional. A single exposed API key can compromise your entire application and user data. When in doubt, assume the worst and implement the backend proxy pattern.
