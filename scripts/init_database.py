#!/usr/bin/env python3
"""
Initialize database with subscription tiers and create demo user
"""
import asyncio
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from backend.models.database import async_session_maker, engine
from backend.models.user import User
from backend.auth.password import get_password_hash


async def init_subscription_tiers():
    """Initialize subscription tiers"""
    async with async_session_maker() as session:
        # Check if tiers already exist
        result = await session.execute(text("SELECT COUNT(*) FROM subscription_tiers"))
        count = result.scalar()

        if count > 0:
            print(f"✓ Subscription tiers already initialized ({count} tiers found)")
            return

        print("Initializing subscription tiers...")
        await session.execute(text("""
            INSERT INTO subscription_tiers (name, display_name, description, price_monthly, price_yearly, credits_per_month, max_video_length_seconds, max_file_size_mb, max_concurrent_jobs, features) VALUES
            ('free', 'Free Tier', 'Perfect for trying out our service', 0, 0, 100, 300, 100, 1, '["basic_processing"]'),
            ('pro', 'Pro Plan', 'For regular users and small businesses', 29.99, 299.99, 1000, 1800, 500, 3, '["basic_processing", "priority_support", "api_access"]'),
            ('enterprise', 'Enterprise Plan', 'For large organizations', 99.99, 999.99, 5000, 7200, 2000, 10, '["basic_processing", "priority_support", "api_access", "custom_models", "dedicated_support"]')
        """))
        await session.commit()
        print("✓ Subscription tiers initialized")


async def create_demo_user():
    """Create demo user"""
    async with async_session_maker() as session:
        # Check if demo user exists
        result = await session.execute(
            text("SELECT id FROM users WHERE email = 'demo@example.com'")
        )
        if result.first():
            print("✓ Demo user already exists")
            return

        print("Creating demo user...")
        password_hash = get_password_hash("demo123")

        await session.execute(text("""
            INSERT INTO users (email, password_hash, first_name, last_name, subscription_tier_id, credits_balance, email_verified)
            VALUES ('demo@example.com', :password_hash, 'Demo', 'User', 1, 100, true)
        """), {"password_hash": password_hash})

        await session.commit()
        print("✓ Demo user created (email: demo@example.com, password: demo123)")


async def create_boss_user():
    """Create boss user"""
    async with async_session_maker() as session:
        # Check if boss user exists
        result = await session.execute(
            text("SELECT id FROM users WHERE email = 'boss@example.com'")
        )
        if result.first():
            print("✓ Boss user already exists")
            return

        print("Creating boss user...")
        password_hash = get_password_hash("boss123")

        await session.execute(text("""
            INSERT INTO users (email, password_hash, first_name, last_name, subscription_tier_id, credits_balance, email_verified)
            VALUES ('boss@example.com', :password_hash, 'Boss', 'User', 2, 1000, true)
        """), {"password_hash": password_hash})

        await session.commit()
        print("✓ Boss user created (email: boss@example.com, password: boss123)")


async def main():
    print("=" * 60)
    print("Database Initialization Script")
    print("=" * 60)

    try:
        # Initialize subscription tiers
        await init_subscription_tiers()

        # Create demo users
        await create_demo_user()
        await create_boss_user()

        print("\n" + "=" * 60)
        print("✓ Database initialization completed successfully!")
        print("=" * 60)
        print("\nYou can now log in with:")
        print("  Demo User: demo@example.com / demo123")
        print("  Boss User: boss@example.com / boss123")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
