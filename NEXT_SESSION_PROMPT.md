# Next Session Context - MetaFrazo Platform

**Last Updated**: December 30, 2025
**Current Status**: Editor Jobs Feature Complete - Re-edit Feature Removed

---

## What Was Completed (Dec 30, 2025)

### Re-edit Feature Removed

The re-edit functionality (restoring segments/effects from previous sessions) was causing multiple TypeScript errors and runtime issues. It has been completely removed:

**MetaFrazo Changes:**
- Removed `initialSegments`/`initialEffects` props from `ProVideoEditor.tsx`
- Removed `segments_data`/`effects_data` from `ValidationResponse` in backend schemas
- Removed `SavedSegmentData`/`SavedEffectData` types from `embeddedApi.ts`
- Fixed TypeScript errors for optional `AudioInput` properties (`file`, `fileName`, `fileSize`)

**Phraze.so (Cadence) Changes:**
- Removed segments_data/effects_data fetching from JWT token generation
- Removed "Re-edit" button from Jobs page UI

**Note**: The database still stores `segments_data` and `effects_data` when callbacks come from MetaFrazo (for auditing), but they are no longer passed back to the editor via JWT.

---

## Current Production URLs

| Service | URL |
|---------|-----|
| MetaFrazo Frontend | https://frontend-production-b02b.up.railway.app |
| MetaFrazo Backend | https://backend-production-268a.up.railway.app |
| Embedded Editor | https://editor.phraze.so |
| Phraze.so Main | https://phraze.so |

---

## Key Files

### MetaFrazo Platform (This Repo)

| File | Purpose |
|------|---------|
| `frontend/src/components/VideoEditor/Pro/ProVideoEditor.tsx` | Main Pro editor component |
| `frontend/src/pages/embedded/EmbeddedEditorPage.tsx` | Embedded editor page for Phraze.so |
| `frontend/src/services/embeddedApi.ts` | API service for embedded mode |
| `frontend/src/types/segments.ts` | TypeScript interfaces for segments |
| `backend/auth/phraze/schemas.py` | Pydantic schemas for JWT validation |
| `backend/api/routes/embedded/routes.py` | API routes for embedded editor |

### Phraze.so Platform (Cadence Repo)

| File | Purpose |
|------|---------|
| `src/app/api/open/editor-jobs/route.ts` | Open API for job CRUD + callbacks |
| `src/app/api/translator/editor-jobs/generate-token/route.ts` | JWT token generation |
| `src/app/dashboard/translator/jobs/JobsPageContent.tsx` | Jobs page UI |

---

## Working Flow

1. User goes to Phraze.so Jobs page → Editor Jobs tab
2. User uploads video OR pastes S3 URL
3. JWT token generated, user redirected to MetaFrazo editor
4. User edits video → Adds audio segments, sets erasure areas
5. User submits → MetaFrazo processes video (Sync.so + GhostCut)
6. MetaFrazo sends callbacks to Phraze.so
7. User downloads completed video

---

## GitHub Repositories

- **MetaFrazo**: https://github.com/lisperz/metafrazo-platform (main branch)
- **Phraze.so (Cadence)**: `fix/jwt-key-database-query` branch contains latest changes

---

## Notes for Future Sessions

- **No Claude co-author**: Do not include Claude as co-author in git commits
- **AudioInput interface**: Properties `file`, `fileName`, `fileSize` are optional - always use `?? null` or `?? 0` when accessing them
- **Re-edit feature**: Currently disabled. If re-implementing, ensure all TypeScript types are properly handled
