#!/usr/bin/env python3
"""
Add job_metadata column to video_jobs table
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

import psycopg2

def run_migration():
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="vti_db",
        user="vti_user",
        password=os.getenv("DB_PASSWORD", "vti_password_123")
    )

    cursor = conn.cursor()

    try:
        # Add job_metadata column if it doesn't exist
        cursor.execute("""
            ALTER TABLE video_jobs
            ADD COLUMN IF NOT EXISTS job_metadata JSONB DEFAULT '{}'::jsonb;
        """)
        conn.commit()
        print("Successfully added job_metadata column to video_jobs table")
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
