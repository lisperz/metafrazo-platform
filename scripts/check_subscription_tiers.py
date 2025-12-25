#!/usr/bin/env python3
"""Check existing subscription tiers in the database"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decouple import config
import psycopg2

db_url = config("DATABASE_URL", default=None)
if not db_url:
    print("ERROR: DATABASE_URL not found")
    sys.exit(1)

conn = psycopg2.connect(db_url)
cursor = conn.cursor()

cursor.execute("SELECT id, name, display_name FROM subscription_tiers ORDER BY id")
tiers = cursor.fetchall()

if tiers:
    print("Existing subscription tiers:")
    for tier in tiers:
        print(f"  ID: {tier[0]}, Name: {tier[1]}, Display: {tier[2]}")
else:
    print("No subscription tiers found!")

cursor.close()
conn.close()
