#!/usr/bin/env python3
"""
Generate JWT tokens for Phraze.so -> Metafrazo integration testing.

This script simulates what Phraze.so would do to generate a JWT token
for embedding the Metafrazo editor.

Usage:
    python scripts/generate_jwt_token.py

The generated token can be used to test the embedded editor at:
    http://localhost:3001/editor/embedded?token=<generated_token>
"""

import jwt
import datetime
import uuid
import sys
import os

# Path to private key
PRIVATE_KEY_PATH = os.path.join(os.path.dirname(__file__), "../keys/phraze_private.pem")

def load_private_key() -> str:
    """Load the RSA private key from file."""
    with open(PRIVATE_KEY_PATH, "r") as f:
        return f.read()

def generate_token(
    user_id: str,
    job_id: str,
    video_url: str,
    callback_url: str,
    subscription_tier: str = "pro",
    expires_in_hours: int = 24
) -> str:
    """
    Generate a JWT token for Metafrazo embedded editor.

    Args:
        user_id: Phraze.so user ID
        job_id: Phraze.so job ID
        video_url: S3 URL of the video to edit
        callback_url: URL to send completion/failure callbacks
        subscription_tier: User subscription tier (free, normal, pro, enterprise)
        expires_in_hours: Token expiration time in hours

    Returns:
        Signed JWT token string
    """
    private_key = load_private_key()

    now = datetime.datetime.utcnow()
    exp = now + datetime.timedelta(hours=expires_in_hours)

    # Payload must match PhrazeTokenPayload schema in backend
    payload = {
        "iss": "phraze.so",
        "sub": user_id,                          # Required - maps to user_id
        "job_id": job_id,                        # Required
        "video_url": video_url,                  # Required
        "callback_url": callback_url,            # Required
        "permissions": ["edit", "process"],      # Required field
        "subscription_tier": subscription_tier,  # Required field
        "iat": int(now.timestamp()),             # Required
        "exp": int(exp.timestamp()),             # Required
        "jti": str(uuid.uuid4()),                # Optional JWT ID
    }

    token = jwt.encode(payload, private_key, algorithm="RS256")
    return token

def main():
    # Example values - modify these for your testing
    user_id = "03139de3-8cc6-4702-a2fd-048dff642ccb"  # From Phraze.so
    job_id = str(uuid.uuid4())  # Generate new job ID
    video_url = "https://taylorswiftnyu.s3.us-east-2.amazonaws.com/render_9bKalfgxFl2ydKtS1fJv.mp4"
    callback_url = "http://localhost:3000/api/open/editor-jobs"  # Phraze.so callback endpoint

    print("=" * 70)
    print("JWT Token Generator for Metafrazo Integration")
    print("=" * 70)
    print()
    print("Token Parameters:")
    print(f"  user_id:           {user_id}")
    print(f"  job_id:            {job_id}")
    print(f"  video_url:         {video_url}")
    print(f"  callback_url:      {callback_url}")
    print(f"  subscription_tier: pro")
    print()

    token = generate_token(
        user_id=user_id,
        job_id=job_id,
        video_url=video_url,
        callback_url=callback_url,
        subscription_tier="pro"
    )

    print("Generated JWT Token:")
    print("-" * 70)
    print(token)
    print("-" * 70)
    print()
    print("Test URLs:")
    print(f"  Railway: https://frontend-production-b02b.up.railway.app/editor/embedded?token={token}")
    print(f"  Local:   http://localhost:3001/editor/embedded?token={token}")
    print()
    print("Backend validation test:")
    print(f"  curl 'https://backend-production-268a.up.railway.app/api/v1/embedded/validate?token={token}'")
    print()
    print("Decode token at: https://jwt.io")
    print()

if __name__ == "__main__":
    main()
