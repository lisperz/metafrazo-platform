"""
Database initialization endpoint - ONLY for initial setup
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from backend.models.database import get_database
from backend.auth.jwt_handler import JWTHandler

router = APIRouter()


@router.post("/initialize-database")
def initialize_database(db: Session = Depends(get_database)):
    """
    Initialize database with subscription tiers and demo users
    WARNING: This should only be called once during initial setup
    """
    try:
        # Check if already initialized
        result = db.execute(text("SELECT COUNT(*) FROM subscription_tiers"))
        count = result.scalar()

        if count > 0:
            return {"message": "Database already initialized", "tiers_count": count}

        # Initialize subscription tiers
        db.execute(text("""
            INSERT INTO subscription_tiers (name, display_name, description, price_monthly, price_yearly, credits_per_month, max_video_length_seconds, max_file_size_mb, max_concurrent_jobs, features) VALUES
            ('free', 'Free Tier', 'Perfect for trying out our service', 0, 0, 100, 300, 100, 1, '["basic_processing"]'),
            ('pro', 'Pro Plan', 'For regular users and small businesses', 29.99, 299.99, 1000, 1800, 500, 3, '["basic_processing", "priority_support", "api_access"]'),
            ('enterprise', 'Enterprise Plan', 'For large organizations', 99.99, 999.99, 5000, 7200, 2000, 10, '["basic_processing", "priority_support", "api_access", "custom_models", "dedicated_support"]')
        """))

        # Create demo user (password: demo123)
        # Pre-computed bcrypt hash to avoid runtime hashing issues
        demo_hash = "$2b$12$Jmmu8lkVOYy1byb1lfrgd.M7rHRxmLtfefa/oKiXeeOdwa5.rfvwm"
        db.execute(text("""
            INSERT INTO users (email, password_hash, first_name, last_name, subscription_tier_id, credits_balance, email_verified)
            VALUES ('demo@example.com', :password_hash, 'Demo', 'User', 1, 100, true)
        """), {"password_hash": demo_hash})

        # Create boss user (password: boss123)
        boss_hash = "$2b$12$ue6QnVYW3pEcVZ.FqbF7W.VGqE8n2vKZqaALy6uGhXwp5yPzL7yKO"
        db.execute(text("""
            INSERT INTO users (email, password_hash, first_name, last_name, subscription_tier_id, credits_balance, email_verified)
            VALUES ('boss@example.com', :password_hash, 'Boss', 'User', 2, 1000, true)
        """), {"password_hash": boss_hash})

        db.commit()

        return {
            "message": "Database initialized successfully",
            "subscription_tiers": 3,
            "demo_users_created": 2,
            "credentials": {
                "demo_user": {"email": "demo@example.com", "password": "demo123"},
                "boss_user": {"email": "boss@example.com", "password": "boss123"}
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")
