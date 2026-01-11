# API Key Safety Checklist

**Quick Reference for Developers**
**Last Updated:** 2026-01-10

---

## CRITICAL RULE

> **NEVER expose API keys in client-side code (browsers, mobile apps, desktop apps).**
>
> See [API_KEY_SECURITY.md](/docs/api/API_KEY_SECURITY.md) for detailed guidance.
> See [SECURITY.md](/SECURITY.md) for the full security policy.

---

## Pre-Development Checklist

- [ ] Understand the backend proxy pattern
- [ ] Set up environment variable management
- [ ] Configure `.gitignore` to exclude secrets
- [ ] Review OWASP API Security guidelines

---

## Code Review Checklist

### WRONG Patterns - Reject Immediately

| Pattern | Example | Risk |
|---------|---------|------|
| Hardcoded API key | `const API_KEY = 'zerodb_sk_...'` | CRITICAL |
| Frontend env var | `process.env.REACT_APP_API_KEY` | CRITICAL |
| HTML/DOM exposure | `<meta data-api-key="...">` | CRITICAL |
| Base64 "encoding" | `atob('encoded_key')` | CRITICAL |
| Mobile hardcoding | `let apiKey = "zerodb_sk_..."` | CRITICAL |
| Config file in repo | `config.json` with secrets | CRITICAL |

### RIGHT Patterns - Approve

| Pattern | Example | Status |
|---------|---------|--------|
| Backend proxy | Client -> Your Server -> ZeroDB | SECURE |
| Environment variables | `os.getenv('ZERODB_API_KEY')` | SECURE |
| Secret manager | AWS/GCP/Azure secret services | SECURE |
| User JWT for client auth | `Authorization: Bearer <user_token>` | SECURE |

---

## Pre-Deployment Checklist

### API Key Protection

- [ ] No API keys in frontend code
- [ ] No API keys in mobile app code
- [ ] No API keys in version control
- [ ] `.env` files in `.gitignore`
- [ ] Secrets stored in environment or secret manager

### Backend Proxy

- [ ] All ZeroDB calls go through your backend
- [ ] User authentication implemented (JWT/OAuth)
- [ ] Request validation in place
- [ ] Error messages don't leak secrets

### Infrastructure

- [ ] HTTPS enforced everywhere
- [ ] Rate limiting configured
- [ ] CORS restricted to your domains
- [ ] Audit logging enabled

### Monitoring

- [ ] Unusual usage alerts configured
- [ ] Failed auth attempts logged
- [ ] Incident response plan ready

---

## Quick Reference: Secure Architecture

```
+------------+       +---------------+       +--------------+
|   Client   | JWT   | Your Backend  | API   |   ZeroDB     |
|   (React,  |------>| (FastAPI,     | Key   |   API        |
|   iOS,     |       |  Express)     |------>|              |
|   Android) |       |               |       |              |
+------------+       +---------------+       +--------------+
      |                     |                       |
  User Token           API Key                 Validated
  (safe to use)        (NEVER exposed)         Request
```

---

## Emergency: Key Compromised

1. **Revoke key immediately** in ZeroDB dashboard
2. **Generate new key**
3. **Update backend** environment
4. **Restart application**
5. **Review logs** for unauthorized access
6. **Notify team** and document incident

---

## Common Questions

**Q: Can I use the API key in React with environment variables?**
A: NO. `REACT_APP_*` variables are embedded in the bundle and visible to users.

**Q: Is Base64 encoding my key secure?**
A: NO. Base64 is encoding, not encryption. It's trivially reversible.

**Q: Can I hide the key in a compiled mobile app?**
A: NO. App binaries can be decompiled. Use a backend proxy.

**Q: What if I need real-time features in the browser?**
A: Use your backend as a WebSocket proxy. Never connect directly with API keys.

---

## Links

- Full Guide: [API_KEY_SECURITY.md](/docs/api/API_KEY_SECURITY.md)
- Security Policy: [SECURITY.md](/SECURITY.md)
- OWASP: [API Security Top 10](https://owasp.org/www-project-api-security/)

---

**When in doubt: Use the backend proxy pattern. API keys belong on servers, not clients.**
