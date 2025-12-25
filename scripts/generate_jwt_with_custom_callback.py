#!/usr/bin/env python3
"""
Generate JWT token for embedded editor with custom callback URL
This is useful for local testing with ngrok or production deployment.

Usage:
    # For local testing with ngrok:
    python scripts/generate_jwt_with_custom_callback.py https://abc123.ngrok.io

    # For production phraze.so:
    python scripts/generate_jwt_with_custom_callback.py https://phraze.so
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import jwt


def generate_test_token(base_callback_url: str):
    """Generate a JWT token for testing the embedded editor"""

    # Load the private key for signing
    with open("keys/phraze_private.pem", "r") as f:
        private_key = f.read()

    # Token payload
    now = datetime.utcnow()
    payload = {
        "iss": "phraze.so",
        "sub": "03139de3-8cc6-4702-a2fd-048dff642ccb",  # User ID
        "job_id": f"test-job-{int(now.timestamp())}",
        "video_url": "https://taylorswiftnyu.s3.us-east-2.amazonaws.com/render_9bKalfgxFl2ydKtS1fJv.mp4",
        "callback_url": f"{base_callback_url}/api/open/editor-jobs",
        "permissions": ["edit", "process"],
        "subscription_tier": "pro",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=1)).timestamp()),
        "jti": f"test-{int(now.timestamp())}"
    }

    # Generate token
    token = jwt.encode(payload, private_key, algorithm="RS256")

    print("=" * 80)
    print("JWT Token Generated for Embedded Editor")
    print("=" * 80)
    print()
    print(f"Callback URL: {payload['callback_url']}")
    print(f"Job ID: {payload['job_id']}")
    print(f"User ID: {payload['sub']}")
    print()
    print("=" * 80)
    print("Test URLs:")
    print("=" * 80)
    print()

    # Railway URL
    railway_url = f"https://frontend-production-b02b.up.railway.app/editor/embedded?token={token}"
    print(f"Railway Frontend:")
    print(f"{railway_url}")
    print()

    # Local frontend URL (if running locally)
    local_url = f"http://localhost:3001/editor/embedded?token={token}"
    print(f"Local Frontend (if running):")
    print(f"{local_url}")
    print()

    print("=" * 80)
    print("JWT Token (copy this if needed):")
    print("=" * 80)
    print(token)
    print()

    print("=" * 80)
    print("Next Steps:")
    print("=" * 80)
    print()
    print(f"1. Make sure your Phraze.so backend is running and accessible at:")
    print(f"   {base_callback_url}")
    print()
    print(f"2. Ensure the callback endpoint is ready:")
    print(f"   POST {payload['callback_url']}")
    print()
    print(f"3. Open the test URL in your browser")
    print()
    print(f"4. Submit a video job and watch for callbacks!")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: Please provide the base callback URL")
        print()
        print("Usage examples:")
        print("  # For local testing with ngrok:")
        print("  python scripts/generate_jwt_with_custom_callback.py https://abc123.ngrok.io")
        print()
        print("  # For production phraze.so:")
        print("  python scripts/generate_jwt_with_custom_callback.py https://phraze.so")
        print()
        print("  # For Railway-deployed phraze.so:")
        print("  python scripts/generate_jwt_with_custom_callback.py https://phraze-backend.railway.app")
        sys.exit(1)

    base_url = sys.argv[1].rstrip('/')
    generate_test_token(base_url)
