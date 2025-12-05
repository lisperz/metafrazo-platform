# AWS Deployment Guide - Video Text Inpainting Service

**Target**: Production deployment on AWS
**Last Updated**: December 2, 2025

---

## 🎯 Why NOT AWS Amplify?

AWS Amplify is designed for:
- ❌ Static websites (HTML/CSS/JS)
- ❌ Single-page React apps (no backend)
- ❌ Serverless applications (Lambda functions)

Your application requires:
- ✅ PostgreSQL database (persistent storage)
- ✅ Redis cache (in-memory database)
- ✅ Celery workers (background processing)
- ✅ Multi-container Docker setup
- ✅ Long-running video processing tasks

**Conclusion**: AWS Amplify cannot handle your architecture.

---

## 🚀 Recommended: AWS Elastic Beanstalk

**Best for**: Docker Compose multi-container applications like yours

### Why Elastic Beanstalk?

1. ✅ **Supports Docker Compose** - Deploy your exact setup
2. ✅ **Managed infrastructure** - AWS handles servers, load balancing, auto-scaling
3. ✅ **RDS + ElastiCache** - Managed PostgreSQL and Redis
4. ✅ **Easy deployment** - `eb deploy` command
5. ✅ **Cost-effective** - Pay only for resources used
6. ✅ **Health monitoring** - Built-in application health checks

---

## 📋 Deployment Steps

### Step 1: Install AWS CLI & EB CLI

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# Install EB CLI
pip install awsebcli --upgrade --user

# Verify installation
aws --version
eb --version
```

---

### Step 2: Configure AWS Credentials

```bash
# Configure AWS CLI with your credentials
aws configure

# Enter:
# - AWS Access Key ID: [Your AWS Access Key]
# - AWS Secret Access Key: [Your AWS Secret Key]
# - Default region: us-east-1 (or your preferred region)
# - Default output format: json
```

**Where to get AWS credentials**:
1. Go to AWS Console → IAM → Users → Create User
2. Attach policy: `AdministratorAccess-AWSElasticBeanstalk`
3. Create access key → Save Access Key ID and Secret Access Key

---

### Step 3: Prepare Your Application

#### Create `.ebignore` file:

```bash
# .ebignore - Files to exclude from deployment
.git
.venv
__pycache__
*.pyc
*.pyo
node_modules
.DS_Store
.env
logs/
.idea
*.log
frontend/node_modules
frontend/build
postgres_data
redis_data
upload_data
```

#### Create `Dockerrun.aws.json` (Elastic Beanstalk multi-container config):

```json
{
  "AWSEBDockerrunVersion": 2,
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "backend",
      "essential": true,
      "memory": 1024,
      "portMappings": [
        {
          "hostPort": 8000,
          "containerPort": 8000
        }
      ],
      "links": ["redis"],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ]
    },
    {
      "name": "redis",
      "image": "redis:7-alpine",
      "essential": true,
      "memory": 512,
      "command": ["redis-server", "--appendonly", "yes"]
    },
    {
      "name": "worker",
      "image": "worker",
      "essential": true,
      "memory": 1024,
      "links": ["redis"]
    },
    {
      "name": "frontend",
      "image": "frontend",
      "essential": true,
      "memory": 512,
      "portMappings": [
        {
          "hostPort": 80,
          "containerPort": 80
        }
      ],
      "links": ["backend"]
    }
  ]
}
```

---

### Step 4: Initialize Elastic Beanstalk Application

```bash
# Navigate to project root
cd /Users/zhuchen/Downloads/Test1-frazo

# Initialize EB application
eb init

# Follow prompts:
# - Select region: us-east-1 (or your preferred)
# - Application name: video-text-inpainting
# - Platform: Docker (Multi-container)
# - Set up SSH: Yes (for debugging)
```

---

### Step 5: Create RDS PostgreSQL Database

```bash
# Create EB environment with RDS
eb create video-inpainting-prod \
  --database.engine postgres \
  --database.username vti_user \
  --database.password YOUR_SECURE_PASSWORD \
  --instance-type t3.medium \
  --envvars \
    JWT_SECRET_KEY=your-production-jwt-secret,\
    GHOSTCUT_API_KEY=your-ghostcut-key,\
    AWS_ACCESS_KEY_ID=your-aws-key,\
    AWS_SECRET_ACCESS_KEY=your-aws-secret,\
    AWS_S3_BUCKET=your-s3-bucket,\
    SYNC_API_KEY=your-sync-api-key,\
    CORS_ORIGINS=https://company-website.com
```

**This creates**:
- ✅ Load balancer
- ✅ Auto-scaling group (2 EC2 instances)
- ✅ RDS PostgreSQL database
- ✅ Security groups
- ✅ CloudWatch monitoring

---

### Step 6: Deploy Your Application

```bash
# Deploy to Elastic Beanstalk
eb deploy

# Monitor deployment
eb status
eb logs

