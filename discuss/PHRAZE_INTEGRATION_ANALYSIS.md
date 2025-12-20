# Phraze.so Integration Analysis & Implementation Review

**Document Created**: December 16, 2025
**Status**: Pre-Implementation Analysis
**Purpose**: Identify gaps, concerns, and recommendations before implementation

---

## Table of Contents

1. [Summary of Confirmed Details](#summary-of-confirmed-details)
2. [Architecture Insight](#architecture-insight)
3. [Potential Gaps & Concerns](#potential-gaps--concerns)
4. [Suggested Questions for Developer](#suggested-questions-for-developer)
5. [Recommended Architecture](#recommended-architecture)
6. [Updated Task List](#updated-task-list)
7. [Questions to Confirm Before Starting](#questions-to-confirm-before-starting)

---

## Summary of Confirmed Details

Based on communication with the developer:

| Question | Developer Answer |
|----------|------------------|
| Token Format | JWT (similar to translation/QA flow) |
| User/Job Tracking | Both `userId` and `jobId` in token, job entry exists before redirect |
| Error Handling | Use same DB entry (created before redirect) |
| DNS/SSL | Managed by Cloudflare |

### Original Questions Asked

1. How will phraze.so generate the token? (JWT?)
2. User Identification: Should we track jobs by phraze.so user ID, or is it stateless?
3. Error Handling: If processing fails, how should we notify phraze.so?
4. Handle DNS/SSL for editor.phraze.so?

### Developer Responses

1. Editing Jobs will be similar to translation and QA but redirected to editor instead after db entry. Tokens will be JWT and we can sign it with whatever details required by the editor dashboard both for editing and tracking.
2. userId and jobId can be used for tracking
3. We can use the same entry in db which was done just before redirecting
4. It will be managed by Cloudflare

---

## Architecture Insight

The developer mentioned: **"We can use the same entry in db which was done just before redirecting"**

This implies one of two scenarios:

### Scenario A: Shared Database Access

```
phraze.so creates job → Redirect to editor → Editor updates SAME DB row
```

- Editor directly connects to phraze.so's database
- Simpler, but tighter coupling
- Security concerns with shared DB credentials

### Scenario B: API Callback (More Likely)

```
phraze.so creates job → Redirect to editor → Editor calls phraze.so API to update job
```

- Editor has its own processing, reports back via webhook/API
- More decoupled, standard microservice pattern
- Better security isolation

**Action Required**: Clarify with developer which approach to use.

---

## Potential Gaps & Concerns

### 1. JWT Secret Key Sharing

The developer confirmed JWT tokens, but didn't specify:

| Item | Question to Ask |
|------|-----------------|
| Algorithm | HS256 (symmetric) or RS256 (asymmetric)? |
| Secret Key | How will editor receive the signing secret/public key? |
| Key Rotation | How to handle key updates without downtime? |

**Recommendation**: Request RS256 with public key - more secure, no shared secret needed.

#### JWT Algorithm Comparison

| Algorithm | How It Works | Pros | Cons |
|-----------|--------------|------|------|
| HS256 | Shared secret key | Simple setup | Secret must be shared securely |
| RS256 | Public/private key pair | Editor only needs public key | Slightly more complex setup |

---

### 2. Callback/Completion Flow

When video processing completes, how does phraze.so know?

| Option | Pros | Cons |
|--------|------|------|
| **Webhook callback** (Yes,this way) | Decoupled, reliable | Needs phraze.so endpoint |
| **Direct DB update** no | Simple | Tight coupling, security risk |
| **Redirect with status** no | User sees result | Doesn't work for background processing |
| **Polling from phraze.so** no | Simple for phraze.so | Inefficient, delayed updates |

**Recommended Flow**:

```
Editor completes → POST to phraze.so/api/editor/callback
                   with {jobId, status, outputUrl}
                → Redirect user back to phraze.so/jobs/{jobId}  //save final vid in s3 and add that link to the same record that we created when starting the editing job
```

---

### 3. S3 Access & Output Storage

| Question | Impact |
|----------|--------|
| Whose S3 bucket for input videos? | Need cross-account access or pre-signed URLs |
| Where to store processed output? | Our bucket or phraze.so's? |
| URL expiration policy? | If pre-signed, how long valid? |
| Large file handling? | Multi-part upload for processed videos? |

#### S3 Access Options

```
Option 1: Pre-signed URLs (Recommended)
─────────────────────────────────────────
phraze.so generates pre-signed URL → Include in JWT → Editor downloads directly

Option 2: Cross-account Access
─────────────────────────────────────────
phraze.so grants bucket access to editor's AWS role → Editor accesses directly

Option 3: Proxy through phraze.so API
─────────────────────────────────────────
Editor requests file via phraze.so API → phraze.so streams from S3
```

---

### 4. Session & State Management

| Scenario | What Happens? |
|----------|---------------|
| User refreshes editor page | Token still valid? Can resume? |
| User closes browser mid-processing | Background job continues? How to resume viewing? |
| Token expires during editing | Re-auth flow? Or extend session? |
| User opens multiple tabs | Same job or new job per tab? |

#### Proposed Session Handling

```javascript
// On page load
1. Extract JWT from URL query parameter
2. Validate JWT (check signature, expiration)
3. If valid: Store in sessionStorage, load video
4. If invalid: Redirect to phraze.so with error

// On page refresh
1. Check sessionStorage for cached JWT
2. Re-validate (may have expired)
3. If still valid: Continue editing
4. If expired: Redirect to phraze.so for new token
```

---

### 5. Error Scenarios Not Covered

```
┌─────────────────────────────────────────────────────────────────┐
│                    Error Handling Matrix                         │
├──────────────────────┬──────────────────────────────────────────┤
│ Error Type           │ Proposed Handling                        │
├──────────────────────┼──────────────────────────────────────────┤
│ Invalid/expired JWT  │ Redirect to phraze.so with error code    │
│ Video not found (S3) │ Show error, update job status to failed  │
│ Sync.so API failure  │ Retry 3x, then mark failed, notify       │
│ GhostCut API failure │ Retry 3x, then mark failed, notify       │
│ Network disconnect   │ Auto-retry with exponential backoff      │
│ User cancels mid-job │ Cancel Celery task, update job status    │
│ S3 upload failure    │ Retry 3x, then mark failed, notify       │
│ Callback failure     │ Retry with exponential backoff, log      │
└──────────────────────┴──────────────────────────────────────────┘
```

#### Error Response Format

```json
{
  "error_code": "TOKEN_EXPIRED",
  "message": "Your session has expired. Please return to phraze.so to continue.",
  "redirect_url": "https://phraze.so/dashboard?error=session_expired",
  "job_id": "uuid-here",
  "timestamp": "2025-12-16T10:30:00Z"
}
```

---

### 6. Missing from Current Task List

| Missing Item | Why It Matters |
|--------------|----------------|
| **Callback endpoint spec** | How editor notifies phraze.so of completion |
| **Output URL generation** | Who generates download link, where stored |
| **Job status sync mechanism** | Real-time updates or batch? |
| **Token refresh strategy** | Long editing sessions may exceed token expiry |
| **Fallback/error redirect** | Where to send user on failures |
| **Progress reporting** | Should editor send progress % to phraze.so? |
| **Return URL configuration** | Where to redirect user after completion |
| **Timeout handling** | What if processing takes too long? |
| **Concurrent session handling** | Multiple edits of same video? |

---

## Suggested Questions for Developer

### Critical Questions (Block Implementation)

``` 
1. **Database Access**:
   Will editor have direct DB access, or should we call an API
   endpoint on phraze.so to update job status?

2. **JWT Details**:
   - What algorithm (HS256/RS256)?
   - How will we receive the secret/public key?
   - What claims will be in the token? (userId, jobId, s3Url, etc.)
   - What is the token expiration time?

3. **Callback Endpoint**:
   - Should editor call a phraze.so API when processing completes?
   - What's the endpoint URL format?
   - What payload is expected?
   - How to authenticate the callback?

4. **S3 Configuration**:
   - Are input URLs pre-signed? What's the expiration?
   - Where should we store processed output files?
   - Same bucket or our own?
   - Who generates the final download URL?

5. **Return Flow**:
   - After editing completes, where do we redirect the user?
   - What query parameters should we include?
   - What if user wants to cancel and go back? they can just use the "go back" button in editor to go back and cancel.
```

### Nice-to-Have Questions

```markdown
6. **Progress Updates**:
   - Should we send real-time progress to phraze.so? no
   - WebSocket, SSE, or polling?

7. **Retry Policy**:
   - If callback fails, how many retries?
   - Should we queue failed callbacks?

8. **Logging & Monitoring**:
   - Shared request IDs for tracing?
   - Log forwarding to phraze.so?

9. **Rate Limiting**:
   - Any limits on editor API calls?
   - Concurrent job limits per user?
```

---

## Recommended Architecture

### High-Level Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           phraze.so                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────┐   │
│  │ User clicks │───▶│ Create Job  │───▶│ Generate JWT                │   │
│  │ "Edit Video"│    │ in DB       │    │ {userId, jobId, s3Url, exp} │   │
│  └─────────────┘    └─────────────┘    └──────────────┬──────────────┘   │
│                                                        │                  │
│  ┌─────────────────────────────────────────────────────┼────────────────┐ │
│  │ POST /api/editor/callback                           │                │ │
│  │ Receives: {jobId, status, outputUrl, error?}        │                │ │
│  │ Updates job in DB, notifies user                    │                │ │
│  └─────────────────────────────────────────────────────┼────────────────┘ │
└────────────────────────────────────────────────────────┼──────────────────┘
                                                         │
                    Redirect: editor.phraze.so/editor?token=<JWT>
                                                         │
                                                         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        editor.phraze.so                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────┐   │
│  │ Validate    │───▶│ Decode JWT  │───▶│ Load video from S3 URL      │   │
│  │ JWT Token   │    │ Extract IDs │    │ (no upload UI needed)       │   │
│  └─────────────┘    └─────────────┘    └──────────────┬──────────────┘   │
│         │                                              │                  │
│         │ Invalid                                      ▼                  │
│         ▼                              ┌─────────────────────────────┐   │
│  Redirect to                           │ User edits video            │   │
│  phraze.so                             │ (text removal, lip-sync)    │   │
│                                        └──────────────┬──────────────┘   │
│                                                       │                  │
│                                                       ▼                  │
│                                        ┌─────────────────────────────┐   │
│                                        │ Process via Celery          │   │
│                                        │ Call Sync.so / GhostCut     │   │
│                                        └──────────────┬──────────────┘   │
│                                                       │                  │
│                                                       ▼                  │
│                                        ┌─────────────────────────────┐   │
│                                        │ Upload result to S3         │   │
│                                        │ Call phraze.so callback     │   │
│                                        │ Redirect user back          │   │
│                                        └─────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────┘
```

### JWT Token Structure (Proposed)

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT"
  },
  "payload": {
    "sub": "user-uuid-here",
    "job_id": "job-uuid-here",
    "video_url": "https://s3.amazonaws.com/bucket/video.mp4",
    "callback_url": "https://phraze.so/api/editor/callback",
    "return_url": "https://phraze.so/jobs/{job_id}",
    "permissions": ["edit", "process"],
    "iat": 1702720000,
    "exp": 1702723600
  }
}
```

### API Endpoints (Editor Side)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v1/embedded/validate` | Validate JWT, return decoded claims |
| POST | `/api/v1/embedded/process` | Start video processing |
| GET | `/api/v1/embedded/status/{job_id}` | Get processing status |
| POST | `/api/v1/embedded/cancel/{job_id}` | Cancel processing |

### Callback Payload (Editor → phraze.so)

```json
{
  "job_id": "uuid-here",
  "status": "completed",
  "output_url": "https://s3.amazonaws.com/bucket/processed.mp4",
  "processing_time_seconds": 120,
  "metadata": {
    "text_regions_removed": 5,
    "lip_sync_applied": true,
    "output_duration_seconds": 45
  },
  "timestamp": "2025-12-16T10:30:00Z",
  "signature": "hmac-signature-for-verification"
}
```

---

## Updated Task List

### Phase 1: Core Integration (This Week - Priority)

#### 1.1 JWT Validation System
- [ ] Receive JWT secret/public key from phraze.so team
- [ ] Create `backend/auth/phraze_validator.py`
- [ ] Implement token validation middleware
- [ ] Extract userId, jobId, s3Url from token claims
- [ ] Handle token expiration gracefully

#### 1.2 Embedded Mode Configuration
- [ ] Add `EMBEDDED_MODE` flag to `backend/config.py`
- [ ] Add `PHRAZE_DOMAIN` configuration
- [ ] Add `PHRAZE_JWT_SECRET` or `PHRAZE_PUBLIC_KEY`
- [ ] Add `PHRAZE_CALLBACK_URL` configuration
- [ ] Update CORS for phraze.so origins

#### 1.3 Validation Endpoint
- [ ] Create `GET /api/v1/embedded/validate`
- [ ] Verify token signature and expiration
- [ ] Return decoded claims on success
- [ ] Return appropriate error codes on failure

#### 1.4 Embedded Editor Page (Frontend)
- [ ] Create `frontend/src/pages/EmbeddedEditor.tsx`
- [ ] Parse JWT from URL query parameter
- [ ] Call validation endpoint
- [ ] Load video from S3 URL (skip upload UI)
- [ ] Handle invalid token redirect to phraze.so

#### 1.5 Mock Redirect Page for Testing
- [ ] Create test page that generates JWTs
- [ ] Include mock userId, jobId, s3Url
- [ ] Simulate phraze.so redirect flow
- [ ] Allow testing different scenarios (expired, invalid, etc.)

### Phase 2: Completion Flow (After Developer Clarification)

#### 2.1 Callback Integration
- [ ] Implement callback to phraze.so on completion
- [ ] Send jobId, status, outputUrl
- [ ] Handle callback authentication (HMAC signature?)
- [ ] Implement retry logic for failed callbacks

#### 2.2 Error Handling
- [ ] Implement failure notifications to phraze.so
- [ ] Create error code mapping
- [ ] Redirect with appropriate error codes
- [ ] Log errors for debugging

#### 2.3 User Redirect Flow
- [ ] Redirect to phraze.so on completion
- [ ] Include job status in redirect URL
- [ ] Handle "back to phraze.so" button

### Phase 3: Polish & Testing

#### 3.1 Progress Reporting (If Required)
- [ ] Implement progress webhook to phraze.so
- [ ] Send percentage updates during processing

#### 3.2 Edge Case Handling
- [ ] Handle page refresh during editing
- [ ] Handle browser close during processing
- [ ] Handle concurrent sessions

#### 3.3 Documentation
- [ ] Document API endpoints
- [ ] Document JWT structure
- [ ] Document callback format
- [ ] Create integration guide for phraze.so team

---

## Questions to Confirm Before Starting

### Must Answer Before Implementation

| # | Question | Impact if Unknown |
|---|----------|-------------------|
| 1 | JWT algorithm and key sharing method? | Cannot implement token validation |
| 2 | Callback endpoint URL and format? | Cannot notify phraze.so of completion |
| 3 | S3 input URL format (pre-signed?)? | Cannot load videos |
| 4 | Where to store output files? | Cannot save processed videos |
| 5 | Return URL after completion? | Cannot redirect user back |

### Can Assume Reasonable Defaults

| # | Question | Assumed Default |
|---|----------|-----------------|
| 6 | Token expiration time? | 1 hour |
| 7 | Retry count for callbacks? | 3 retries with exponential backoff |
| 8 | Progress update frequency? | Every 10% or 30 seconds |

---

## Environment Variables (New)

```bash
# Embedded Mode Configuration
EMBEDDED_MODE=true
PHRAZE_DOMAIN=phraze.so
PHRAZE_JWT_SECRET=your-shared-secret          # If using HS256
PHRAZE_PUBLIC_KEY_PATH=/path/to/public.pem    # If using RS256
PHRAZE_CALLBACK_URL=https://phraze.so/api/editor/callback
PHRAZE_RETURN_URL=https://phraze.so/jobs    

# Allowed S3 Domains (comma-separated)
ALLOWED_S3_DOMAINS=s3.amazonaws.com,s3.us-east-2.amazonaws.com

# CORS - Update for phraze.so
CORS_ORIGINS=https://phraze.so,https://editor.phraze.so

# Callback Security
CALLBACK_HMAC_SECRET=secret-for-signing-callbacks
```

---

## Next Steps

1. **Send clarification questions to developer** (see [Questions for Developer](#suggested-questions-for-developer))
2. **Receive JWT secret/public key** from phraze.so team
3. **Start Phase 1 implementation** once questions are answered
4. **Create mock redirect page** for local testing
5. **Coordinate with phraze.so team** for integration testing

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-16 | Development Team | Initial analysis document |

---

*This document will be updated as clarifications are received from the phraze.so development team.*
