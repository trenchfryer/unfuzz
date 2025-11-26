#!/usr/bin/env python3
"""
Database Migration Runner for UnFuzz
Executes SQL migration files against Supabase
"""
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql
import sys

# Load environment variables
load_dotenv()

def run_migration(cursor, filepath):
    """Execute a SQL migration file"""
    print(f"\n{'='*60}")
    print(f"Running migration: {os.path.basename(filepath)}")
    print(f"{'='*60}\n")

    with open(filepath, 'r') as f:
        sql_content = f.read()

    try:
        cursor.execute(sql_content)
        print(f"✓ Successfully executed {os.path.basename(filepath)}")
        return True
    except Exception as e:
        print(f"✗ Error executing {os.path.basename(filepath)}: {e}")
        return False

def main():
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')

    if not database_url:
        print("ERROR: DATABASE_URL not found in environment variables")
        print("Please ensure .env file exists with DATABASE_URL set")
        sys.exit(1)

    print(f"Connecting to database...")

    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        conn.autocommit = False  # Use transactions
        cursor = conn.cursor()

        print("✓ Connected successfully\n")

        # List of migration files to run in order
        migrations = [
            'database/schema.sql',
            'database/migration_001_team_player_support.sql'
        ]

        success_count = 0

        for migration_file in migrations:
            if os.path.exists(migration_file):
                if run_migration(cursor, migration_file):
                    success_count += 1
                    conn.commit()
                    print(f"✓ Transaction committed\n")
                else:
                    conn.rollback()
                    print(f"✗ Transaction rolled back\n")
                    print(f"\nMigrations stopped due to error in {migration_file}")
                    break
            else:
                print(f"✗ Migration file not found: {migration_file}\n")

        cursor.close()
        conn.close()

        print(f"\n{'='*60}")
        print(f"Migration Summary")
        print(f"{'='*60}")
        print(f"Total migrations: {len(migrations)}")
        print(f"Successful: {success_count}")
        print(f"Failed: {len(migrations) - success_count}")
        print(f"{'='*60}\n")

        if success_count == len(migrations):
            print("✓ All migrations completed successfully!")

            # Verify tables were created
            conn = psycopg2.connect(database_url)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            cursor.close()
            conn.close()

            print(f"\nCreated tables ({len(tables)}):")
            for table in tables:
                print(f"  - {table[0]}")

            return 0
        else:
            print("✗ Some migrations failed. Please check the errors above.")
            return 1

    except psycopg2.Error as e:
        print(f"\n✗ Database connection error: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
