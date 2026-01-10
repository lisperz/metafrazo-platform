# Next Session Context - MetaFrazo Platform

**Last Updated**: January 10, 2026
**Current Status**: Database Password Fixed, Speaker-Selection Feature Planned

---

## This Week's Tasks (Jan 2026)

| Task | Status | Notes |
|------|--------|-------|
| 1. Choose timestamps in 2-hour video | ✅ Complete | |
| 2. Fix errors with video editor + phraze.so | ✅ Fixed locally | AWS DB password updated |
| 3. Cross-env testing (phraze.so, dev, staging) | 🔄 In Progress | Waiting for Phraze developer to update AWS env vars |
| 4. Speaker-selection research | ✅ Documented | See `discuss/speaker-selection-task-breakdown.md` |

---

## Recent Changes (Jan 10, 2026)

### Database Password Issue Fixed

AWS RDS database passwords were changed, breaking Editor Jobs. Fixed locally by updating:

**Phraze.so (Cadence) `.env.local`:**
```
# Dev database
AWS_DB_HOST=phraze-dev-instance-1.ccdrwsnbgg82.us-east-2.rds.amazonaws.com
AWS_DB_PASSWORD="5lzrR.wZxn|WbD2(iFYbe6p.c-bg"
```

**Phraze.so (Cadence) `.env` (production):**
```
# Production database
AWS_DB_HOST=cadence-db.ccdrwsnbgg82.us-east-2.rds.amazonaws.com
AWS_DB_PASSWORD="?j<doiF5.kP0QAQ_hXg92!d46IU6"
```

**Status**: Local works. Production environments (phraze.so, staging.phraze.so, dev.phraze.so) need AWS Elastic Beanstalk env var updates by Phraze developer.

### Speaker-Selection Feature Research

Created comprehensive task breakdown for Sync.so speaker-selection integration:
- **Document**: `discuss/speaker-selection-task-breakdown.md`
- **API Reference**: https://docs.sync.so/developer-guides/speaker-selection
- **Estimated effort**: 14-20 hours across 5 phases

---

## Production URLs

| Service | URL |
|---------|-----|
| MetaFrazo Frontend | https://frontend-production-b02b.up.railway.app |
| MetaFrazo Backend | https://backend-production-268a.up.railway.app |
| Embedded Editor | https://editor.phraze.so |
| Phraze.so Main | https://phraze.so |
| Phraze.so Staging | https://staging.phraze.so |
| Phraze.so Dev | https://dev.phraze.so |

---

## GitHub Repositories

| Repo | URL | Branch |
|------|-----|--------|
| MetaFrazo (Video Editor) | https://github.com/lisperz/metafrazo-platform | `main` |
| Phraze.so (Cadence) | https://github.com/phrazeai-dev/cadence | `fix/jwt-key-database-query` |

---

## Key Files

### MetaFrazo Platform (This Repo)

| File | Purpose |
|------|---------|
| `frontend/src/components/VideoEditor/Pro/ProVideoEditor.tsx` | Main Pro editor component |
| `frontend/src/pages/embedded/EmbeddedEditorPage.tsx` | Embedded editor page for Phraze.so |
| `frontend/src/services/embeddedApi.ts` | API service for embedded mode |
| `backend/services/sync_segments_service.py` | Sync.so API integration (add speaker-selection here) |
| `backend/auth/phraze/schemas.py` | Pydantic schemas for JWT validation |
| `discuss/speaker-selection-task-breakdown.md` | Speaker-selection implementation plan |

### Phraze.so Platform (Cadence Repo)

| File | Purpose |
|------|---------|
| `src/app/api/open/editor-jobs/route.ts` | Open API for job CRUD + callbacks |
| `src/app/api/translator/editor-jobs/generate-token/route.ts` | JWT token generation |
| `src/app/dashboard/translator/jobs/JobsPageContent.tsx` | Jobs page UI with Editor Jobs tab |
| `src/constants/featureFlags.ts` | Controls Editor Jobs access per environment/user |

---

## Environment Configuration

### Three Phraze.so Environments

| Environment | URL | Database | User with Editor Access |
|-------------|-----|----------|-------------------------|
| Dev | dev.phraze.so / localhost | phraze-dev-instance-1 | `03139de3-8cc6-4702-a2fd-048dff642ccb` |
| Staging | staging.phraze.so | phraze-dev-instance-1 | `3793b467-c3c0-4982-8d23-1b2a21aafb18` |
| Production | phraze.so | cadence-db | `3793b467-c3c0-4982-8d23-1b2a21aafb18` |

### Switching Environments Locally (Cadence)

Edit `NEXT_PUBLIC_APP_URL` in `.env.local`:
```bash
# Dev (default)
NEXT_PUBLIC_APP_URL=http://localhost:3000

# Staging
NEXT_PUBLIC_APP_URL=https://staging.phraze.so

# Production
NEXT_PUBLIC_APP_URL=https://phraze.so
```

Then restart `npm run dev`.

---

## Integration Flow

```
Phraze.so                              MetaFrazo Editor
    │                                      │
    │  1. User creates editor job          │
    │  2. JWT token generated (RS256)      │
    │  3. Redirect ──────────────────────► │
    │                                      │  4. Validate JWT
    │                                      │  5. Load video
    │                                      │  6. User edits
    │                                      │  7. Submit processing
    │  8. Callback ◄────────────────────── │
    │  9. Update job status                │
    │ 10. User downloads result            │
```

---

## Next Steps

### Immediate (Waiting on Phraze Developer)
- [ ] Phraze developer updates AWS Elastic Beanstalk env vars for all 3 environments
- [ ] Test Editor Jobs on dev.phraze.so, staging.phraze.so, phraze.so

### Speaker-Selection Implementation (Next Feature)
- [ ] Phase 1: Backend API enhancement (2-3 hrs)
- [ ] Phase 2: Frame capture utilities (3-4 hrs)
- [ ] Phase 3: Speaker selection UI (4-6 hrs)
- [ ] Phase 4: Integration with submit flow (3-4 hrs)
- [ ] Phase 5: Testing & edge cases (2-3 hrs)

---

## Notes for Future Sessions

- **No Claude co-author**: Do not include Claude as co-author in git commits
- **AudioInput interface**: Properties `file`, `fileName`, `fileSize` are optional - use `?? null` or `?? 0`
- **Re-edit feature**: Removed (Dec 2025). Database still stores data for auditing.
- **Run scripts**: Use `.sh` scripts in `scripts/` directory, not direct npm/python commands
- **File limits**: Keep files under 300 lines, folders under 8 files
