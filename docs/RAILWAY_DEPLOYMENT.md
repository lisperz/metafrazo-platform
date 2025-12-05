# Railway.app Deployment Guide - FASTEST & EASIEST! 🚂

**Deployment Time**: 10-15 minutes
**Cost**: $5/month free tier, then ~$20-40/month
**Difficulty**: ⭐☆☆☆☆ (Easiest option!)

---

## 🎯 Why Railway?

- ✅ **Supports Docker Compose directly** - Use your existing setup!
- ✅ **Automatic PostgreSQL & Redis** - One-click database creation
- ✅ **No AWS permissions needed** - You control everything
- ✅ **$5 free credit/month** - Perfect for testing
- ✅ **Auto-deploys from GitHub** - Push code = auto-deploy
- ✅ **Public URL automatically** - Get https://your-app.up.railway.app
- ✅ **Much simpler than AWS** - No IAM, security groups, VPCs, etc.

---

## 📋 What You'll Get

After deployment:
```
Frontend:  https://frontend-production-xxxx.up.railway.app
Backend:   https://backend-production-xxxx.up.railway.app
Database:  Managed PostgreSQL (automatic backups)
Redis:     Managed Redis (automatic)
```

**Share with company developer**:
- Backend API: `https://backend-production-xxxx.up.railway.app`
- Documentation: `docs/INTEGRATION_GUIDE.md`

---

## 🚀 Step-by-Step Deployment

### Step 1: Sign Up for Railway (2 minutes)

1. Go to https://railway.app
2. Click "Start a New Project"
3. Sign up with:
   - **GitHub** (recommended - enables auto-deploy)
   - Or email

**No credit card required for trial!** You get $5 free credit.

---

### Step 2: Install Railway CLI (1 minute)

```bash
# Install Railway CLI
npm install -g @railway/cli

# OR if you don't have npm
brew install railway

# Verify installation
railway --version
```

---

### Step 3: Login to Railway

```bash
# Login to Railway (opens browser)
railway login

# You'll see: "Logged in as your-email@example.com"
```

---

### Step 4: Create Railway Project

```bash
# Navigate to your project
cd /Users/zhuchen/Downloads/Test1-frazo

# Initialize Railway project
railway init

# Choose:
# - Project name: video-text-inpainting
# - Create new project: Yes
```

---

### Step 5: Add PostgreSQL Database (1 minute)

```bash
# Add PostgreSQL to your project
railway add --database postgres

# Railway automatically:
# ✅ Creates PostgreSQL instance
# ✅ Generates DATABASE_URL
# ✅ Sets up backups
```

---

### Step 6: Add Redis Cache (1 minute)

```bash
# Add Redis to your project
railway add --database redis

# Railway automatically:
# ✅ Creates Redis instance
# ✅ Generates REDIS_URL
```

---

### Step 7: Set Environment Variables

```bash
# Set all required environment variables
railway variables set \
  JWT_SECRET_KEY="your-super-secret-production-key-$(openssl rand -hex 32)" \
  GHOSTCUT_API_KEY="your-ghostcut-api-key" \
  GHOSTCUT_APP_SECRET="your-ghostcut-app-secret" \
  GHOSTCUT_UID="your-ghostcut-uid" \
  GHOSTCUT_API_URL="https://api.zhaoli.com" \
  SYNC_API_KEY="your-sync-api-key" \
  SYNC_API_URL="https://api.sync.so" \
  AWS_ACCESS_KEY_ID="your-aws-access-key" \
  AWS_SECRET_ACCESS_KEY="your-aws-secret-key" \
  AWS_REGION="us-east-1" \
  AWS_S3_BUCKET="your-s3-bucket-name" \
  ENVIRONMENT="production" \
  DEBUG="false" \
  CORS_ORIGINS="https://company-website.com"
```

**Note**: Railway automatically provides `DATABASE_URL` and `REDIS_URL` from Step 5 & 6!

---

### Step 8: Create Railway Configuration

Railway uses `railway.json` for multi-service deployments. Let me create this for you:

