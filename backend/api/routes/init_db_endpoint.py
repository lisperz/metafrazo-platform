"""
Database initialization endpoint - ONLY for initial setup
"""
from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from backend.models.database import async_session_maker
from backend.auth.jwt_handler import JWTHandler

router = APIRouter()


@router.post("/initialize-database")
async def initialize_database():
    """
    Initialize database with subscription tiers and demo users
    WARNING: This should only be called once during initial setup
    """
    try:
        async with async_session_maker() as session:
            # Check if already initialized
            result = await session.execute(text("SELECT COUNT(*) FROM subscription_tiers"))
            count = result.scalar()

            if count > 0:
                return {"message": "Database already initialized", "tiers_count": count}

            # Initialize subscription tiers
            await session.execute(text("""
                INSERT INTO subscription_tiers (name, display_name, description, price_monthly, price_yearly, credits_per_month, max_video_length_seconds, max_file_size_mb, max_concurrent_jobs, features) VALUES
                ('free', 'Free Tier', 'Perfect for trying out our service', 0, 0, 100, 300, 100, 1, '["basic_processing"]'),
                ('pro', 'Pro Plan', 'For regular users and small businesses', 29.99, 299.99, 1000, 1800, 500, 3, '["basic_processing", "priority_support", "api_access"]'),
                ('enterprise', 'Enterprise Plan', 'For large organizations', 99.99, 999.99, 5000, 7200, 2000, 10, '["basic_processing", "priority_support", "api_access", "custom_models", "dedicated_support"]')
            """))

            # Create demo user
            password_hash = JWTHandler.hash_password("demo123")
            await session.execute(text("""
                INSERT INTO users (email, password_hash, first_name, last_name, subscription_tier_id, credits_balance, email_verified)
                VALUES ('demo@example.com', :password_hash, 'Demo', 'User', 1, 100, true)
            """), {"password_hash": password_hash})

            # Create boss user
            boss_password_hash = JWTHandler.hash_password("boss123")
            await session.execute(text("""
                INSERT INTO users (email, password_hash, first_name, last_name, subscription_tier_id, credits_balance, email_verified)
                VALUES ('boss@example.com', :password_hash, 'Boss', 'User', 2, 1000, true)
            """), {"password_hash": boss_password_hash})

            await session.commit()

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
        raise HTTPException(status_code=500, detail=f"Database initialization failed: {str(e)}")
