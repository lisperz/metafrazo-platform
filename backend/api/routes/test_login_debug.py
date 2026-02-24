"""
Debug endpoint to test login functionality and services
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.models.database import get_database
from backend.models.user import User
from backend.auth.jwt_handler import JWTHandler

router = APIRouter()


@router.get("/check-services")
def check_services():
    """Check if S3 and Sync.so services are properly configured"""
    from backend.config import settings
    import os

    # Get raw credentials for debugging (safely)
    aws_key = (settings.aws_access_key_id or "").strip()
    aws_secret = (settings.aws_secret_access_key or "").strip()

    results = {
        "aws": {
            "access_key_configured": bool(aws_key),
            "access_key_length": len(aws_key),
            "access_key_preview": f"{aws_key[:4]}...{aws_key[-4:]}" if len(aws_key) > 8 else "TOO_SHORT",
            "secret_key_configured": bool(aws_secret),
            "secret_key_length": len(aws_secret),
            "region": settings.aws_region,
            "bucket": settings.aws_s3_bucket,
        },
        "sync_so": {
            "api_key_configured": bool(settings.sync_api_key),
            "api_url": settings.sync_api_url,
        },
        "ghostcut": {
            "api_key_configured": bool(settings.ghostcut_api_key),
            "app_key_configured": bool(settings.ghostcut_app_key),
            "app_secret_configured": bool(settings.ghostcut_app_secret),
        },
        "environment": {
            "environment": settings.environment,
            "debug": settings.debug,
            "cors_origins": settings.cors_origins,
        }
    }

    # Test S3 connection
    try:
        from backend.services.s3 import s3_service
        results["aws"]["s3_service_initialized"] = True
        results["aws"]["bucket_name"] = s3_service.bucket_name

        # Test actual S3 connection
        try:
            connection_ok = s3_service.test_connection()
            results["aws"]["s3_connection_test"] = "SUCCESS" if connection_ok else "FAILED"
        except Exception as conn_e:
            results["aws"]["s3_connection_test"] = f"ERROR: {str(conn_e)}"
    except Exception as e:
        results["aws"]["s3_service_initialized"] = False
        results["aws"]["s3_error"] = str(e)

    # Test Sync.so service
    try:
        from backend.services.sync_segments_service import sync_segments_service
        results["sync_so"]["service_initialized"] = True
        results["sync_so"]["has_api_key"] = bool(sync_segments_service.api_key)
    except Exception as e:
        results["sync_so"]["service_initialized"] = False
        results["sync_so"]["error"] = str(e)

    return results


@router.get("/test-s3-upload")
def test_s3_upload():
    """Test S3 upload with a small test file"""
    import tempfile
    import os
    from backend.config import settings

    results = {
        "test_started": True,
        "credentials": {
            "access_key_set": bool(settings.aws_access_key_id),
            "secret_key_set": bool(settings.aws_secret_access_key),
            "region": settings.aws_region,
            "bucket": settings.aws_s3_bucket
        }
    }

    try:
        from backend.services.s3 import s3_service

        # Create a small test file
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.txt', delete=False
        ) as f:
            f.write("S3 upload test from video inpainting service")
            test_file_path = f.name

        try:
            # Try to upload the test file
            test_key = f"test/s3-test-{os.getpid()}.txt"
            results["test_key"] = test_key

            s3_service.s3_client.upload_file(
                test_file_path,
                s3_service.bucket_name,
                test_key
            )
            results["upload_success"] = True
            results["public_url"] = s3_service.get_public_url(test_key)

            # Clean up - delete the test file from S3
            s3_service.delete_file(test_key)
            results["cleanup_success"] = True

        except Exception as upload_e:
            results["upload_success"] = False
            results["upload_error"] = str(upload_e)
            results["error_type"] = type(upload_e).__name__

        finally:
            # Clean up local temp file
            if os.path.exists(test_file_path):
                os.unlink(test_file_path)

    except Exception as e:
        results["service_error"] = str(e)
        results["error_type"] = type(e).__name__

    return results


@router.post("/debug-login")
def debug_login(email: str, password: str, db: Session = Depends(get_database)):
    """Debug login to see where it fails"""
    try:
        # Step 1: Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"error": "User not found", "email": email}

        # Step 2: Show hash info
        hash_info = {
            "hash_length": len(user.password_hash) if user.password_hash else 0,
            "hash_prefix": user.password_hash[:30] if user.password_hash else None,
            "starts_with_2b": user.password_hash.startswith("$2b$") if user.password_hash else False,
        }

        # Step 3: Check password
        try:
            password_valid = user.check_password(password)
            if not password_valid:
                return {"error": "Password invalid", "hash_info": hash_info}
        except Exception as e:
            return {"error": f"Password check failed: {str(e)}", "type": str(type(e)), "hash_info": hash_info}

        # Step 4: Check status
        if user.status != "active":
            return {"error": f"User status is {user.status}, not active"}

        # Success
        return {
            "success": True,
            "user_email": user.email,
            "user_status": user.status,
            "user_id": str(user.id)
        }

    except Exception as e:
        import traceback
        return {
            "error": "Exception occurred",
            "message": str(e),
            "traceback": traceback.format_exc()
        }


@router.post("/reset-user-password")
def reset_user_password(email: str, new_password: str, db: Session = Depends(get_database)):
    """Reset a user's password with a properly hashed password"""
    from datetime import datetime

    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"error": "User not found", "email": email}

        # Generate new hash using JWTHandler
        new_hash = JWTHandler.hash_password(new_password)

        # Update user
        user.password_hash = new_hash
        user.status = "active"

        # Fix created_at if null
        if user.created_at is None:
            user.created_at = datetime.utcnow()

        db.commit()

        return {
            "success": True,
            "email": email,
            "new_hash_prefix": new_hash[:30],
            "created_at_fixed": user.created_at is not None,
            "message": "Password reset successfully"
        }

    except Exception as e:
        db.rollback()
        import traceback
        return {
            "error": "Exception occurred",
            "message": str(e),
            "traceback": traceback.format_exc()
        }


