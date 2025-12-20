"""
Mock routes for testing phraze.so integration
Generates JWT tokens for local development and testing
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from jose import jwt

from backend.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


# For testing, we'll use a test RSA key pair (PKCS#8 format)
# In production, phraze.so would have the private key and we'd only have the public key
TEST_PRIVATE_KEY = """-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQCs1dXgSYFDCi+y
NDurdBPmm1AOMfFoJIczzaLG/sqyvK0jeu3yp86j9bzlfWRBnY5NL751oMXLee0F
FqNoIWO8ZUrl15HcW+nK4hWmkHneXnndrIBMvgYmkS207d0TI81oHY3M7buDnqOB
Q+qBj7MxJjcibeTbFtdnpO2hGqTgskY0WUKA98AH17+GiQgXBeyvjkFL99aNRdSh
ml+TgyJI2727sFGTXlh3eE9SxLVBvgzj6KFu1Ahtn0Y3Y7fI9xSqXuVkNBAiNng6
Ly9N0VenBf8E81lgKvMxS1FsB+p6MFOj38DLq4txOZXjKPpLvcsZ0nRxWNDFIRDg
WBX1nKzHAgMBAAECggEAQrH56KU01nP11+TEKfOPQmwoxnGLYM7HxbvS1su32KVq
gsiLThpnaWoIzN5Ic/Gi2jJUYvv5l/2i81W7FRHddPP5pRw80zY8z+fSxwX1oVP/
3wUUNYkWwoc/hhRMPXiRaV4OPEh5Fd9/5QAaXIjhc1P17rlNmSYFVZ+Ve5fWjEZc
Vw9iYbVAUeFFK0NzFcyhrjTzQ9++pejHBKt45bPWrrk0TaLWPFQebw0l8V3AJ1BC
8mJkp2h1o9LbgneKXxRWSfMzYUfzg2/9dZAFHalpWOEVUqjI1qSUvr0eKMjTxsgH
rhI2fU27XcdeaH4R6bSnFQbT8zQ7iPYHPooFntZ/QQKBgQDk/2LlYPB3+YTCv8Yq
VRoWoSqjRwzQ+LRxZIDL0Haoi4jJTcmKII+F1Oe4fkU49ve22BIHEt1+swxtKUXM
1XYhj3BPPnXwHRT6AbNzNRKloejUYvpdAZWVccK/IsmAZMbBWbQQCvTwYqcgcg5W
TrsIHlU5qHv8+ulO5awhWyJ9sQKBgQDBNxxzV95I5RGVvlANbBWq/HxsRL2lqYw3
OzZPOFypp3XeB5dWoXL7qPybdgRWzrp9dP+RkykJ/86ZG4ddxoMFYjhoOf6ePAps
u7zq02Exa3gV4k+EyYEGqRAQK+YJ4fN/PO5xc3nNfhhg6iUfm4ZOg+bmQsHAhlHp
kq4E1NKX9wKBgQCjgLlS/7ESaITjLFxIU3UKHU69P/ilqD3mDJVtcM2YL/Cdkr3I
stDnBInij73LG4Lo+UN963lcgmjn9CUTSIJNGgZdfkJlC86zZs2C/6ztuDnukzEh
gQUVrCEZqbPnyYyj9vF61ufmTvn3T5hvBU3DUS0Wuva0PU6h95i8RD7PMQKBgQCO
UVrKdxGLXfdK9kie6ls3fAzl7uhGKxHV6O6DAb/3UxsVtT+7FubMCdgvZomhq1pg
aJqLDvtumxcBXe6im0MM5yEnXHh48z62gr6Pta1kqoVkkTMDWy2Hy2XCk6M46k7i
DO6RcH5qZ5PrZux7UKJoGO4t80Ql3IpfYqR9eIm6VwKBgQDMvVu+UkGTk+jBrecV
ymNAhKDBqyXPmknvKiG/jA3xIWtjc5uNvTF0/YjyKDmDdEjVO32kvbmJLtn9e92L
QxulnJPO80kVSq0sXjnYrDpJMm6u8PMbtQHHebY9JkHWIPqz+zjfGXQRg6eORwtF
hZFCIaM3Lgf5qAHTVJplzqrMrw==
-----END PRIVATE KEY-----"""

TEST_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEArNXV4EmBQwovsjQ7q3QT
5ptQDjHxaCSHM82ixv7KsrytI3rt8qfOo/W85X1kQZ2OTS++daDFy3ntBRajaCFj
vGVK5deR3FvpyuIVppB53l553ayATL4GJpEttO3dEyPNaB2NzO27g56jgUPqgY+z
MSY3Im3k2xbXZ6TtoRqk4LJGNFlCgPfAB9e/hokIFwXsr45BS/fWjUXUoZpfk4Mi
SNu9u7BRk15Yd3hPUsS1Qb4M4+ihbtQIbZ9GN2O3yPcUql7lZDQQIjZ4Oi8vTdFX
pwX/BPNZYCrzMUtRbAfqejBTo9/Ay6uLcTmV4yj6S73LGdJ0cVjQxSEQ4FgV9Zys
xwIDAQAB
-----END PUBLIC KEY-----"""


