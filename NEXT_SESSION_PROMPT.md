# Next Session Context - Railway Deployment Status

**Last Updated**: December 7, 2025
**Current Status**: **FULLY DEPLOYED AND WORKING**

---

## Railway Deployment - Current State

### All Services Running

| Service | URL | Status |
|---------|-----|--------|
| Backend API | https://backend-production-268a.up.railway.app | Running |
| Frontend | https://frontend-production-b02b.up.railway.app | Running |
| PostgreSQL | Internal Railway connection | Connected |
| Redis | Internal Railway connection | Connected |
| Worker (Celery) | Internal | Running |
| Beat (Scheduler) | Internal | Running |

### Features Working

1. **User Authentication**: Login/logout with JWT tokens
2. **Normal Video Editor**: `/editor` - Lip-sync + text removal
3. **Pro Video Editor**: `/editor/pro` - Advanced segments-based lip-sync
4. **Translation History**: `/history` - View all processed jobs
5. **Dashboard**: `/dashboard` - User overview with quick actions
6. **GhostCut Integration**: Text removal API working
7. **Sync.so Integration**: Lip-sync API working
8. **AWS S3**: File uploads working

---

## Demo Credentials

| Email | Password | Role |
|-------|----------|------|
| demo@example.com | demo123 | User |
| boss@example.com | boss123 | Admin |

---

## Key Files Reference

### Backend API Routes
- **Normal Video Editor API**: `backend/api/routes/video_editors/sync/sync_api_original.py`
  - Endpoint: `POST /api/v1/video-editors/sync-process`
- **Pro Video Editor API**: `backend/api/routes/video_editors/sync/routes.py`
  - Endpoint: `POST /api/v1/video-editors/pro-sync-process`
- **GhostCut (Text Removal)**: `backend/api/routes/jobs/processing/direct_process_original.py`
  - Endpoint: `POST /api/v1/jobs/direct-process`

### Frontend Key Components
- **Sidebar Navigation**: `frontend/src/components/Layout/Sidebar.tsx`
- **Dashboard Page**: `frontend/src/pages/dashboard/DashboardPage/DashboardPage.tsx`
- **Jobs Page**: `frontend/src/pages/jobs/JobsPage.tsx`
- **Job Actions Menu**: `frontend/src/pages/jobs/components/JobActionsMenu.tsx`
- **Video Editor Page**: `frontend/src/pages/video/VideoEditorPage.tsx`
- **App Routes**: `frontend/src/App.tsx`

### Configuration
- **Backend Settings**: `backend/config.py`

---

## Railway CLI Reference

```bash
# View logs
railway logs --service backend
railway logs --service worker
railway logs --service frontend

# Deploy manually
railway up --service backend --detach
railway up --service frontend --detach

# Check status
railway status
```

---

## Important Notes

1. **Frontend Environment Variables**: React embeds env vars at BUILD TIME. After changing `REACT_APP_*` variables, trigger a rebuild with `railway up --service frontend --detach`

2. **Sync.so API Credits**: If jobs fail with "free credit limit exceeded", add credits at https://sync.so/billing/subscription

3. **Both video editors share the same API key**: Normal and Pro editors both use `settings.sync_api_key`

4. **Job Status Spelling**: Database uses `canceled` (American), frontend handles both `canceled` and `cancelled` (British)

---

## Current App Structure

### Navigation (Sidebar)
- **TRANSLATE**
  - Video Editor → `/editor`
  - Pro Video Editor (PRO badge) → `/editor/pro`
  - Translation History → `/history`
- **CREDITS**
  - Credits → `/credits`
- **HELP & SUPPORT**
  - Documentation → `/docs`
  - FAQ → `/faq`
  - Support → `/support`

### Main Pages
- `/dashboard` - User dashboard with quick actions, credit usage, recent jobs
- `/editor` - Normal video editor (text removal + lip-sync)
- `/editor/pro` - Pro video editor (segment-based lip-sync)
- `/history` or `/jobs` - Translation/job history
- `/credits` - Account settings and profile information

### Sidebar Features
- **MetaFrazo Logo**: Clickable, navigates to `/dashboard`
- **Account Section**: Shows user email, avatar clickable to profile
- **Account Dropdown**: Profile Settings and Sign Out options

---

## Latest Updates (December 7, 2025)

### UI Improvements

1. **Account Dropdown Menu** (`Sidebar.tsx`)
   - Added dropdown menu when clicking the expand arrow in Account section
   - Menu includes: Profile Settings, Sign Out
   - Sign Out calls logout API and redirects to `/login`

2. **Clickable Logo and Avatar** (`Sidebar.tsx`)
   - MetaFrazo logo (M icon) now clickable → navigates to `/dashboard`
   - MetaFrazo text also clickable → navigates to `/dashboard`
   - User avatar clickable → navigates to `/credits` (profile settings)

3. **Removed Statistics Row** (`DashboardPage.tsx`)
   - Removed StatsCards component from dashboard
   - Dashboard now shows: Header, Subscription Alert, Quick Actions, Credit Usage, Recent Jobs

4. **Fixed Job Actions Menu** (`JobActionsMenu.tsx`)
   - Fixed empty menu for canceled jobs (spelling mismatch: `canceled` vs `cancelled`)
   - Now handles both American (`canceled`) and British (`cancelled`) spellings
   - Shows "Delete Job" option for all terminal states (completed, failed, canceled/cancelled)
   - Shows "No actions available" when no actions are applicable
   - Added loading states: "Cancelling...", "Deleting..."

### Files Modified
- `frontend/src/components/Layout/Sidebar.tsx`
- `frontend/src/pages/dashboard/DashboardPage/DashboardPage.tsx`
- `frontend/src/pages/jobs/components/JobActionsMenu.tsx`
- `frontend/src/pages/jobs/types.ts`
- `frontend/src/pages/jobs/utils/formatters.ts`

---

## Application Status

The application is fully deployed and functional:
- Clean dashboard without statistics row
- Clickable logo navigates to dashboard
- Account dropdown with Sign Out functionality
- Job actions menu properly shows Delete for all terminal job states
- Video Editor with lip-sync + text removal
- Pro Video Editor with segment-based processing
- Translation History with proper job actions
- All API integrations working (GhostCut, Sync.so, AWS S3)
