#!/usr/bin/env python3
"""
Complete end-to-end test for Phraze.so + MetaFrazo integration

This script:
1. Creates a job in Phraze.so database
2. Generates a JWT token for that job
3. Outputs test URLs

Usage:
    python3 scripts/test_phraze_callback_flow.py https://YOUR-NGROK-URL.ngrok.io
"""

import sys
import os
import uuid
from datetime import datetime, timedelta
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt


def create_editor_job(phraze_base_url: str, user_id: str, video_url: str) -> str:
    """Create a job in Phraze.so database and return the job ID"""

    print("📝 Step 1: Creating editor job in Phraze.so database...")

    endpoint = f"{phraze_base_url}/api/open/editor-jobs"

    payload = {
        "user_id": user_id,
        "video_url": video_url,
        "processing_type": "lip_sync",
        "status": "pending"
    }

    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()

        data = response.json()
        if data.get("success") and data.get("data"):
            job_id = data["data"]["id"]
            print(f"✅ Job created successfully!")
            print(f"   Job ID: {job_id}")
            print(f"   Status: {data['data'].get('status', 'pending')}")
            return job_id
        else:
            print(f"❌ Failed to create job: {data}")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating job: {e}")
        print(f"\n⚠️  Make sure Phraze.so is running at {phraze_base_url}")
        sys.exit(1)


def generate_jwt_token(job_id: str, user_id: str, video_url: str, callback_url: str) -> str:
    """Generate JWT token for the created job"""

    print("\n🔑 Step 2: Generating JWT token...")

    # Load the private key for signing
    key_path = "keys/phraze_private.pem"
    if not os.path.exists(key_path):
        print(f"❌ Private key not found: {key_path}")
        sys.exit(1)

    with open(key_path, "r") as f:
        private_key = f.read()

    # Token payload
    now = datetime.utcnow()
    payload = {
        "iss": "phraze.so",
        "sub": user_id,
        "job_id": job_id,
        "video_url": video_url,
        "callback_url": callback_url,
        "permissions": ["edit", "process"],
        "subscription_tier": "pro",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=1)).timestamp()),
        "jti": str(uuid.uuid4())
    }

    # Generate token
    token = jwt.encode(payload, private_key, algorithm="RS256")

    print(f"✅ JWT token generated!")
    print(f"   Expires: {datetime.fromtimestamp(payload['exp']).strftime('%Y-%m-%d %H:%M:%S')}")

    return token


def main():
    if len(sys.argv) < 2:
        print("❌ ERROR: Please provide the ngrok URL")
        print()
        print("Usage:")
        print("  python3 scripts/test_phraze_callback_flow.py https://YOUR-NGROK-URL.ngrok.io")
        print()
        print("Example:")
        print("  python3 scripts/test_phraze_callback_flow.py https://abc123.ngrok.io")
        sys.exit(1)

    ngrok_url = sys.argv[1].rstrip('/')

    # Configuration
    user_id = "03139de3-8cc6-4702-a2fd-048dff642ccb"
    video_url = "https://taylorswiftnyu.s3.us-east-2.amazonaws.com/render_9bKalfgxFl2ydKtS1fJv.mp4"
    callback_url = f"{ngrok_url}/api/open/editor-jobs"

    print("=" * 80)
    print("Phraze.so + MetaFrazo Integration Test")
    print("=" * 80)
    print()
    print(f"ngrok URL: {ngrok_url}")
    print(f"Callback URL: {callback_url}")
    print(f"User ID: {user_id}")
    print()
    print("=" * 80)
    print()

    # Step 1: Create job in Phraze.so database
    job_id = create_editor_job(ngrok_url, user_id, video_url)

    # Step 2: Generate JWT token
    token = generate_jwt_token(job_id, user_id, video_url, callback_url)

    # Step 3: Output test URLs
    print()
    print("=" * 80)
    print("🎉 Setup Complete! Ready to Test")
    print("=" * 80)
    print()

    editor_phraze_url = f"https://editor.phraze.so/editor/embedded?token={token}"
    railway_url = f"https://frontend-production-b02b.up.railway.app/editor/embedded?token={token}"
    local_url = f"http://localhost:3001/editor/embedded?token={token}"

    print("📋 Test URLs:")
    print()
    print("🌟 Editor.phraze.so (PRODUCTION - recommended):")
    print(f"{editor_phraze_url}")
    print()
    print("Railway Frontend (backup):")
    print(f"{railway_url}")
    print()
    print("Local Frontend (if running):")
    print(f"{local_url}")
    print()

    print("=" * 80)
    print("Next Steps:")
    print("=" * 80)
    print()
    print("1. ✅ Phraze.so running at: http://localhost:3000")
    print("2. ✅ ngrok tunnel active")
    print("3. ✅ Editor job created in database")
    print("4. ✅ JWT token generated")
    print()
    print("5. 🌐 Open the editor.phraze.so URL above in your browser")
    print("6. 🎬 Edit the video and submit the job")
    print("7. 👀 Watch your Phraze.so terminal for callbacks:")
    print()
    print("   You should see:")
    print("   📥 MetaFrazo callback received via POST: { job_id: '...', status: 'started' }")
    print("   ✅ MetaFrazo callback processed successfully")
    print()
    print("   ... wait 1-2 minutes ...")
    print()
    print("   📥 MetaFrazo callback received via POST: { job_id: '...', status: 'completed' }")
    print("   ✅ MetaFrazo callback processed successfully")
    print()
    print("8. ✅ Verify in database:")
    print(f"   curl '{ngrok_url}/api/open/editor-jobs?id={job_id}' | jq")
    print()
    print("=" * 80)
    print()
    print("Job ID for reference: " + job_id)
    print()


if __name__ == "__main__":
    main()
