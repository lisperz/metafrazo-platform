"""
Phraze.so token validation using RS256 JWT
"""

import hmac
import hashlib
import logging
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from fastapi import Request, HTTPException, status
from jose import jwt, JWTError

from backend.config import settings
from .schemas import PhrazeTokenPayload, ErrorResponse

logger = logging.getLogger(__name__)


class PhrazeValidator:
    """Validates requests coming from phraze.so using RS256 JWT"""

    _public_key: Optional[str] = None

    @classmethod
    def get_public_key(cls) -> str:
        """Get the public key for RS256 verification"""
        if cls._public_key is not None:
            return cls._public_key

        # Try loading from environment variable first
        if settings.phraze_public_key:
            cls._public_key = settings.phraze_public_key
            logger.info("Loaded Phraze public key from environment variable")
            return cls._public_key

        # Try loading from file path
        if settings.phraze_public_key_path:
            try:
                with open(settings.phraze_public_key_path, 'r') as f:
                    cls._public_key = f.read()
                logger.info(f"Loaded Phraze public key from {settings.phraze_public_key_path}")
                return cls._public_key
            except FileNotFoundError:
                logger.warning(f"Public key file not found: {settings.phraze_public_key_path}")

        # For development/testing, allow empty key (will use mock validation)
        if settings.environment == "development":
            logger.warning("No Phraze public key configured - using development mode")
            return ""

        raise ValueError("Phraze public key not configured")

    @classmethod
    def validate_token(cls, token: str) -> PhrazeTokenPayload:
        """
        Validate JWT token from phraze.so using RS256
        Returns decoded payload if valid, raises HTTPException if invalid
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    error_code="TOKEN_MISSING",
                    message="Authentication token is required",
                    redirect_url=f"https://{settings.phraze_domain}"
                ).model_dump()
            )

        try:
            public_key = cls.get_public_key()
            logger.info(f"Environment: {settings.environment}, public_key present: {bool(public_key)}")

            # For development without public key, decode without verification
            if not public_key and settings.environment == "development":
                logger.info("Using development mode - decoding without verification")
                # jose library requires a key parameter even when verify_signature is False
                # Use a dummy key and disable all verification
                payload = jwt.decode(
                    token,
                    "",  # Empty key since we're not verifying
                    algorithms=["RS256", "HS256"],  # Accept both since we're not verifying
                    options={
                        "verify_signature": False,
                        "verify_aud": False,
                        "verify_iss": False,
                        "verify_sub": False,
                        "verify_jti": False,
                        "verify_at_hash": False,
                    }
                )
            else:
                logger.info("Using production mode - verifying with RS256")
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    options={"verify_aud": False}
                )

            logger.info(f"Token decoded successfully: {payload}")

            # Validate required fields
            token_payload = PhrazeTokenPayload(**payload)

            # Check expiration
            if token_payload.is_expired:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=ErrorResponse(
                        error_code="TOKEN_EXPIRED",
                        message="Your session has expired. Please return to phraze.so to continue.",
                        redirect_url=f"https://{settings.phraze_domain}",
                        job_id=token_payload.job_id
                    ).model_dump()
                )

            logger.info(f"Token validated for user {token_payload.user_id}, job {token_payload.job_id}")
            return token_payload

        except JWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ErrorResponse(
                    error_code="TOKEN_INVALID",
                    message="Invalid authentication token",
                    redirect_url=f"https://{settings.phraze_domain}"
                ).model_dump()
            )
        except ValueError as e:
            logger.error(f"Token payload validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="TOKEN_MALFORMED",
                    message="Token payload is malformed",
                    redirect_url=f"https://{settings.phraze_domain}"
                ).model_dump()
            )

    @classmethod
    def validate_referrer(cls, request: Request) -> bool:
        """Check if request originates from phraze.so"""
        referrer = request.headers.get("referer", "")
        origin = request.headers.get("origin", "")

        # In development mode, allow local testing
        if settings.environment == "development":
            local_origins = ["localhost", "127.0.0.1"]
            if any(local in referrer or local in origin for local in local_origins):
                return True

        return (
            settings.phraze_domain in referrer or
            settings.phraze_domain in origin
        )

    @classmethod
    def validate_s3_url(cls, url: str) -> bool:
        """Ensure S3 URL is from allowed domains"""
        if not url:
            return False

        parsed = urlparse(url)

        # Allow our own bucket domain patterns
        allowed_patterns = [
            "s3.amazonaws.com",
            "s3.us-east-2.amazonaws.com",
            ".s3.amazonaws.com",
            ".s3.us-east-2.amazonaws.com",
            "taylorswiftnyu.s3",  # Our bucket
        ]

        for pattern in allowed_patterns:
            if pattern in parsed.netloc:
                return True

        # Check configured allowed domains
        for domain in settings.allowed_s3_domains_list:
            if domain in parsed.netloc:
                return True

        return False

    @classmethod
    def generate_callback_signature(cls, payload: dict) -> str:
        """Generate HMAC signature for callback payload"""
        if not settings.callback_hmac_secret:
            logger.warning("No callback HMAC secret configured")
            return ""

        # Create deterministic string from payload
        message_parts = [
            payload.get("job_id", ""),
            payload.get("status", ""),
            payload.get("output_url", ""),
            payload.get("timestamp", "")
        ]
        message = "|".join(str(p) for p in message_parts)

        signature = hmac.new(
            settings.callback_hmac_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature

    @classmethod
    async def validate_embedded_request(
        cls,
        request: Request,
        token: str
    ) -> PhrazeTokenPayload:
        """
        Full validation of incoming embedded request
        Returns validated token payload
        """
        # Validate referrer (optional in development)
        if not cls.validate_referrer(request):
            logger.warning(f"Request from invalid origin: {request.headers.get('origin')}")
            # Don't block, just log - tokens are the primary auth mechanism

        # Validate token
        token_payload = cls.validate_token(token)

        # Validate S3 URL from token
        if not cls.validate_s3_url(token_payload.video_url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ErrorResponse(
                    error_code="INVALID_VIDEO_URL",
                    message="Video URL is not from an allowed source",
                    redirect_url=f"https://{settings.phraze_domain}",
                    job_id=token_payload.job_id
                ).model_dump()
            )

        return token_payload
