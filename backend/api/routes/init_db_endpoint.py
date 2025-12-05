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
        # Check if subscription tiers exist
        result = db.execute(text("SELECT COUNT(*) FROM subscription_tiers"))
        tiers_count = result.scalar()

        if tiers_count == 0:
            # Initialize subscription tiers
            db.execute(text("""
                INSERT INTO subscription_tiers (name, display_name, description, price_monthly, price_yearly, credits_per_month, max_video_length_seconds, max_file_size_mb, max_concurrent_jobs, features) VALUES
                ('free', 'Free Tier', 'Perfect for trying out our service', 0, 0, 100, 300, 100, 1, '["basic_processing"]'),
                ('pro', 'Pro Plan', 'For regular users and small businesses', 29.99, 299.99, 1000, 1800, 500, 3, '["basic_processing", "priority_support", "api_access"]'),
                ('enterprise', 'Enterprise Plan', 'For large organizations', 99.99, 999.99, 5000, 7200, 2000, 10, '["basic_processing", "priority_support", "api_access", "custom_models", "dedicated_support"]')
            """))

        # Get tier IDs dynamically
        free_tier_result = db.execute(text("SELECT id FROM subscription_tiers WHERE name = 'free'")).first()
        pro_tier_result = db.execute(text("SELECT id FROM subscription_tiers WHERE name = 'pro'")).first()

        if not free_tier_result or not pro_tier_result:
            raise Exception("Subscription tiers not found. Database may be corrupted.")

        free_tier_id = free_tier_result[0]
        pro_tier_id = pro_tier_result[0]

        # Check and create demo user (password: demo123)
        demo_exists = db.execute(text("SELECT COUNT(*) FROM users WHERE email = 'demo@example.com'")).scalar()
        users_created = 0

        if demo_exists == 0:
            demo_hash = "$2b$12$Jmmu8lkVOYy1byb1lfrgd.M7rHRxmLtfefa/oKiXeeOdwa5.rfvwm"
            db.execute(text("""
                INSERT INTO users (id, email, password_hash, first_name, last_name, subscription_tier_id, credits_balance, email_verified, status)
                VALUES (gen_random_uuid(), 'demo@example.com', :password_hash, 'Demo', 'User', :tier_id, 100, true, 'active')
            """), {"password_hash": demo_hash, "tier_id": free_tier_id})
            users_created += 1
        else:
            # Update existing user to active status
            db.execute(text("UPDATE users SET status = 'active' WHERE email = 'demo@example.com'"))

        # Check and create boss user (password: boss123)
        boss_exists = db.execute(text("SELECT COUNT(*) FROM users WHERE email = 'boss@example.com'")).scalar()

        if boss_exists == 0:
            boss_hash = "$2b$12$ue6QnVYW3pEcVZ.FqbF7W.VGqE8n2vKZqaALy6uGhXwp5yPzL7yKO"
            db.execute(text("""
                INSERT INTO users (id, email, password_hash, first_name, last_name, subscription_tier_id, credits_balance, email_verified, status)
                VALUES (gen_random_uuid(), 'boss@example.com', :password_hash, 'Boss', 'User', :tier_id, 1000, true, 'active')
            """), {"password_hash": boss_hash, "tier_id": pro_tier_id})
            users_created += 1
        else:
            # Update existing user to active status
            db.execute(text("UPDATE users SET status = 'active' WHERE email = 'boss@example.com'"))

        db.commit()

        return {
            "message": "Database initialization completed",
            "subscription_tiers_existed": tiers_count > 0,
            "subscription_tiers_created": 3 if tiers_count == 0 else 0,
            "users_created": users_created,
            "credentials": {
                "demo_user": {"email": "demo@example.com", "password": "demo123"},
                "boss_user": {"email": "boss@example.com", "password": "boss123"}
            }
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")