**File**: `railway.json`
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile.backend"
  },
  "deploy": {
    "numReplicas": 1,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

---

### Step 9: Deploy Backend Service

```bash
# Deploy backend to Railway
railway up

# Railway will:
# 1. Build your Docker image (Dockerfile.backend)
# 2. Push to Railway registry
# 3. Deploy to Railway infrastructure
# 4. Generate public URL
# 5. Start the service

# This takes 3-5 minutes...
```

**Watch the deployment**:
```bash
# Check deployment status
railway status

# View logs
railway logs
```

---

### Step 10: Deploy Worker Service (Celery)

Railway doesn't directly support multiple services in one command, so we'll create separate services:

```bash
# Create a new service for worker
railway service create worker

# Deploy worker
railway up --service worker --dockerfile Dockerfile.worker

# Worker will use same DATABASE_URL and REDIS_URL automatically!
```

---

### Step 11: Deploy Frontend (Netlify or Railway)

**Option A: Deploy Frontend to Railway** (Recommended)

```bash
# Create frontend service
railway service create frontend

# Deploy frontend
railway up --service frontend --dockerfile Dockerfile.frontend
```

**Option B: Deploy Frontend to Netlify** (Free!)

```bash
# Build frontend
cd frontend
npm run build

# Deploy to Netlify
npx netlify-cli deploy --prod --dir=build

# You'll get: https://your-app.netlify.app
```

---

### Step 12: Get Your Public URLs

```bash
# List all services
railway service list

# Get backend URL
railway domain

# You'll see something like:
# https://backend-production-xxxx.up.railway.app
```

**Alternative**: Go to Railway dashboard (https://railway.app/dashboard) and click on each service to see URLs.

---

## 🌐 Your Deployment URLs

After completion, you'll have:

```
Backend API:    https://backend-production-xxxx.up.railway.app
API Docs:       https://backend-production-xxxx.up.railway.app/docs
Frontend:       https://frontend-production-xxxx.up.railway.app
                (or https://your-app.netlify.app if using Netlify)

Database:       Managed PostgreSQL (internal)
Redis:          Managed Redis (internal)
Worker:         Running in background (no public URL)
```

---

## 🧪 Test Your Deployment

```bash
# 1. Test health endpoint
curl https://backend-production-xxxx.up.railway.app/health

# Expected: {"status": "healthy"}

# 2. Test authentication
curl -X POST https://backend-production-xxxx.up.railway.app/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}'

# 3. Open API docs in browser
open https://backend-production-xxxx.up.railway.app/docs
```

---

## 💰 Railway Pricing

### Free Tier (Hobby Plan):
- **$5 credit/month** (renews monthly)
- Good for: Testing and low-traffic apps
- Includes: Database, Redis, deployments

### When You Need More (After $5 credit):
- **Pay-as-you-go**: Only pay for what you use
- **~$20-40/month** for your app (typical)
  - Backend: ~$10-15/month (512MB RAM)
  - Worker: ~$5-10/month (256MB RAM)
  - PostgreSQL: ~$5/month (1GB storage)
  - Redis: ~$5/month (256MB)
  - Frontend: ~$5/month (if hosted on Railway)

### Cost Optimization:
- Host frontend on **Netlify** (free) instead of Railway
- Use smaller instances during testing
- Scale up when company website integrates

---

## 🔄 Updating Your Application

### Method 1: GitHub Auto-Deploy (Recommended)

```bash
# 1. Connect Railway to GitHub (in Railway dashboard)
# 2. Every time you push to main branch:
git push origin main

# Railway automatically:
# ✅ Detects new commit
# ✅ Builds new Docker image
# ✅ Deploys automatically
# ✅ Zero downtime deployment
```

### Method 2: Manual Deploy

```bash
# Make code changes
# Then redeploy
railway up

# Railway rebuilds and redeploys
```

---

## 📊 Monitoring & Logs

### View Logs
```bash
# Real-time logs
railway logs

# Logs for specific service
railway logs --service backend

# Last 100 lines
railway logs --tail 100
```

### Railway Dashboard
1. Go to https://railway.app/dashboard
2. Click on your project
3. View:
   - **Deployments**: Build history
   - **Metrics**: CPU, Memory, Network
   - **Logs**: Real-time application logs
   - **Variables**: Environment variables

---

## 🛠️ Common Tasks

### Add Custom Domain

```bash
# Add your custom domain
railway domain add api.your-company.com

# Railway provides:
# 1. DNS instructions
# 2. Automatic SSL certificate
# 3. HTTPS enabled
```

### Scale Your Application

```bash
# Scale backend to 2 replicas
railway scale backend --replicas 2

# Or use Railway dashboard: Settings → Replicas
```

### Database Backups

Railway automatically backs up PostgreSQL:
- **Frequency**: Daily
- **Retention**: 7 days
- **Manual backup**: Railway dashboard → Database → Backups → Create Backup

### View Database

```bash
# Connect to PostgreSQL
railway connect postgres

# You'll get a psql shell
# \dt - list tables
# \q - quit
```

---

## 🆘 Troubleshooting

### Issue: "Railway login failed"
**Solution**:
```bash
# Clear Railway config
rm -rf ~/.railway

# Login again
railway login
```

### Issue: "Build failed - Docker error"
**Solution**:
```bash
# Check Dockerfile paths
ls -la Dockerfile.backend

# Test build locally first
docker build -f Dockerfile.backend -t test .
```

### Issue: "Service not responding"
**Solution**:
```bash
# Check logs for errors
railway logs --service backend

# Common issues:
# 1. DATABASE_URL not set → Check environment variables
# 2. Port mismatch → Railway expects port from $PORT variable
# 3. Missing dependencies → Check requirements.txt
```

### Issue: "Database connection error"
**Solution**:
```bash
# Verify DATABASE_URL exists
railway variables

# Test database connection
railway run python -c "import psycopg2; print('DB OK')"
```

### Issue: "CORS errors from company website"
**Solution**:
```bash
# Add company domain to CORS_ORIGINS
railway variables set CORS_ORIGINS="https://company-website.com,https://www.company-website.com"

# Redeploy
railway up
```

---

## 🔒 Security Best Practices

1. **Rotate secrets regularly**
   ```bash
   # Generate new JWT secret
   railway variables set JWT_SECRET_KEY="$(openssl rand -hex 32)"
   ```

2. **Use Railway's secret variables**
   - Never commit secrets to Git
   - Railway encrypts all variables

3. **Enable 2FA on Railway account**
   - Go to Railway dashboard → Settings → Security

4. **Restrict CORS origins**
   ```bash
   # Only allow company website
   railway variables set CORS_ORIGINS="https://company-website.com"
   ```

5. **Monitor access logs**
   ```bash
   # Check for unusual activity
   railway logs | grep "401\|403\|500"
   ```

---

## 📞 Share with Company Developer

After deployment, send this to the company developer:

```
Hi [Developer Name],

Our video editor service is now deployed and ready for integration!

🌐 Backend API: https://backend-production-xxxx.up.railway.app
📖 API Documentation: https://backend-production-xxxx.up.railway.app/docs
📚 Integration Guide: [Attach docs/INTEGRATION_GUIDE.md]

The service includes:
✅ Multi-segment lip-sync (Sync.so API)
✅ Text removal (GhostCut API)
✅ WebSocket real-time updates
✅ JWT authentication
✅ S3 file storage

Let me know if you need:
- API credentials
- CORS domain whitelist update
- Any clarification on endpoints

Ready to integrate! 🚀

Best,
[Your Name]
```

---

## 🎓 Railway vs AWS Comparison

| Feature | Railway | AWS App Runner |
|---------|---------|----------------|
| Setup time | 10 min | 45 min |
| Docker Compose support | ✅ Native | ❌ No |
| Database setup | 1 click | 15 min |
| Redis setup | 1 click | 30 min |
| Cost (monthly) | $20-40 | $50-80 |
| Auto-deploy from GitHub | ✅ Built-in | ⚙️ Manual setup |
| Logs & monitoring | ✅ Built-in | ⚙️ CloudWatch |
| Custom domains | ✅ Free SSL | ✅ Free SSL |
| Scaling | ✅ Easy | ⚙️ Medium |
| Permissions needed | ❌ No | ✅ IAM roles |

---

## 🚀 Next Steps

1. ✅ **Deploy to Railway** (10-15 minutes)
2. ✅ **Test all endpoints** (5 minutes)
3. ✅ **Share URL with company developer**
4. ✅ **They start integration!**
5. ✅ **Monitor usage and costs**

Later (optional):
- Migrate to company AWS when permissions granted
- Set up custom domain (api.your-company.com)
- Enable GitHub auto-deploy
- Scale up if needed

---

## 💡 Pro Tips

1. **Use Railway CLI for everything** - It's faster than web dashboard
2. **Enable GitHub auto-deploy** - Push code = auto-deploy
3. **Monitor costs** - Railway dashboard shows real-time usage
4. **Start small, scale later** - Begin with minimal resources
5. **Keep Railway for staging** - Even after moving to AWS, Railway is great for testing

---

## 📊 Expected Timeline

```
Now:       Deploy to Railway (10 minutes)
           ↓
Today:     Share URL with company developer
           ↓
This week: Company developer integrates
           ↓
Next week: Monitor usage, optimize costs
           ↓
Later:     Migrate to company AWS (optional)
```

---

**Ready to deploy? Follow the steps above, and you'll have a public URL in 10-15 minutes!** 🚀

**Questions? I'm here to help with every step!**
