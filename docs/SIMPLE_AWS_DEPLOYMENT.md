# Simple AWS Deployment Guide (Alternative to Elastic Beanstalk)

**For**: First-time AWS deployers who want a simpler approach
**Time**: 30-45 minutes
**Cost**: ~$50-100/month

---

## 🎯 Simplified Architecture

Instead of complex Elastic Beanstalk, we'll use:

1. **AWS App Runner** - For backend API (Docker container)
2. **AWS RDS** - For PostgreSQL database
3. **AWS ElastiCache** - For Redis (optional, can use Redis Cloud free tier)
4. **AWS S3** - For file storage (already using)
5. **Netlify/Vercel** - For React frontend (free tier)

This is **much simpler** than Elastic Beanstalk!

---

## 📋 Step-by-Step Deployment

### Step 1: Deploy PostgreSQL Database (AWS RDS)

1. Go to AWS Console → RDS → Create database
2. Choose:
   - Engine: PostgreSQL 15
   - Template: Free tier (or Dev/Test for production)
   - DB instance identifier: `vti-database`
   - Master username: `vti_user`
   - Master password: [Create secure password]
   - Instance: `db.t3.micro` (free tier eligible)
   - Storage: 20 GB
   - Public access: **No** (secure)
3. Click "Create database"
4. Wait 5-10 minutes for creation
5. **Save the endpoint**: `vti-database.xxxxxxxxx.us-east-1.rds.amazonaws.com`

---

### Step 2: Deploy Redis Cache (Redis Cloud - Free Alternative)

Since AWS ElastiCache is complex, use Redis Cloud (free tier):

1. Go to https://redis.com/try-free/
2. Sign up for free account
3. Create database:
   - Name: vti-redis
   - Region: Same as your AWS region
   - Plan: Free (30MB)
4. **Save connection string**: `redis://default:password@redis-xxxxx.redislabs.com:xxxxx`

---

### Step 3: Prepare Backend for AWS App Runner

Create `backend/Dockerfile.apprunner`:

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    ffmpeg \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/

# Create directories
RUN mkdir -p /app/uploads /app/logs

# Expose port
EXPOSE 8000

# Start application
CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Step 4: Push Backend Image to AWS ECR

```bash
# 1. Create ECR repository
aws ecr create-repository --repository-name vti-backend --region us-east-1

# 2. Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# 3. Build Docker image
docker build -f backend/Dockerfile.apprunner -t vti-backend .

# 4. Tag image
docker tag vti-backend:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/vti-backend:latest

# 5. Push to ECR
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/vti-backend:latest
```

**Replace** `YOUR_AWS_ACCOUNT_ID` with your actual AWS account ID (find it in AWS Console → Account Settings)

---

### Step 5: Deploy Backend with AWS App Runner

1. Go to AWS Console → App Runner → Create service
2. Choose:
   - Source: Container registry
   - Repository type: Amazon ECR
   - Container image URI: `YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/vti-backend:latest`
   - Port: 8000
3. Configure service:
   - Service name: `vti-backend-service`
   - CPU: 1 vCPU
   - Memory: 2 GB
4. Add environment variables (click "Add environment variable"):
   ```
   DATABASE_URL=postgresql://vti_user:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/video_text_inpainting
   REDIS_URL=redis://default:YOUR_PASSWORD@YOUR_REDIS_ENDPOINT:xxxxx
   JWT_SECRET_KEY=your-super-secret-key
   GHOSTCUT_API_KEY=your-ghostcut-key
   AWS_ACCESS_KEY_ID=your-aws-key
   AWS_SECRET_ACCESS_KEY=your-aws-secret
   AWS_S3_BUCKET=your-s3-bucket
   SYNC_API_KEY=your-sync-api-key
   CORS_ORIGINS=https://your-frontend-domain.netlify.app
   ENVIRONMENT=production
   DEBUG=false
   ```
5. Click "Create & deploy"
6. Wait 5-10 minutes for deployment
7. **Save the App Runner URL**: `https://xxxxx.us-east-1.awsapprunner.com`

---

### Step 6: Deploy Celery Worker (AWS ECS Fargate)

This is for background video processing.

1. Create `backend/Dockerfile.worker`:
   ```dockerfile
   FROM python:3.11-slim

   RUN apt-get update && apt-get install -y \
       build-essential curl ffmpeg libpq-dev && \
       rm -rf /var/lib/apt/lists/*

   WORKDIR /app
   COPY backend/requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY backend/ ./backend/

   CMD ["celery", "-A", "backend.workers.celery_app", "worker", "--loglevel=info"]
   ```

2. Push to ECR:
   ```bash
   aws ecr create-repository --repository-name vti-worker
   docker build -f backend/Dockerfile.worker -t vti-worker .
   docker tag vti-worker:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/vti-worker:latest
   docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/vti-worker:latest
   ```