@router.post("/test-full-login")
def test_full_login(email: str, password: str, request: Request, db: Session = Depends(get_database)):
    """Test the full login flow step by step"""
    import traceback
    from backend.models.user import UserSession

    steps = []

    try:
        # Step 1: Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"error": "User not found", "steps": steps}
        steps.append({"step": 1, "status": "ok", "message": "User found"})

        # Step 2: Check password
        if not user.check_password(password):
            return {"error": "Invalid password", "steps": steps}
        steps.append({"step": 2, "status": "ok", "message": "Password valid"})

        # Step 3: Check status
        if user.status != "active":
            return {"error": f"User status is {user.status}", "steps": steps}
        steps.append({"step": 3, "status": "ok", "message": "User active"})

        # Step 4: Create session
        try:
            session = UserSession.create_session(
                user_id=user.id,
                ip_address=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown")
            )
            db.add(session)
            steps.append({"step": 4, "status": "ok", "message": "Session created"})
        except Exception as e:
            return {"error": f"Session creation failed: {str(e)}", "steps": steps, "traceback": traceback.format_exc()}

        # Step 5: Create tokens
        try:
            access_token = JWTHandler.create_access_token({"sub": str(user.id)})
            refresh_token = JWTHandler.create_refresh_token({"sub": str(user.id)})
            session.session_token = access_token
            session.refresh_token = refresh_token
            steps.append({"step": 5, "status": "ok", "message": "Tokens created"})
        except Exception as e:
            return {"error": f"Token creation failed: {str(e)}", "steps": steps, "traceback": traceback.format_exc()}

        # Step 6: Check subscription tier
        try:
            tier_name = "free"
            if user.subscription_tier:
                tier_name = user.subscription_tier.name
            steps.append({
                "step": 6,
                "status": "ok",
                "message": f"Tier: {tier_name}",
                "tier_id": user.subscription_tier_id,
                "created_at": str(user.created_at) if user.created_at else None,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email_verified": user.email_verified,
                "credits_balance": user.credits_balance
            })
        except Exception as e:
            return {"error": f"Subscription tier check failed: {str(e)}", "steps": steps, "traceback": traceback.format_exc()}

        # Step 7: Commit
        try:
            db.commit()
            steps.append({"step": 7, "status": "ok", "message": "Committed to database"})
        except Exception as e:
            db.rollback()
            return {"error": f"Commit failed: {str(e)}", "steps": steps, "traceback": traceback.format_exc()}

        # Step 8: Build UserResponse (this is where actual login fails)
        try:
            from backend.api.routes.auth.schemas import UserResponse
            tier_name = "free"
            if user.subscription_tier:
                tier_name = user.subscription_tier.name

            user_response = UserResponse(
                id=str(user.id),
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                company=user.company,
                email_verified=user.email_verified,
                subscription_tier=tier_name,
                credits_balance=user.credits_balance,
                created_at=user.created_at
            )
            steps.append({"step": 8, "status": "ok", "message": "UserResponse built successfully"})
        except Exception as e:
            return {"error": f"UserResponse build failed: {str(e)}", "steps": steps, "traceback": traceback.format_exc()}

        # Step 9: Build TokenResponse
        try:
            from backend.api.routes.auth.schemas import TokenResponse
            from backend.config import settings

            token_response = TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=settings.access_token_expire_minutes * 60,
                user=user_response
            )
            steps.append({"step": 9, "status": "ok", "message": "TokenResponse built successfully"})
        except Exception as e:
            return {"error": f"TokenResponse build failed: {str(e)}", "steps": steps, "traceback": traceback.format_exc()}

        return {
            "success": True,
            "steps": steps,
            "access_token_prefix": access_token[:50] + "...",
            "user_id": str(user.id)
        }

    except Exception as e:
        return {
            "error": "Unexpected exception",
            "message": str(e),
            "steps": steps,
            "traceback": traceback.format_exc()
        }
