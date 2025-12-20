# Phraze.so Integration Plan - Editor Service

**Document Created**: December 11, 2025
**Status**: Pending Confirmation with Management
**Author**: Development Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Requirements Overview](#requirements-overview)
3. [Architecture Transformation](#architecture-transformation)
4. [Components to Remove vs Keep](#components-to-remove-vs-keep)
5. [Database Schema Changes](#database-schema-changes)
6. [Implementation Plan](#implementation-plan)
7. [Code Examples](#code-examples)
8. [UI Theme Specifications](#ui-theme-specifications)
9. [Files to Delete/Modify](#files-to-deletemodify)
10. [Questions for Clarification](#questions-for-clarification)
11. [Implementation Order](#implementation-order)

---

## Executive Summary

### Context
- **phraze.so** is the company's main website/platform
- **editor.phraze.so** is where our video editor will be deployed as a subdomain
- **MetaFrazo** (current standalone editor) will become an embedded service within phraze.so

### Key Changes Required
1. **Remove direct authentication** - phraze.so handles user auth
2. **Remove credit/billing system** - phraze.so manages all billing
3. **Change media input** - Load from S3 URL parameter instead of file upload
4. **Rebrand UI** - Match phraze.so design system

---

## Requirements Overview

### Source Document
File: `/Users/zhuchen/Downloads/Editor req.docx`

### Requirement 1: Authentication and Access Validation

> The editor service must implement a specific validation mechanism instead of a traditional login process.

**Details:**
- **No Direct Login Required**: Users should not be prompted to log in directly to the editor service (editor.phraze.so)
- **Redirection and Query Parameter Validation**: Access validation requires:
  1. Request must be verifiably redirected from the main phraze.so domain
  2. Redirection URL must contain a valid S3 URL as a mandatory query parameter
- **Failure Behavior**: If validation fails, redirect to phraze.so

### Requirement 2: Credit and Billing System Management

> The editor service is not responsible for tracking or managing user credits or billing.

**Details:**
- **No Local Credit System**: The editor service must not implement its own credit or usage tracking system
- **External Credit Management**: All credit and billing logistics are exclusively handled by the phraze.so platform

### Requirement 3: Media Loading Mechanism

> The primary method for loading media will transition from local file upload to direct S3 link ingestion.

**Details:**
- **Redirection Flow**: phraze.so initiates editing by redirecting user to editor.phraze.so
- **S3 URL Transmission**: Redirection includes secure S3 URL in query parameters
- **Mandatory S3 Link Usage**: Editor must bypass standard file upload interface and use provided S3 link directly
- **Return Format**: Pending further discussion (to be provided later)

### Requirement 4: User Interface (UI) and Design

> The UI must adhere strictly to external design specifications.

**Details:**
- **UI Reference Guide**: https://docs.google.com/document/d/e/2PACX-1vTGGbVVWOzBsXpsKUeiNbgQyBlYt2U5dlyxm4isb23esVV8MWj5L71CSHVwgiwtdoHbCs6DCDfSz27U/pub
- **Consistency**: Editor service must follow guidelines for consistent look and feel with main service

---

## Architecture Transformation

### Current State (Standalone MetaFrazo)

```
┌─────────────────────────────────────────────────────────┐
│                    MetaFrazo Platform                    │
├─────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐  │
│  │  Auth   │  │ Credits │  │ Upload  │  │  Editor   │  │
│  │ System  │  │ System  │  │   UI    │  │   Core    │  │
│  └─────────┘  └─────────┘  └─────────┘  └───────────┘  │
│       ↓            ↓            ↓            ↓          │
│  ┌──────────────────────────────────────────────────┐  │
│  │              PostgreSQL (Full Schema)             │  │
│  │  users, sessions, credits, subscriptions, jobs    │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Future State (Embedded in phraze.so)

```
┌─────────────────────────────────────────────────────────┐
│                      phraze.so                           │
│  (Main Platform - handles Auth, Credits, User Mgmt)     │
└────────────────────────┬────────────────────────────────┘
                         │ Redirect with S3 URL + Token
                         ▼
┌─────────────────────────────────────────────────────────┐
│               editor.phraze.so                           │
│            (Embedded Editor Service)                     │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │   Token     │  │  S3 Video   │  │    Editor       │  │
│  │ Validation  │  │   Loader    │  │     Core        │  │
│  │ (from phraze)│  │ (from URL)  │  │  (unchanged)    │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
│                          ↓                               │
│  ┌──────────────────────────────────────────────────┐   │
│  │         PostgreSQL (Simplified Schema)            │   │
│  │              video_jobs, files only               │   │
│  │         (NO users, credits, subscriptions)        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

```
User on phraze.so
       │
       │ 1. User selects video to edit
       ▼
phraze.so uploads video to S3
       │
       │ 2. Generate signed token + S3 URL
       ▼
Redirect to: editor.phraze.so/editor?video_url=<S3_URL>&token=<TOKEN>&user_id=<ID>
       │
       │ 3. Validate token and referrer
       ▼
Editor loads video from S3 URL (no upload UI)
       │
       │ 4. User edits video
       ▼
Processing via Sync.so / GhostCut APIs
       │
       │ 5. Return processed video (format TBD)
       ▼
Callback to phraze.so with result
```

---

## Components to Remove vs Keep

### Components to REMOVE

| Component | Location | Reason |
|-----------|----------|--------|
| User Registration | `backend/api/routes/auth/` | phraze.so handles users |
| User Login | `backend/api/routes/auth/` | phraze.so handles auth |
| Credit System | `backend/models/user.py` | phraze.so manages billing |
| Subscription Tiers | `backend/models/user.py` | phraze.so manages plans |
| Credit Transactions | `backend/models/user.py` | phraze.so tracks usage |
| Credit Packages | `backend/models/user.py` | phraze.so sells credits |
| File Upload UI | `frontend/src/components/VideoEditor/VideoUpload/` | S3 URL from phraze.so |
| Login Page | `frontend/src/pages/Auth/LoginPage.tsx` | No direct login |
| Register Page | `frontend/src/pages/Auth/RegisterPage.tsx` | No registration |
| Dashboard | `frontend/src/pages/dashboard/` | Not needed |
| Credits Page | `/credits` route | phraze.so manages |
| Sidebar Navigation | Complex navigation not needed | Simplified UI |

### Components to KEEP

| Component | Location | Reason |
|-----------|----------|--------|
| Video Editor Core | `frontend/src/components/VideoEditor/` | Core functionality |
| GhostCut Integration | `backend/api/routes/video_editors/ghostcut/` | Text removal |
| Sync.so Integration | `backend/api/routes/video_editors/sync/` | Lip-sync |
| Job Processing | `backend/api/routes/jobs/` | Track processing |
| S3 Service | `backend/services/s3/` | Store processed videos |
| Celery Workers | `backend/workers/` | Background processing |
| WebSocket Updates | `backend/api/websocket.py` | Real-time progress |

---

## Database Schema Changes

### Tables to DROP

```sql
-- Remove credit and user management tables
DROP TABLE IF EXISTS credit_transactions;
DROP TABLE IF EXISTS credit_packages;
DROP TABLE IF EXISTS subscription_tiers;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS api_keys;

-- Optionally drop or simplify users table
-- (depends on whether we need to track jobs by user)
```

### Simplified Schema

```sql
-- Simplified video_jobs table
CREATE TABLE video_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phraze_user_id VARCHAR(255) NOT NULL,  -- User ID from phraze.so
    phraze_session_id VARCHAR(255),         -- Session tracking

    -- Job details (keep existing)
    original_filename VARCHAR(500) NOT NULL,
    status VARCHAR(20) DEFAULT 'queued',
    progress_percentage INTEGER DEFAULT 0,
    progress_message TEXT,

    -- Processing config (keep existing)
    processing_config JSONB DEFAULT '{}',
    zhaoli_task_id VARCHAR(255),

    -- NO credit fields needed
    -- estimated_credits: REMOVED
    -- actual_credits_used: REMOVED

    -- File info (keep existing)
    input_url VARCHAR(1000),      -- S3 URL from phraze.so
    output_url VARCHAR(1000),     -- Processed video URL

    -- Timestamps (keep existing)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- Error handling (keep existing)
    error_message TEXT,
    error_code VARCHAR(50)
);

-- Keep files table for job artifacts
CREATE TABLE files (
    id SERIAL PRIMARY KEY,
    job_id UUID REFERENCES video_jobs(id) ON DELETE CASCADE,
    file_type VARCHAR(50) NOT NULL,
    s3_key VARCHAR(500),
    s3_url VARCHAR(1000),
    file_size_bytes BIGINT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Implementation Plan

### Phase 1: Backend Simplification

#### 1.1 Add Embedded Mode Configuration

**File**: `backend/config.py`

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Embedded Mode (for phraze.so integration)
    embedded_mode: bool = config("EMBEDDED_MODE", default=False, cast=bool)
    phraze_domain: str = config("PHRAZE_DOMAIN", default="phraze.so")
    phraze_secret_key: str = config("PHRAZE_SECRET_KEY", default="")
    allowed_s3_domains: List[str] = ["s3.amazonaws.com", "s3.us-east-2.amazonaws.com"]
```

#### 1.2 Create Phraze Token Validator

**New File**: `backend/auth/phraze_validator.py`

```python
import hmac
import hashlib
from fastapi import Request, HTTPException
from backend.config import settings

class PhrazeValidator:
    """Validates requests coming from phraze.so"""

    @staticmethod
    def validate_referrer(request: Request) -> bool:
        """Check request originates from phraze.so"""
        referrer = request.headers.get("referer", "")
        origin = request.headers.get("origin", "")
        return (
            settings.phraze_domain in referrer or
            settings.phraze_domain in origin
        )

    @staticmethod
    def validate_token(token: str, video_url: str) -> bool:
        """
        Validate token from phraze.so
        Token format TBD - implement based on phraze.so's specification
        """
        if not token or not settings.phraze_secret_key:
            return False

        # Example: HMAC validation (adjust based on actual format)
        expected = hmac.new(
            settings.phraze_secret_key.encode(),
            video_url.encode(),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(token, expected)

    @staticmethod
    def validate_s3_url(url: str) -> bool:
        """Ensure S3 URL is from allowed domains"""
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in settings.allowed_s3_domains)

    @staticmethod
    async def validate_request(
        request: Request,
        video_url: str,
        token: str
    ) -> dict:
        """Full validation of incoming request"""
        if not PhrazeValidator.validate_referrer(request):
            raise HTTPException(
                status_code=403,
                detail="Access denied: Invalid origin"
            )

        if not PhrazeValidator.validate_s3_url(video_url):
            raise HTTPException(
                status_code=400,
                detail="Invalid video URL"
            )

        if not PhrazeValidator.validate_token(token, video_url):
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token"
            )

        return {"valid": True}
```

#### 1.3 Create Embedded Editor Endpoints

**New File**: `backend/api/routes/embedded_editor.py`

```python
from fastapi import APIRouter, Request, Query, Body, HTTPException
from backend.auth.phraze_validator import PhrazeValidator
from backend.config import settings

router = APIRouter()

@router.get("/validate")
async def validate_access(
    request: Request,
    video_url: str = Query(..., description="S3 URL of video to edit"),
    token: str = Query(..., description="Auth token from phraze.so"),
    user_id: str = Query(None, description="User ID from phraze.so")
):
    """
    Validate access from phraze.so redirect
    Called when user lands on editor.phraze.so
    """
    await PhrazeValidator.validate_request(request, video_url, token)

    return {
        "valid": True,
        "video_url": video_url,
        "user_id": user_id,
        "message": "Access granted"
    }

@router.post("/process")
async def process_video(
    request: Request,
    video_url: str = Query(...),
    token: str = Query(...),
    user_id: str = Query(None),
    processing_config: dict = Body(default={})
):
    """
    Process video from phraze.so
    NO credit checking - phraze.so handles billing
    """
    await PhrazeValidator.validate_request(request, video_url, token)

    # Create job WITHOUT credit checks
    job = await create_job_without_credits(
        phraze_user_id=user_id,
        input_url=video_url,
        config=processing_config
    )

    # Start processing
    await start_processing(job.id)

    return {
        "job_id": str(job.id),
        "status": "processing",
        "message": "Video processing started"
    }
```

#### 1.4 Remove Credit Logic from Processing

**Modify**: `backend/api/routes/video_editors/sync/sync_api_original.py`

```python
@router.post("/sync-process")
async def sync_process(
    # ... existing params ...
):
    # REMOVE these lines:
    # if not user.has_sufficient_credits(estimated_credits):
    #     raise HTTPException(status_code=402, detail="Insufficient credits")
    # user.deduct_credits(estimated_credits)

    # Add conditional logic:
    if not settings.embedded_mode:
        # Standalone mode: Check credits (if keeping standalone)
        pass
    # Embedded mode: No credit checks

    # KEEP processing logic unchanged
    # ...
```

### Phase 2: Frontend Simplification

#### 2.1 Create Embedded Editor Page

**New File**: `frontend/src/pages/EmbeddedEditor.tsx`

```typescript
import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import VideoEditor from '../components/VideoEditor/VideoEditor';
import LoadingScreen from '../components/Common/LoadingScreen';
import { validateAccess } from '../services/api';

const EmbeddedEditor: React.FC = () => {
  const [searchParams] = useSearchParams();
  const [isValid, setIsValid] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);

  const videoUrl = searchParams.get('video_url');
  const token = searchParams.get('token');
  const userId = searchParams.get('user_id');

  useEffect(() => {
    const validate = async () => {
      if (!videoUrl || !token) {
        // Missing required params - redirect to phraze.so
        window.location.href = 'https://phraze.so';
        return;
      }

      try {
        await validateAccess(videoUrl, token, userId);
        setIsValid(true);
      } catch (err) {
        setError('Access denied. Redirecting...');
        setTimeout(() => {
          window.location.href = 'https://phraze.so';
        }, 2000);
      }
    };

    validate();
  }, [videoUrl, token, userId]);

  if (isValid === null) {
    return <LoadingScreen message="Validating access..." />;
  }

  if (error) {
    return <LoadingScreen message={error} />;
  }

  // Render editor directly with video URL - NO upload UI
  return (
    <VideoEditor
      videoSource={videoUrl!}
      embeddedMode={true}
      userId={userId}
    />
  );
};

export default EmbeddedEditor;
```

#### 2.2 Simplified App Router

**Modify**: `frontend/src/App.tsx` (Embedded Mode Version)

```typescript
import React, { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './contexts/ThemeContext';
import EmbeddedEditor from './pages/EmbeddedEditor';
import LoadingScreen from './components/Common/LoadingScreen';

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <Routes>
        {/* Main editor route - requires video_url and token params */}
        <Route path="/editor" element={<EmbeddedEditor />} />

        {/* Pro editor route */}
        <Route path="/editor/pro" element={<EmbeddedEditor pro={true} />} />

        {/* Redirect all other routes to phraze.so */}
        <Route path="*" element={<RedirectToPhraze />} />
      </Routes>
    </ThemeProvider>
  );
};

const RedirectToPhraze: React.FC = () => {
  useEffect(() => {
    window.location.href = 'https://phraze.so';
  }, []);
  return <LoadingScreen message="Redirecting to Phraze..." />;
};

export default App;
```

### Phase 3: Apply Phraze.so UI Theme

#### 3.1 Phraze Theme Configuration

**New File**: `frontend/src/theme/phrazeTheme.ts`

```typescript
import { createTheme } from '@mui/material/styles';

export const phrazeTheme = createTheme({
  palette: {
    primary: {
      main: '#0A47F2',      // Phraze Primary Blue
      light: '#2563EB',
      dark: '#1D4ED8',
    },
    secondary: {
      main: '#D763FF',      // Accent Purple
      light: '#8A88FF',
    },
    background: {
      default: '#F0F3F6',   // Light Background
      paper: '#FFFFFF',
    },
    text: {
      primary: '#0E0E0C',
      secondary: '#6B7280',
    },
    success: { main: '#22C55E' },  // Completed status
    error: { main: '#EF4444' },    // Needs revision
    warning: { main: '#F97316' },  // Assigned
    info: { main: '#3B82F6' },     // Active/translating
  },
  typography: {
    fontFamily: '"Inter", "Geist Sans", -apple-system, sans-serif',
    h1: {
      fontFamily: '"Satoshi", sans-serif',
      fontWeight: 700,
      fontSize: '2.5rem',
    },
    h2: {
      fontFamily: '"Satoshi", sans-serif',
      fontWeight: 600,
      fontSize: '2rem',
    },
    h3: {
      fontFamily: '"Satoshi", sans-serif',
      fontWeight: 600,
      fontSize: '1.5rem',
    },
    button: {
      fontFamily: '"Satoshi", sans-serif',
      fontWeight: 500,
      textTransform: 'none',
    },
    body1: {
      fontFamily: '"Inter", sans-serif',
      fontSize: '1rem',
    },
    body2: {
      fontFamily: '"Inter", sans-serif',
      fontSize: '0.875rem',
    },
  },
  shape: {
    borderRadius: 12,  // Default rounded-xl
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 24,  // rounded-3xl
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          border: 'none',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        contained: {
          borderRadius: 12,
          padding: '12px 24px',
          boxShadow: '0px 0px 25px 10px rgba(50, 119, 248, 0.15)',
          transition: 'all 0.2s ease',
          '&:hover': {
            boxShadow: '0px 0px 30px 12px rgba(50, 119, 248, 0.25)',
          },
        },
        outlined: {
          borderRadius: 12,
          padding: '12px 24px',
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            borderColor: '#E5E7EB',
            '&:focus-within': {
              borderColor: '#0A47F2',
            },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
});

// Status badge colors
export const statusColors = {
  completed: '#22C55E',
  failed: '#EF4444',
  processing: '#3B82F6',
  queued: '#F97316',
  canceled: '#6B7280',
};
```

---

## UI Theme Specifications

### Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Primary Blue | `#0A47F2` | CTAs, brand accents, links |
| Button Blue | `#2563EB` | Button backgrounds |
| Button Hover | `#1D4ED8` | Button hover state |
| Dark Background | `#0E0E0C` | Footers, dark sections |
| Light Background | `#F0F3F6` | Page backgrounds |
| Accent Purple | `#D763FF` | Gradients, highlights |
| Secondary Purple | `#8A88FF` | Secondary accents |

### Status Colors

| Status | Color | Hex |
|--------|-------|-----|
| Completed | Green | `#22C55E` |
| Failed/Needs Revision | Red | `#EF4444` |
| Active/Processing | Blue | `#3B82F6` |
| Queued/Assigned | Orange | `#F97316` |
| Syncing | Purple | `#8A88FF` |

### Typography

| Element | Font | Weight | Size |
|---------|------|--------|------|
| Headlines | Satoshi | Bold (700) | 56px (landing), 40px (h1), 32px (h2) |
| CTAs/Buttons | Satoshi | Medium (500) | 16px |
| Dashboard UI | Inter/Geist Sans | Regular (400) | 14-16px |
| IDs/Codes | Geist Mono | Regular (400) | 12-14px |

### Component Specifications

| Component | Border Radius | Shadow | Padding |
|-----------|---------------|--------|---------|
| Cards | 24px (rounded-3xl) | `0 1px 3px rgba(0,0,0,0.1)` | 24px |
| Buttons | 12px (rounded-xl) | `0px 0px 25px 10px rgba(50, 119, 248, 0.15)` | 16px 24px |
| Inputs | 12px | None | 12px 16px |
| Badges/Chips | 8px | None | 4px 12px |

---

## Files to Delete/Modify

### Backend Files to DELETE

```
backend/api/routes/auth/           # Most files - keep only token validation
  - auth_handlers.py               # DELETE (user registration/login)
  - password_handlers.py           # DELETE (password reset)

backend/models/user.py             # MODIFY - Remove these classes:
  - class SubscriptionTier         # DELETE
  - class CreditTransaction        # DELETE
  - class CreditPackage            # DELETE
  - class APIKey                   # DELETE (or keep if needed)
  - class UserSession              # DELETE
```

### Frontend Files to DELETE

```
frontend/src/pages/Auth/
  - LoginPage.tsx                  # DELETE
  - RegisterPage.tsx               # DELETE

frontend/src/pages/dashboard/      # DELETE entire folder
  - DashboardPage/
  - HomePage.tsx

frontend/src/pages/admin/
  - SettingsPage.tsx               # DELETE or heavily modify (remove credits)

frontend/src/components/Layout/
  - Sidebar.tsx                    # DELETE or heavily simplify

frontend/src/contexts/
  - AuthContext.tsx                # REPLACE with PhrazeContext.tsx
```

### Files to MODIFY

```
backend/config.py                  # Add embedded mode settings
backend/api/main.py                # Add embedded routes, modify CORS
backend/api/routes/video_editors/* # Remove credit checks

frontend/src/App.tsx               # Simplify routing
frontend/src/services/api.ts       # Add validation endpoints
frontend/src/contexts/ThemeContext.tsx  # Use phrazeTheme
```

---

## Questions for Clarification

### Critical Questions (Must Answer Before Implementation)

1. **Token Format and Validation**
   - What format will phraze.so use for the authentication token?
   - Options: JWT, HMAC signature, API key + timestamp
   - Should we validate locally or call phraze.so API to verify?
   - What is the token expiration policy?

2. **User Identification**
   - Should we track jobs by phraze.so user ID?
   - What user identifier will be passed in the URL?
   - Do we need to store any user information locally?

3. **Return Format (Pending)**
   - How should we return the edited video to phraze.so?
   - Webhook callback URL?
   - Query parameter redirect?
   - What data should be included in the callback?

4. **Error Handling**
   - How should we notify phraze.so if processing fails?
   - Should there be a callback for errors?
   - What error information should be provided?

### Infrastructure Questions

5. **Domain Setup**
   - Who handles DNS configuration for editor.phraze.so?
   - Who provides SSL certificate for the subdomain?

6. **Deployment**
   - Same Railway account as current deployment?
   - Or separate infrastructure for editor.phraze.so?

7. **Development Mode**
   - Should we keep standalone mode for development/testing?
   - Or fully convert to embedded-only service?

### S3 Access Questions

8. **S3 URL Format**
   - Are the S3 URLs pre-signed with expiration?
   - What is the expiration time for pre-signed URLs?
   - Do we need cross-account S3 access?

9. **Output Storage**
   - Where should processed videos be stored?
   - Our S3 bucket or phraze.so's S3 bucket?
   - How long should outputs be retained?

---

## Implementation Order

### Recommended Sequence

| Order | Task | Priority | Risk | Effort |
|-------|------|----------|------|--------|
| 1 | Add `EMBEDDED_MODE` config flag | High | Low | 1 hour |
| 2 | Create PhrazeValidator middleware | High | Medium | 4 hours |
| 3 | Create `/embedded/validate` endpoint | High | Low | 2 hours |
| 4 | Modify processing to skip credit checks | High | Low | 2 hours |
| 5 | Create EmbeddedEditor frontend page | High | Medium | 4 hours |
| 6 | Remove Login/Register pages | Medium | Low | 1 hour |
| 7 | Remove Dashboard page | Medium | Low | 1 hour |
| 8 | Simplify/remove Sidebar | Medium | Low | 2 hours |
| 9 | Apply Phraze UI theme | Medium | Medium | 8 hours |
| 10 | Database schema migration | Low | High | 4 hours |

### Estimated Total Effort

- **Backend Changes**: ~12 hours
- **Frontend Changes**: ~16 hours
- **UI Theming**: ~8 hours
- **Testing & QA**: ~8 hours
- **Total**: ~44 hours (approximately 1-2 weeks)

---

## Environment Variables (New)

```bash
# Embedded Mode Configuration
EMBEDDED_MODE=true
PHRAZE_DOMAIN=phraze.so
PHRAZE_SECRET_KEY=your-shared-secret-with-phraze
PHRAZE_CALLBACK_URL=https://phraze.so/api/editor/callback

# Allowed S3 Domains (comma-separated)
ALLOWED_S3_DOMAINS=s3.amazonaws.com,s3.us-east-2.amazonaws.com

# CORS - Update for phraze.so
CORS_ORIGINS=https://phraze.so,https://editor.phraze.so
```

---

## Summary

| Requirement | Implementation Approach |
|-------------|------------------------|
| **No Direct Login** | Remove auth pages, validate via token from phraze.so, redirect invalid requests |
| **No Credit System** | Remove all credit tables/logic, skip billing checks in processing |
| **S3 URL Loading** | Parse `video_url` from query params, skip upload UI, load directly |
| **Phraze UI** | Apply new theme with #0A47F2 blue, rounded corners, Satoshi/Inter fonts |

The editor becomes a **focused, embedded service** that only handles video editing. All user management and billing remains on phraze.so.

---

## Next Steps

1. **Review this document** with your boss
2. **Clarify the questions** listed above (especially token format and return format)
3. **Confirm implementation timeline** and priorities
4. **Begin Phase 1** implementation (backend changes)

---

*Document will be updated as clarifications are received.*