class MockTokenRequest(BaseModel):
    """Request body for generating mock JWT token"""
    user_id: Optional[str] = None
    job_id: Optional[str] = None
    video_url: str
    callback_url: Optional[str] = None
    subscription_tier: str = "normal"  # free, normal, pro, enterprise
    expires_in_hours: int = 1
    frontend_url: Optional[str] = None  # Override frontend URL for Railway testing
    backend_url: Optional[str] = None  # Override backend URL for token validation


class MockTokenResponse(BaseModel):
    """Response containing generated mock JWT token"""
    token: str
    user_id: str
    job_id: str
    video_url: str
    callback_url: str
    subscription_tier: str
    is_pro_user: bool
    expires_at: str
    editor_url: str


@router.post("/generate-token", response_model=MockTokenResponse)
async def generate_mock_token(request: MockTokenRequest):
    """
    Generate a mock JWT token for testing phraze.so integration.
    This simulates what phraze.so would generate when redirecting to the editor.

    Only available in development mode.
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mock token generation is not available in production"
        )

    # Generate IDs if not provided
    user_id = request.user_id or f"mock-user-{uuid.uuid4().hex[:8]}"
    job_id = request.job_id or f"mock-job-{uuid.uuid4().hex[:8]}"
    callback_url = request.callback_url or f"{settings.api_base_url}/api/v1/embedded/mock/callback"

    # Calculate expiration
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=request.expires_in_hours)

    # Validate subscription tier
    valid_tiers = ["free", "normal", "pro", "enterprise"]
    subscription_tier = request.subscription_tier if request.subscription_tier in valid_tiers else "normal"
    is_pro_user = subscription_tier in ["pro", "enterprise"]

    # Create JWT payload
    payload = {
        "sub": user_id,
        "job_id": job_id,
        "video_url": request.video_url,
        "callback_url": callback_url,
        "permissions": ["edit", "process"],
        "subscription_tier": subscription_tier,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp())
    }

    # Sign with RS256
    token = jwt.encode(payload, TEST_PRIVATE_KEY, algorithm="RS256")

    # Generate editor URL - use provided frontend_url or fall back to settings
    base_frontend_url = request.frontend_url or settings.frontend_url
    editor_url = f"{base_frontend_url}/editor/embedded?token={token}"

    # Add backend_url parameter if provided (for testing Railway frontend with local backend)
    if request.backend_url:
        editor_url += f"&backend_url={request.backend_url}"

    logger.info(f"Generated mock token for user {user_id}, job {job_id}, tier {subscription_tier}")

    return MockTokenResponse(
        token=token,
        user_id=user_id,
        job_id=job_id,
        video_url=request.video_url,
        callback_url=callback_url,
        subscription_tier=subscription_tier,
        is_pro_user=is_pro_user,
        expires_at=expires_at.isoformat(),
        editor_url=editor_url
    )


@router.get("/public-key")
async def get_public_key():
    """
    Get the test public key for token verification.
    In production, this would be provided by phraze.so.
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not available in production"
        )

    return {
        "public_key": TEST_PUBLIC_KEY,
        "algorithm": "RS256",
        "note": "This is a test key for development only"
    }


