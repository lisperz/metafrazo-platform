"""
Debug endpoint to test login functionality step by step
"""
from fastapi import APIRouter, Depends, HTTPException
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