# Open application in browser
eb open
```

---

### Step 7: Set Up ElastiCache Redis (Optional - for production)

1. Go to AWS Console → ElastiCache
2. Create Redis cluster:
   - Node type: `cache.t3.micro`
   - Number of nodes: 1
   - VPC: Same as EB environment
3. Update EB environment variable:
   ```bash
   eb setenv REDIS_URL=redis://your-elasticache-endpoint:6379/0
   ```

---

## 🔧 Alternative: Simpler AWS Services Configuration

If Elastic Beanstalk is too complex, here's a **simpler approach**:

### Frontend: AWS Amplify (Static React Build)
### Backend: AWS App Runner (Docker container)
### Database: AWS RDS (PostgreSQL)
### Cache: AWS ElastiCache (Redis)
### Storage: AWS S3 (already using)

Let me know if you want this alternative approach!

---

## 🌐 Your Deployment URL

After deployment, you'll get:
```
http://video-inpainting-prod.us-east-1.elasticbeanstalk.com
```

Or set up custom domain:
```
https://video-editor.your-company.com
```

---

## 💰 Estimated AWS Costs

### Basic Setup (Development):
- EC2 t3.medium (2 instances): ~$60/month
- RDS db.t3.micro: ~$15/month
- Load Balancer: ~$20/month
- S3 storage: ~$5/month (100GB)
- **Total: ~$100/month**

### Production Setup:
- EC2 t3.large (2-4 instances): ~$150-300/month
- RDS db.t3.small: ~$30/month
- ElastiCache: ~$20/month
- Load Balancer: ~$20/month
- S3 + CloudFront: ~$20/month
- **Total: ~$240-390/month**

---

## 🔒 Security Checklist

- ✅ Use HTTPS (Elastic Beanstalk provides free SSL certificate)
- ✅ Store secrets in AWS Secrets Manager (not environment variables)
- ✅ Enable VPC for database (not publicly accessible)
- ✅ Set up WAF (Web Application Firewall) for DDoS protection
- ✅ Enable CloudWatch logs and alarms
- ✅ Rotate JWT secret keys regularly
- ✅ Use IAM roles (not hardcoded AWS keys)

---

## 🧪 Testing Your Deployment

After deployment, test all endpoints:

```bash
# Get deployment URL
export API_URL=$(eb status | grep CNAME | awk '{print $2}')

# Test health endpoint
curl https://$API_URL/health

# Test authentication
curl -X POST https://$API_URL/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'

# Test file upload (after getting token)
curl -X POST https://$API_URL/api/v1/video-editors/sync/pro-sync-process \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.mp4" \
  -F "audio_files=@audio.mp3" \
  -F 'segments_data=[{"startTime": 0, "endTime": 5, "audioInput": {"refId": "audio-1", "duration": 5}}]'
```

---

## 📊 Monitoring & Logs

```bash
# View application logs
eb logs

# Stream logs in real-time
eb logs --stream

# View environment health
eb health

# SSH into instance (for debugging)
eb ssh
```

---

## 🔄 CI/CD with GitHub Actions (Optional)

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to AWS Elastic Beanstalk

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Deploy to EB
        uses: einaregilsson/beanstalk-deploy@v21
        with:
          aws_access_key: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws_secret_key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          application_name: video-text-inpainting
          environment_name: video-inpainting-prod
          region: us-east-1
          version_label: ${{ github.sha }}
          deployment_package: deploy.zip
```

---

## 🆘 Troubleshooting

### Issue: Deployment fails with "No space left on device"
**Solution**: Increase EC2 instance type or add EBS volume

### Issue: Database connection timeout
**Solution**: Check RDS security group allows traffic from EB environment

### Issue: Celery worker not processing jobs
**Solution**: Check Redis connection and Celery logs:
```bash
eb ssh
docker logs $(docker ps -q -f name=worker)
```

### Issue: CORS errors from company website
**Solution**: Update `CORS_ORIGINS` environment variable:
```bash
eb setenv CORS_ORIGINS=https://company-website.com,https://www.company-website.com
```

---

## 📞 Next Steps After Deployment

1. ✅ **Get deployment URL** (e.g., `https://video-inpainting-prod.elasticbeanstalk.com`)
2. ✅ **Test all endpoints** (auth, upload, processing)
3. ✅ **Share with company developer**:
   - Deployment URL
   - API documentation (docs/INTEGRATION_GUIDE.md)
   - API key for authentication
4. ✅ **Set up monitoring** (CloudWatch alarms)
5. ✅ **Configure custom domain** (optional)
6. ✅ **Enable HTTPS** (automatic with EB load balancer)

---

## 🤔 Questions?

**Q: Do I need to keep docker-compose.yml?**
A: Yes! Keep it for local development. EB uses `Dockerrun.aws.json` for production.

**Q: How do I update the application?**
A: Just run `git push` and `eb deploy`. That's it!

**Q: Can the company developer access my AWS account?**
A: No! You only share the **deployment URL**. Your AWS account stays private.

**Q: What if I run out of credits/money?**
A: AWS provides **12-month free tier** for new accounts. After that, you can set up billing alarms.

---

**Ready to deploy? Let me know if you want me to help you with the setup!** 🚀
