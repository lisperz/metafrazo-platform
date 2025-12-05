╔═══════════════════════════════════════════════════════╗
║    🚂 RAILWAY DEPLOYMENT - 3-MINUTE QUICK START 🚂     ║
╚═══════════════════════════════════════════════════════╝

📋 BEFORE YOU START:

Have ready:
✓ GhostCut API key
✓ Sync.so API key  
✓ AWS S3 credentials

───────────────────────────────────────────────────────

🚀 STEP 1: INSTALL RAILWAY CLI (1 min)

npm install -g @railway/cli

───────────────────────────────────────────────────────

🚀 STEP 2: RUN DEPLOYMENT SCRIPT (10 min)

./deploy_to_railway.sh

This script will:
✓ Login to Railway
✓ Create project
✓ Add PostgreSQL database
✓ Add Redis cache
✓ Deploy your app
✓ Generate public URL

───────────────────────────────────────────────────────

🚀 STEP 3: SET ENVIRONMENT VARIABLES (2 min)

railway variables set \
  GHOSTCUT_API_KEY="your-key" \
  SYNC_API_KEY="your-key" \
  AWS_ACCESS_KEY_ID="your-key" \
  AWS_SECRET_ACCESS_KEY="your-secret" \
  AWS_S3_BUCKET="your-bucket"

───────────────────────────────────────────────────────

🚀 STEP 4: GET YOUR URL (instant)

railway domain

Copy this URL! → https://backend-xxxx.up.railway.app

───────────────────────────────────────────────────────

🚀 STEP 5: TEST (1 min)

curl https://YOUR-URL.up.railway.app/health

───────────────────────────────────────────────────────

🚀 STEP 6: SHARE WITH COMPANY DEVELOPER

Send them:
• Backend URL: https://YOUR-URL.up.railway.app
• API Docs: https://YOUR-URL.up.railway.app/docs
• Integration Guide: docs/INTEGRATION_GUIDE.md

✅ DONE! Total time: ~15 minutes

───────────────────────────────────────────────────────

💡 HELPFUL COMMANDS:

View logs:     railway logs
Check status:  railway status  
Redeploy:      railway up
Open dashboard: railway open

───────────────────────────────────────────────────────

📖 FULL DOCUMENTATION:

• RAILWAY_CHECKLIST.md - Detailed checklist
• docs/RAILWAY_DEPLOYMENT.md - Complete guide

───────────────────────────────────────────────────────

🆘 NEED HELP?

Just ask me! I'm here to help with every step.

╚═══════════════════════════════════════════════════════╝