@router.post("/callback")
async def mock_callback(payload: dict):
    """
    Mock callback endpoint that simulates phraze.so receiving job status updates.
    Logs the callback for testing purposes.
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mock callback is not available in production"
        )

    logger.info(f"Mock callback received: {payload}")

    return {
        "received": True,
        "job_id": payload.get("job_id"),
        "status": payload.get("status"),
        "message": "Callback received successfully (mock)"
    }


@router.get("/test-page", response_class=HTMLResponse)
async def mock_test_page():
    """
    Serve a test page for generating tokens and testing the embedded editor flow.
    This simulates the phraze.so interface.
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test page is not available in production"
        )

    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Phraze.so Mock - Editor Integration Test</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                padding: 20px;
            }
            .container {
                max-width: 800px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                padding: 32px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            }
            h1 {
                color: #1a1a2e;
                margin-bottom: 8px;
                font-size: 28px;
            }
            .subtitle {
                color: #666;
                margin-bottom: 32px;
                font-size: 14px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #333;
                font-size: 14px;
            }
            input, select {
                width: 100%;
                padding: 12px 16px;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                font-size: 14px;
                transition: border-color 0.2s;
            }
            input:focus, select:focus {
                outline: none;
                border-color: #667eea;
            }
            .btn {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border: none;
                padding: 14px 28px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                width: 100%;
                transition: transform 0.2s, box-shadow 0.2s;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
            }
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            .result {
                margin-top: 32px;
                padding: 20px;
                background: #f8f9fa;
                border-radius: 12px;
                display: none;
            }
            .result.show { display: block; }
            .result h3 {
                color: #1a1a2e;
                margin-bottom: 16px;
                font-size: 18px;
            }
            .token-box {
                background: #1a1a2e;
                color: #00ff88;
                padding: 16px;
                border-radius: 8px;
                font-family: 'Monaco', 'Menlo', monospace;
                font-size: 12px;
                word-break: break-all;
                margin-bottom: 16px;
                max-height: 150px;
                overflow-y: auto;
            }
            .info-row {
                display: flex;
                justify-content: space-between;
                padding: 8px 0;
                border-bottom: 1px solid #e0e0e0;
                font-size: 14px;
            }
            .info-row:last-child { border-bottom: none; }
            .info-label { color: #666; }
            .info-value { color: #1a1a2e; font-weight: 500; }
            .btn-secondary {
                background: #f0f0f0;
                color: #333;
                margin-top: 12px;
            }
            .btn-secondary:hover {
                background: #e0e0e0;
                box-shadow: none;
                transform: none;
            }
            .callbacks {
                margin-top: 32px;
                padding: 20px;
                background: #fff3cd;
                border-radius: 12px;
                border: 1px solid #ffc107;
            }
            .callbacks h3 {
                color: #856404;
                margin-bottom: 12px;
            }
            .callback-log {
                background: white;
                padding: 12px;
                border-radius: 8px;
                font-family: monospace;
                font-size: 12px;
                max-height: 200px;
                overflow-y: auto;
            }
            .callback-entry {
                padding: 8px;
                border-bottom: 1px solid #eee;
            }
            .callback-entry:last-child { border-bottom: none; }
            .status-started { color: #0066cc; }
            .status-completed { color: #22c55e; }
            .status-failed { color: #ef4444; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Phraze.so Mock Interface</h1>
            <p class="subtitle">Test the embedded editor integration by generating JWT tokens</p>

            <form id="tokenForm">
                <div class="form-group">
                    <label for="videoUrl">Video S3 URL *</label>
                    <input type="url" id="videoUrl" required
                           placeholder="https://s3.amazonaws.com/bucket/video.mp4"
                           value="https://taylorswiftnyu.s3.us-east-2.amazonaws.com/test_video.mp4">
                </div>

                <div class="form-group">
                    <label for="userId">User ID (optional)</label>
                    <input type="text" id="userId" placeholder="Auto-generated if empty">
                </div>

                <div class="form-group">
                    <label for="jobId">Job ID (optional)</label>
                    <input type="text" id="jobId" placeholder="Auto-generated if empty">
                </div>

                <div class="form-group">
                    <label for="subscriptionTier">Subscription Tier</label>
                    <select id="subscriptionTier">
                        <option value="free">Free (Basic Editor)</option>
                        <option value="normal" selected>Normal (Basic Editor)</option>
                        <option value="pro">Pro (Pro Editor)</option>
                        <option value="enterprise">Enterprise (Pro Editor)</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="expiresIn">Token Expiration</label>
                    <select id="expiresIn">
                        <option value="1">1 hour</option>
                        <option value="4">4 hours</option>
                        <option value="24">24 hours</option>
                    </select>
                </div>

                <div class="form-group">
                    <label for="frontendUrl">Frontend URL (for Railway testing)</label>
                    <input type="url" id="frontendUrl"
                           placeholder="https://your-app.railway.app"
                           value="">
                    <small style="color: #666; font-size: 12px;">Leave empty for default (localhost:80). Use your Railway URL to test deployed frontend.</small>
                </div>

                <div class="form-group">
                    <label for="backendUrl">Backend URL (for token validation)</label>
                    <input type="url" id="backendUrl"
                           placeholder="http://localhost:8000"
                           value="">
                    <small style="color: #666; font-size: 12px;">Leave empty for default. Use your local backend URL (http://localhost:8000) when testing Railway frontend with local backend.</small>
                </div>

                <button type="submit" class="btn" id="generateBtn">
                    Generate Token & Open Editor
                </button>
            </form>

            <div class="result" id="result">
                <h3>Generated Token</h3>
                <div class="token-box" id="tokenBox"></div>

                <div class="info-row">
                    <span class="info-label">User ID</span>
                    <span class="info-value" id="resultUserId"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Job ID</span>
                    <span class="info-value" id="resultJobId"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Subscription Tier</span>
                    <span class="info-value" id="resultTier"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Editor Type</span>
                    <span class="info-value" id="resultEditorType"></span>
                </div>
                <div class="info-row">
                    <span class="info-label">Expires At</span>
                    <span class="info-value" id="resultExpires"></span>
                </div>

                <button class="btn" id="openEditorBtn">Open Editor</button>
                <button class="btn btn-secondary" id="copyTokenBtn">Copy Token</button>
            </div>

            <div class="callbacks" id="callbacks">
                <h3>Callback Log</h3>
                <p style="font-size: 12px; color: #856404; margin-bottom: 12px;">
                    Callbacks received from the editor will appear here
                </p>
                <div class="callback-log" id="callbackLog">
                    <em style="color: #999;">No callbacks received yet...</em>
                </div>
            </div>
        </div>

        <script>
            const API_BASE = window.location.origin;
            let generatedToken = null;
            let editorUrl = null;

            document.getElementById('tokenForm').addEventListener('submit', async (e) => {
                e.preventDefault();

                const btn = document.getElementById('generateBtn');
                btn.disabled = true;
                btn.textContent = 'Generating...';

                try {
                    const response = await fetch(`${API_BASE}/api/v1/embedded/mock/generate-token`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            video_url: document.getElementById('videoUrl').value,
                            user_id: document.getElementById('userId').value || null,
                            job_id: document.getElementById('jobId').value || null,
                            subscription_tier: document.getElementById('subscriptionTier').value,
                            expires_in_hours: parseInt(document.getElementById('expiresIn').value),
                            frontend_url: document.getElementById('frontendUrl').value || null,
                            backend_url: document.getElementById('backendUrl').value || null
                        })
                    });

                    if (!response.ok) throw new Error('Failed to generate token');

                    const data = await response.json();
                    generatedToken = data.token;
                    editorUrl = data.editor_url;

                    document.getElementById('tokenBox').textContent = data.token;
                    document.getElementById('resultUserId').textContent = data.user_id;
                    document.getElementById('resultJobId').textContent = data.job_id;
                    document.getElementById('resultTier').textContent = data.subscription_tier.toUpperCase();
                    document.getElementById('resultEditorType').textContent = data.is_pro_user ? 'Pro Video Editor' : 'Basic Video Editor';
                    document.getElementById('resultEditorType').style.color = data.is_pro_user ? '#764ba2' : '#667eea';
                    document.getElementById('resultExpires').textContent = new Date(data.expires_at).toLocaleString();

                    document.getElementById('result').classList.add('show');

                } catch (error) {
                    alert('Error: ' + error.message);
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Generate Token & Open Editor';
                }
            });

            document.getElementById('openEditorBtn').addEventListener('click', () => {
                if (editorUrl) {
                    window.open(editorUrl, '_blank');
                }
            });

            document.getElementById('copyTokenBtn').addEventListener('click', () => {
                if (generatedToken) {
                    navigator.clipboard.writeText(generatedToken);
                    alert('Token copied to clipboard!');
                }
            });

            // Poll for callbacks (in a real scenario, this would be WebSocket or SSE)
            setInterval(async () => {
                // This is just for demonstration - in production you'd use proper real-time updates
            }, 5000);
        </script>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


@router.get("/redirect-to-editor")
async def redirect_to_editor(
    video_url: str = Query(..., description="S3 URL of video to edit"),
    user_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None)
):
    """
    Simulate phraze.so redirect to editor with generated token.
    This is how phraze.so would redirect users to the editor.
    """
    if settings.environment == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not available in production"
        )

    # Generate token
    user_id = user_id or f"mock-user-{uuid.uuid4().hex[:8]}"
    job_id = job_id or f"mock-job-{uuid.uuid4().hex[:8]}"
    callback_url = f"{settings.api_base_url}/api/v1/embedded/mock/callback"

    now = datetime.utcnow()
    expires_at = now + timedelta(hours=1)

    payload = {
        "sub": user_id,
        "job_id": job_id,
        "video_url": video_url,
        "callback_url": callback_url,
        "permissions": ["edit", "process"],
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp())
    }

    token = jwt.encode(payload, TEST_PRIVATE_KEY, algorithm="RS256")

    # Redirect to embedded editor
    editor_url = f"{settings.frontend_url}/editor/embedded?token={token}"

    return RedirectResponse(url=editor_url, status_code=302)
