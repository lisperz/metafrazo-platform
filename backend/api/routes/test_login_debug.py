"""
Debug endpoint to test login functionality step by step
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.models.database import get_database
from backend.models.user import User

router = APIRouter()


@router.post("/debug-login")
def debug_login(email: str, password: str, db: Session = Depends(get_database)):
    """Debug login to see where it fails"""
    try:
        # Step 1: Find user
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {"error": "User not found", "email": email}

        # Step 2: Check password
        try:
            password_valid = user.check_password(password)
            if not password_valid:
                return {"error": "Password invalid", "password_hash_sample": user.password_hash[:20]}
        except Exception as e:
            return {"error": f"Password check failed: {str(e)}", "type": str(type(e))}

        # Step 3: Check status
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
