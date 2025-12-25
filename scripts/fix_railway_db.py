#!/usr/bin/env python3
"""
Fix Railway database schema - add missing columns for embedded jobs
Run this script to add the missing columns to the video_jobs table.

Usage:
    python scripts/fix_railway_db.py

The script will use DATABASE_URL from your .env file or environment.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decouple import config
import psycopg2


def get_database_url():
    """Get database URL from environment"""
    db_url = config("DATABASE_URL", default=None)
    if not db_url:
        print("ERROR: DATABASE_URL not found in environment or .env file")
        print("\nTo fix this, either:")
        print("1. Add DATABASE_URL to your .env file")
        print("2. Or run: DATABASE_URL='your_railway_url' python scripts/fix_railway_db.py")
        sys.exit(1)
    return db_url


def run_migrations():
    """Run database migrations to add missing columns"""
    db_url = get_database_url()

    print(f"Connecting to database...")
    print(f"URL: {db_url[:50]}...")

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()

        print("\nChecking and adding missing columns to video_jobs table...\n")

        # List of columns to add
        columns_to_add = [
            ("segments_data", "JSONB", None),
            ("job_metadata", "JSONB", "'{}'"),
            ("is_embedded_job", "BOOLEAN", "FALSE"),
            ("is_pro_job", "BOOLEAN", "FALSE"),
        ]

        for col_name, col_type, default in columns_to_add:
            try:
                if default:
                    sql = f"ALTER TABLE video_jobs ADD COLUMN IF NOT EXISTS {col_name} {col_type} DEFAULT {default};"
                else:
                    sql = f"ALTER TABLE video_jobs ADD COLUMN IF NOT EXISTS {col_name} {col_type};"

                cursor.execute(sql)
                print(f"  [OK] Column '{col_name}' checked/added")
            except Exception as e:
                print(f"  [SKIP] Column '{col_name}': {e}")

        # Verify columns exist
        print("\nVerifying video_jobs columns...")
        cursor.execute("""
            SELECT column_name, data_type, column_default
            FROM information_schema.columns
            WHERE table_name = 'video_jobs'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()
        print(f"\nFound {len(columns)} columns in video_jobs table:")
        for col in columns:
            print(f"  - {col[0]}: {col[1]} (default: {col[2]})")

        cursor.close()
        conn.close()

        print("\n" + "="*50)
        print("Database migration completed successfully!")
        print("="*50)
        print("\nYou can now try submitting a video job again.")

    except psycopg2.Error as e:
        print(f"\nDatabase error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
