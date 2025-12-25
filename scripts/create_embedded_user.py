#!/usr/bin/env python3
"""
Create a dedicated user for embedded jobs from phraze.so
This user will own all embedded video jobs.

Usage:
    python scripts/create_embedded_user.py
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decouple import config
import psycopg2
import uuid
import bcrypt


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_embedded_user():
    """Create the embedded user in the database"""
    db_url = config("DATABASE_URL", default=None)
    if not db_url:
        print("ERROR: DATABASE_URL not found in environment or .env file")
        sys.exit(1)

    print(f"Connecting to database...")
    print(f"URL: {db_url[:50]}...")

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()

        # User details
        user_id = "03139de3-8cc6-4702-a2fd-048dff642ccb"
        email = "embedded@phraze.so"
        password_hash = hash_password("phraze-embedded-user-no-login")

        print(f"\nCreating embedded user...")
        print(f"  User ID: {user_id}")
        print(f"  Email: {email}")

        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
        existing = cursor.fetchone()

        if existing:
            print(f"\n✅ User already exists with ID {user_id}")
            cursor.close()
            conn.close()
            return

        # Insert user
        sql = """
            INSERT INTO users (
                id,
                email,
                password_hash,
                first_name,
                last_name,
                email_verified,
                subscription_tier_id,
                credits_balance,
                status,
                user_metadata
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """

        cursor.execute(sql, (
            user_id,
            email,
            password_hash,
            "Phraze.so",
            "Embedded User",
            True,  # email_verified
            20,    # subscription_tier_id (pro tier for embedded jobs)
            999999,  # credits_balance (unlimited for embedded jobs)
            "active",
            '{"source": "phraze.so", "purpose": "embedded_jobs", "note": "This user owns all embedded video jobs from Phraze.so"}'
        ))

        print(f"\n✅ User created successfully!")
        print(f"\n{'='*60}")
        print("Embedded user is ready for use!")
        print(f"{'='*60}")
        print("\nYou can now submit video jobs through the embedded editor.")

        cursor.close()
        conn.close()

    except psycopg2.Error as e:
        print(f"\nDatabase error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_embedded_user()
