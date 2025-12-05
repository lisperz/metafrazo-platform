# Railway Deployment Checklist ✅

**Estimated Time**: 10-15 minutes
**Cost**: $5/month free tier

---

## 📋 Pre-Deployment Checklist

### Before You Start:

- [ ] Have a GitHub account (for Railway sign-up)
- [ ] Have API keys ready:
  - [ ] GhostCut API key
  - [ ] Sync.so API key
  - [ ] AWS S3 credentials (Access Key, Secret Key, Bucket name)
- [ ] Node.js installed (for Railway CLI)

---

## 🚀 Deployment Steps

### Step 1: Install Railway CLI (1 minute)

```bash
npm install -g @railway/cli
# OR
brew install railway
```

- [ ] Railway CLI installed
- [ ] Verified with `railway --version`

---

### Step 2: Sign Up & Login (2 minutes)

```bash
# Login to Railway
railway login
```

- [ ] Created account at https://railway.app
- [ ] Logged in via CLI
- [ ] Verified with `railway whoami`

---

### Step 3: Initialize Project (1 minute)

```bash
cd /Users/zhuchen/Downloads/Test1-frazo
railway init
```

- [ ] Project initialized
- [ ] Project name: `video-text-inpainting`

---

### Step 4: Add Database Services (2 minutes)

```bash
# Add PostgreSQL
railway add --database postgres

# Add Redis
railway add --database redis
```

- [ ] PostgreSQL added
- [ ] Redis added
- [ ] Verified with `railway variables` (should see DATABASE_URL and REDIS_URL)

---

### Step 5: Set Environment Variables (3 minutes)

```bash
railway variables set \
  JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  GHOSTCUT_API_KEY="your-ghostcut-key" \
  GHOSTCUT_APP_SECRET="your-ghostcut-secret" \
  GHOSTCUT_UID="your-ghostcut-uid" \
  SYNC_API_KEY="your-sync-key" \
  AWS_ACCESS_KEY_ID="your-aws-key" \
  AWS_SECRET_ACCESS_KEY="your-aws-secret" \
  AWS_S3_BUCKET="your-bucket-name" \
  AWS_REGION="us-east-1" \
  ENVIRONMENT="production" \
  DEBUG="false" \
  CORS_ORIGINS="https://company-website.com"
```

- [ ] All environment variables set
- [ ] Verified with `railway variables`

---

### Step 6: Deploy Backend (5 minutes)

```bash
railway up
```

- [ ] Backend deployment started
- [ ] Build successful
- [ ] Service running
- [ ] Checked logs with `railway logs`

---

### Step 7: Get Public URL (1 minute)

```bash
railway domain
```

- [ ] Public URL generated
- [ ] URL saved: `https://__________________.up.railway.app`

---

### Step 8: Test Deployment (2 minutes)

```bash
# Replace YOUR_URL with actual URL
curl https://YOUR_URL.up.railway.app/health

# Should return: {"status":"healthy"}
```

- [ ] Health check passed
- [ ] API docs accessible at `/docs`
- [ ] Tested authentication endpoint

---

## 📊 Post-Deployment Checklist

### Verify Everything Works:

- [ ] Backend responds to `/health` endpoint
- [ ] API documentation loads at `/docs`
- [ ] Database connection works (check logs)
- [ ] Redis connection works (check logs)
- [ ] CORS allows company website domain
- [ ] S3 file upload works

---

### Share with Company Developer:

- [ ] Sent backend URL: `https://____________.up.railway.app`
- [ ] Sent API documentation: `docs/INTEGRATION_GUIDE.md`
- [ ] Provided test credentials (if needed)
- [ ] Updated CORS to include their domain

---

## 🔧 Optional Setup

### Deploy Worker Service (for background jobs):

```bash
railway service create worker
railway up --service worker --dockerfile Dockerfile.worker
```

- [ ] Worker service created
- [ ] Worker deployed
- [ ] Worker processing jobs (check logs)

---

### Deploy Frontend (Choose One):

**Option A: Railway**
```bash
railway service create frontend
railway up --service frontend --dockerfile Dockerfile.frontend
```

- [ ] Frontend deployed to Railway
- [ ] Frontend URL: `https://__________________.up.railway.app`

**Option B: Netlify (Free)**
```bash
cd frontend
npm run build
npx netlify-cli deploy --prod --dir=build
```

- [ ] Frontend deployed to Netlify
- [ ] Frontend URL: `https://__________________.netlify.app`

---

### Set Up Auto-Deploy:

- [ ] Connected Railway to GitHub repository
- [ ] Enabled auto-deploy on push to main branch
- [ ] Tested: git push triggers automatic deployment

---

### Set Up Custom Domain (Optional):

```bash
railway domain add api.your-domain.com
```

- [ ] Custom domain added
- [ ] DNS configured
- [ ] SSL certificate generated
- [ ] Custom domain works: `https://api.your-domain.com`

---

## 📞 Information for Company Developer

After completing deployment, provide this information:

```
Backend API Base URL:
https://__________________.up.railway.app

API Documentation:
https://__________________.up.railway.app/docs

Authentication:
- Method: JWT Bearer Token
- Endpoint: POST /api/v1/auth/login

Key Endpoints:
- Upload & Process: POST /api/v1/video-editors/sync/pro-sync-process
- Job Status: GET /api/v1/jobs/{job_id}
- WebSocket: wss://__________________.up.railway.app

CORS Whitelist:
- Currently allows: https://company-website.com
- To add more domains: Contact me

Rate Limits:
- 60 requests/minute (Pro tier)

Documentation:
- See attached: INTEGRATION_GUIDE.md
- Quick Start: QUICK_START.md
- API Spec: API_SPECIFICATION.md
```

---

## 💰 Cost Tracking

- [ ] Checked current usage in Railway dashboard
- [ ] Set up billing alerts (if needed)
- [ ] Current monthly estimate: $________

**Free Tier**: $5/month credit (good for testing)
**Expected Cost**: ~$20-40/month (production)

---

## 🔄 Monitoring Setup

- [ ] Bookmarked Railway dashboard: https://railway.app/dashboard
- [ ] Set up real-time logs: `railway logs --stream`
- [ ] Checked metrics (CPU, Memory, Network)
- [ ] Set up alerting (optional)

---

## ✅ Deployment Complete!

If all checkboxes are checked, you're done! 🎉

**Your service is now live and ready for integration!**

---

## 📚 Useful Commands

```bash
# View logs
railway logs

# Check status
railway status

# List services
railway service list

# Open dashboard
railway open

# Update environment variables
railway variables set KEY=value

# Redeploy
railway up

# Connect to database
railway connect postgres

# View current variables
railway variables
```

---

## 🆘 Troubleshooting

If something doesn't work:

1. **Check logs**: `railway logs`
2. **Verify variables**: `railway variables`
3. **Check build status**: Railway dashboard → Deployments
4. **Test locally first**: `docker-compose up`
5. **Contact Railway support**: https://railway.app/help

---

## 📖 Documentation References

- Railway Guide: `docs/RAILWAY_DEPLOYMENT.md`
- Integration Guide: `docs/INTEGRATION_GUIDE.md`
- API Specification: `docs/API_SPECIFICATION.md`
- Quick Start: `docs/QUICK_START.md`

---

**Need help?** Ask me any questions about the deployment process!
