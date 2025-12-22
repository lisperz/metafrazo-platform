# Railway Environment Variables Configuration

This document lists all environment variables needed for the Metafrazo platform deployment on Railway.

---

## Backend Service Environment Variables

### Required Variables (Must be set)

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/dbname` |
| `REDIS_URL` | Redis connection string | `redis://default:pass@host:6379` |
| `SECRET_KEY` | JWT signing secret (min 32 chars) | `your-secure-random-secret-key-min-32-chars` |
| `AWS_ACCESS_KEY_ID` | AWS S3 access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS S3 secret key | `...` |
| `AWS_S3_BUCKET` | S3 bucket name | `taylorswiftnyu` |
| `AWS_REGION` | AWS region | `us-east-2` |
| `SYNC_API_KEY` | Sync.so API key for lip-sync | `...` |
| `GHOSTCUT_APP_KEY` | GhostCut API key | `...` |
| `GHOSTCUT_APP_SECRET` | GhostCut API secret | `...` |
| `GHOSTCUT_UID` | GhostCut user ID | `...` |
| `GHOSTCUT_API_KEY` | GhostCut API key (alias) | `...` |

### Server Configuration

| Variable | Description | Default | Recommended for Railway |
|----------|-------------|---------|------------------------|
| `ENVIRONMENT` | Environment mode | `development` | `production` |
| `PORT` | Server port | `8000` | `8000` (Railway sets this) |
| `HOST` | Server host | `0.0.0.0` | `0.0.0.0` |
| `DEBUG` | Debug mode | `false` | `false` |

### CORS and Frontend

| Variable | Description | Example |
|----------|-------------|---------|
| `FRONTEND_URL` | Frontend URL | `https://your-frontend.railway.app` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | `https://your-frontend.railway.app,https://phraze.so` |
| `API_BASE_URL` | Backend API URL | `https://your-backend.railway.app` |

### Phraze.so Integration (Required for Embedded Editor)

| Variable | Description | Notes |
|----------|-------------|-------|
| `PHRAZE_PUBLIC_KEY` | RSA public key from Phraze.so | Get from Phraze.so developer after sharing integration guide |
| `CALLBACK_HMAC_SECRET` | HMAC secret for callback verification | Generate and share with Phraze.so |
| `PHRAZE_DOMAIN` | Phraze domain | `phraze.so` |
| `ALLOWED_S3_DOMAINS` | Allowed S3 domains for video URLs | `s3.amazonaws.com,s3.us-east-2.amazonaws.com` |

### Celery/Redis (Usually same as REDIS_URL)

| Variable | Description | Notes |
|----------|-------------|-------|
| `CELERY_BROKER_URL` | Celery broker URL | Usually same as `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | Celery result backend | Usually same as `REDIS_URL` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_UPLOAD_SIZE_MB` | Max upload size | `1000` |
| `DEFAULT_PROCESSING_TIMEOUT_MINUTES` | Processing timeout | `180` |
| `MAX_CONCURRENT_JOBS_PER_USER` | Max concurrent jobs | `3` |

---

## Frontend Service Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `REACT_APP_API_URL` | Backend API URL | `https://your-backend.railway.app` |
| `NODE_ENV` | Node environment | `production` |

---

## Worker Service Environment Variables

Worker services need the same variables as Backend, plus:

| Variable | Description | Notes |
|----------|-------------|-------|
| `CELERY_BROKER_URL` | Redis URL for Celery | Same as `REDIS_URL` |
| `CELERY_RESULT_BACKEND` | Redis URL for results | Same as `REDIS_URL` |

---

## Example .env for Railway Backend

```env
# Required
DATABASE_URL=postgresql://user:password@host:5432/database
REDIS_URL=redis://default:password@host:6379
SECRET_KEY=your-super-secret-key-at-least-32-characters-long

# AWS
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=taylorswiftnyu
AWS_REGION=us-east-2

# APIs
SYNC_API_KEY=your-sync-api-key
GHOSTCUT_APP_KEY=your-ghostcut-app-key
GHOSTCUT_APP_SECRET=your-ghostcut-app-secret
GHOSTCUT_UID=your-ghostcut-uid
GHOSTCUT_API_KEY=your-ghostcut-api-key
GHOSTCUT_API_URL=https://api.ghostcut.com
SYNC_API_URL=https://api.sync.so

# Server
ENVIRONMENT=production
PORT=8000
HOST=0.0.0.0
DEBUG=false

# CORS
FRONTEND_URL=https://your-frontend.railway.app
CORS_ORIGINS=https://your-frontend.railway.app,https://phraze.so
API_BASE_URL=https://your-backend.railway.app

# Phraze Integration
PHRAZE_DOMAIN=phraze.so
PHRAZE_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\nMIIBI...\n-----END PUBLIC KEY-----
CALLBACK_HMAC_SECRET=your-shared-hmac-secret
ALLOWED_S3_DOMAINS=s3.amazonaws.com,s3.us-east-2.amazonaws.com

# Celery
CELERY_BROKER_URL=redis://default:password@host:6379
CELERY_RESULT_BACKEND=redis://default:password@host:6379

# Logging
LOG_LEVEL=INFO
```

---

## Generating Secrets

### Generate a secure SECRET_KEY:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Generate CALLBACK_HMAC_SECRET:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### PHRAZE_PUBLIC_KEY format:

When pasting RSA public key in Railway, replace newlines with `\n`:

Original:
```
-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
...
-----END PUBLIC KEY-----
```

Railway format:
```
-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...\n...\n-----END PUBLIC KEY-----
```

---

## Service Architecture on Railway

```
┌─────────────────────────────────────────────────────────────┐
│                     Railway Project                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │  PostgreSQL │  │    Redis    │  │   Frontend (React)  │  │
│  │  (Database) │  │  (Cache)    │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         └────────┬───────┘                     │             │
│                  │                             │             │
│         ┌────────▼────────┐                    │             │
│         │     Backend     │◄───────────────────┘             │
│         │    (FastAPI)    │                                  │
│         └────────┬────────┘                                  │
│                  │                                           │
│         ┌────────▼────────┐                                  │
│         │     Worker      │                                  │
│         │    (Celery)     │                                  │
│         └─────────────────┘                                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Verification

After deployment, verify these endpoints:

1. **Backend Health Check:**
   ```
   curl https://your-backend.railway.app/health
   ```

2. **Mock Token Page (for testing):**
   ```
   https://your-backend.railway.app/api/v1/embedded/mock/test-page
   ```

3. **Frontend:**
   ```
   https://your-frontend.railway.app
   ```

---

*Last updated: December 21, 2024*