3. Create ECS Fargate task:
   - Go to AWS Console → ECS → Create cluster
   - Cluster name: `vti-cluster`
   - Infrastructure: AWS Fargate
   - Create task definition:
     - Name: `vti-worker-task`
     - Container image: ECR worker image
     - Environment variables: Same as App Runner
   - Create service: Run 1 task continuously

---

### Step 7: Deploy Frontend (Netlify - Free!)

1. Build frontend:
   ```bash
   cd frontend
   npm run build
   ```

2. Go to https://netlify.com (free account)
3. Click "Add new site" → "Deploy manually"
4. Drag & drop the `frontend/build` folder
5. Configure:
   - Site name: `your-video-editor`
   - Build command: `npm run build`
   - Publish directory: `build`
6. Add environment variable:
   ```
   REACT_APP_API_URL=https://xxxxx.us-east-1.awsapprunner.com
   ```
7. **Your frontend URL**: `https://your-video-editor.netlify.app`

---

### Step 8: Update CORS in Backend

Update App Runner environment variables to allow your Netlify domain:

```bash
CORS_ORIGINS=https://your-video-editor.netlify.app,https://company-website.com
```

---

## 🌐 Final URLs

After deployment, you'll have:

- **Frontend**: `https://your-video-editor.netlify.app`
- **Backend API**: `https://xxxxx.us-east-1.awsapprunner.com`
- **API Docs**: `https://xxxxx.us-east-1.awsapprunner.com/docs`

**Share with company developer**:
```
Backend API: https://xxxxx.us-east-1.awsapprunner.com
Documentation: [Attach docs/INTEGRATION_GUIDE.md]
```

---

## 💰 Cost Breakdown

### Free Tier (First 12 months):
- RDS db.t3.micro: **Free** (750 hours/month)
- App Runner: **Free** (first 3 months, then ~$30/month)
- ECS Fargate: ~$15/month (0.25 vCPU, 0.5 GB)
- Redis Cloud: **Free** (30MB)
- Netlify: **Free**
- S3 storage: ~$5/month

**Total first year**: ~$20-30/month (after free tiers)

### After Free Tier:
- RDS db.t3.micro: ~$15/month
- App Runner: ~$30/month
- ECS Fargate: ~$15/month
- Redis Cloud: **Free** or upgrade to $5/month
- Netlify: **Free**
- S3 storage: ~$5/month

**Total after 1 year**: ~$65-75/month

---

## 🧪 Testing Your Deployment

```bash
# Test backend health
curl https://YOUR_APP_RUNNER_URL/health

# Test authentication
curl -X POST https://YOUR_APP_RUNNER_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}'

# Test frontend
open https://your-video-editor.netlify.app
```

---

## 🔧 Updating Your Application

### Update Backend:
```bash
# 1. Build new image
docker build -f backend/Dockerfile.apprunner -t vti-backend .

# 2. Push to ECR
docker tag vti-backend:latest YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/vti-backend:latest
docker push YOUR_AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/vti-backend:latest

# 3. App Runner auto-deploys new image (if auto-deploy enabled)
# OR manually trigger deployment in AWS Console
```

### Update Frontend:
```bash
cd frontend
npm run build
# Drag & drop build folder to Netlify dashboard
# OR connect GitHub repo for auto-deploy on git push
```

---

## 📊 Monitoring

### Backend Logs:
- AWS Console → App Runner → Your service → Logs

### Worker Logs:
- AWS Console → ECS → Clusters → vti-cluster → Tasks → Logs

### Database Monitoring:
- AWS Console → RDS → Your database → Monitoring

---

## 🆘 Troubleshooting

### Issue: Backend can't connect to database
**Solution**:
1. Check RDS security group allows traffic from App Runner
2. Verify DATABASE_URL is correct
3. Check RDS is in same VPC/region

### Issue: Frontend can't call backend (CORS error)
**Solution**:
1. Update CORS_ORIGINS environment variable in App Runner
2. Ensure frontend is using correct API URL
3. Check browser console for exact error

### Issue: Worker not processing jobs
**Solution**:
1. Check ECS task is running (not stopped)
2. Verify Redis connection in worker logs
3. Ensure CELERY_BROKER_URL is correct

---

## 🎯 Advantages of This Approach

✅ **Simpler** than Elastic Beanstalk
✅ **Cheaper** (uses free tiers)
✅ **Easier to update** (just push new Docker images)
✅ **Better separation** (frontend on Netlify, backend on App Runner)
✅ **No server management** (fully managed services)

---

**Ready to deploy? Follow the steps above, and you'll have a production-ready service in 30-45 minutes!** 🚀

**Questions? Let me know and I'll help you through each step!**
