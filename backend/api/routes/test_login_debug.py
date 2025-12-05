"""
Debug endpoint to test login functionality step by step
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.models.database import get_database
from backend.models.user import User
from backend.auth.jwt_handler import JWTHandler

router = APIRouter()


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
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"error": "User not found", "email": email}

        # Generate new hash using JWTHandler
        new_hash = JWTHandler.hash_password(new_password)

        # Update user
        user.password_hash = new_hash
        user.status = "active"
        db.commit()

        return {
            "success": True,
            "email": email,
            "new_hash_prefix": new_hash[:30],
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
            steps.append({"step": 6, "status": "ok", "message": f"Tier: {tier_name}", "tier_id": user.subscription_tier_id})
        except Exception as e:
            return {"error": f"Subscription tier check failed: {str(e)}", "steps": steps, "traceback": traceback.format_exc()}

        # Step 7: Commit
        try:
            db.commit()
            steps.append({"step": 7, "status": "ok", "message": "Committed to database"})
        except Exception as e:
            db.rollback()
            return {"error": f"Commit failed: {str(e)}", "steps": steps, "traceback": traceback.format_exc()}

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
