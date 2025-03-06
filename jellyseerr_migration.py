#!/usr/bin/env python3
import os
import sqlite3
import shutil
import sys
from datetime import datetime

# Configuration - update these paths as needed
JELLYSEERR_DB_PATH = "/path/to/jellyseerr/config/db/db.sqlite3"
OVERSEERR_DB_PATH = "/path/to/overseerr/config/db/db.sqlite3"
NEW_JELLYSEERR_DB_PATH = "./newjelly_db.sqlite3"  # Path for the new database
BACKUP_DIR = "./backups"

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

def backup_database(db_path, backup_name):
    """Create a backup of the database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"{backup_name}_{timestamp}.db")
    print(f"Creating backup of database at {backup_path}")
    shutil.copy2(db_path, backup_path)
    return backup_path

def get_table_columns(cursor, table_name):
    """Get column information for a table."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {info[1]: {"index": info[0], "type": info[2], "notnull": info[3], "default": info[4]} 
            for info in cursor.fetchall()}

def clone_database_structure(source_db_path, target_db_path):
    """Clone the structure of a SQLite database without data."""
    print(f"Creating new database with structure from: {source_db_path}")
    
    # Connect to source database
    conn_source = sqlite3.connect(source_db_path)
    cursor_source = conn_source.cursor()
    
    # Get all tables
    cursor_source.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [table[0] for table in cursor_source.fetchall()]
    
    # Create new database
    if os.path.exists(target_db_path):
        os.remove(target_db_path)
    
    conn_target = sqlite3.connect(target_db_path)
    cursor_target = conn_target.cursor()
    
    # Turn off foreign keys temporarily to avoid constraints during creation
    cursor_target.execute("PRAGMA foreign_keys = OFF")
    
    # Copy each table structure
    for table in tables:
        # Skip sqlite_sequence table (handled automatically)
        if table == 'sqlite_sequence':
            continue
            
        print(f"  Cloning table structure: {table}")
        
        # Get table creation SQL
        cursor_source.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
        create_table_sql = cursor_source.fetchone()[0]
        
        # Create table in new database
        cursor_target.execute(create_table_sql)
        
        # Copy indices for this table
        cursor_source.execute(f"SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name='{table}'")
        indices = cursor_source.fetchall()
        for idx in indices:
            if idx[0]:  # Skip NULL entries
                try:
                    cursor_target.execute(idx[0])
                except sqlite3.Error as e:
                    print(f"    Warning: Could not create index: {e}")
    
    # Get all triggers and views
    for object_type in ['trigger', 'view']:
        cursor_source.execute(f"SELECT sql FROM sqlite_master WHERE type='{object_type}'")
        objects = cursor_source.fetchall()
        for obj in objects:
            if obj[0]:  # Skip NULL entries
                try:
                    cursor_target.execute(obj[0])
                except sqlite3.Error as e:
                    print(f"    Warning: Could not create {object_type}: {e}")
    
    # Turn foreign keys back on
    cursor_target.execute("PRAGMA foreign_keys = ON")
    
    # Commit and close
    conn_target.commit()
    conn_source.close()
    conn_target.close()
    
    print(f"New database structure created at: {target_db_path}")

def migrate_tables(over_db_path, jelly_db_path, new_jelly_db_path):
    """Migrate tables from Overseerr DB to a new Jellyseerr DB with column compatibility checks."""
    # Tables to migrate in this specific order as per the tutorial
    tables = [
        "media", "user", "issue", "issue_comment", "media_request", 
        "season", "season_request", "user_settings", 
        "user_push_subscription", "session", "watchlist", "discover_slider"
    ]
    
    print(f"Opening Overseerr database: {over_db_path}")
    print(f"Opening reference Jellyseerr database: {jelly_db_path}")
    print(f"Opening new Jellyseerr database: {new_jelly_db_path}")
    
    # Connect to all databases
    conn_over = sqlite3.connect(over_db_path)
    conn_jelly = sqlite3.connect(jelly_db_path)
    conn_new_jelly = sqlite3.connect(new_jelly_db_path)
    
    # Create cursors
    cursor_over = conn_over.cursor()
    cursor_jelly = conn_jelly.cursor()
    cursor_new_jelly = conn_new_jelly.cursor()
    
    # Summary of column discrepancies
    column_differences = {}
    
    for table in tables:
        print(f"\nMigrating table: {table}")
        
        # Check if table exists in necessary databases
        cursor_over.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor_over.fetchone():
            print(f"Table {table} does not exist in Overseerr database. Skipping...")
            continue
        
        cursor_jelly.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor_jelly.fetchone():
            print(f"Table {table} does not exist in reference Jellyseerr database. Skipping...")
            continue
        
        cursor_new_jelly.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
        if not cursor_new_jelly.fetchone():
            print(f"Table {table} does not exist in new Jellyseerr database. Skipping...")
            continue
        
        # Get column information for both tables
        over_columns = get_table_columns(cursor_over, table)
        jelly_columns = get_table_columns(cursor_jelly, table)
        
        # Compare columns and record differences
        missing_in_jelly = set(over_columns.keys()) - set(jelly_columns.keys())
        missing_in_over = set(jelly_columns.keys()) - set(over_columns.keys())
        
        if missing_in_jelly or missing_in_over:
            column_differences[table] = {
                "missing_in_jellyseerr": list(missing_in_jelly),
                "missing_in_overseerr": list(missing_in_over)
            }
            
            if missing_in_jelly:
                print(f"WARNING: Columns in Overseerr but missing in Jellyseerr: {', '.join(missing_in_jelly)}")
            if missing_in_over:
                print(f"WARNING: Columns in Jellyseerr but missing in Overseerr: {', '.join(missing_in_over)}")
        
        # Get all data from Overseerr table
        cursor_over.execute(f"SELECT * FROM {table}")
        over_rows = cursor_over.fetchall()
        
        if not over_rows:
            print(f"No data in {table}. Skipping...")
            continue
        
        # Get ordered list of columns that exist in both databases
        common_columns = [col for col in over_columns.keys() if col in jelly_columns]
        
        # Get index positions of common columns in Overseerr table
        over_indices = [list(over_columns.keys()).index(col) for col in common_columns]
        
        # Prepare data with only common columns
        processed_rows = []
        for row in over_rows:
            # Extract only the values from common columns by their indices
            processed_row = [row[idx] for idx in over_indices]
            processed_rows.append(processed_row)
        
        # Escape column names to handle reserved keywords
        escaped_columns = [f'"{column}"' for column in common_columns]
        
        # Prepare SQL for insertion
        placeholders = ", ".join(["?" for _ in common_columns])
        columns_str = ", ".join(escaped_columns)
        insert_sql = f'INSERT INTO {table} ({columns_str}) VALUES ({placeholders})'
        
        # Insert data
        try:
            cursor_new_jelly.executemany(insert_sql, processed_rows)
            print(f"Migrated {len(processed_rows)} rows from {table}")
        except sqlite3.Error as e:
            print(f"Error migrating {table}: {str(e)}")
            print(f"Problematic SQL: {insert_sql}")
            response = input("Continue with migration? (y/n): ").lower()
            if response != 'y':
                raise Exception(f"Migration aborted at table '{table}'")
    
    # Commit changes and close connections
    conn_new_jelly.commit()
    print("\nChanges committed to new Jellyseerr database.")
    
    # Print summary of column differences
    if column_differences:
        print("\n=== Column Compatibility Summary ===")
        for table, differences in column_differences.items():
            print(f"\nTable: {table}")
            if differences["missing_in_jellyseerr"]:
                print(f"  Columns in Overseerr but missing in Jellyseerr (data not migrated):")
                for col in differences["missing_in_jellyseerr"]:
                    print(f"    - {col}")
            if differences["missing_in_overseerr"]:
                print(f"  Columns in Jellyseerr but missing in Overseerr (will have default/NULL values):")
                for col in differences["missing_in_overseerr"]:
                    print(f"    - {col}")
    
    conn_over.close()
    conn_jelly.close()
    conn_new_jelly.close()

def main():
    try:
        print("Starting Overseerr to Jellyseerr database migration")
        
        # Step 1: Backup the original databases
        backup_jellyseerr = backup_database(JELLYSEERR_DB_PATH, "jellyseerr_original")
        backup_overseerr = backup_database(OVERSEERR_DB_PATH, "overseerr_original")
        
        # Step 2: Create a new database with the Jellyseerr structure
        clone_database_structure(JELLYSEERR_DB_PATH, NEW_JELLYSEERR_DB_PATH)
        
        # Step 3: Perform the migration to the new database
        print("\nPerforming database migration...")
        migrate_tables(OVERSEERR_DB_PATH, JELLYSEERR_DB_PATH, NEW_JELLYSEERR_DB_PATH)
        
        print("\nMigration completed successfully!")
        print(f"New Jellyseerr database created at: {NEW_JELLYSEERR_DB_PATH}")
        print(f"Original Jellyseerr database backed up to: {backup_jellyseerr}")
        print(f"Original Overseerr database backed up to: {backup_overseerr}")
        print("\nTo use the new database, replace the existing Jellyseerr database with this new one.")
        
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        print("Migration failed. Your original databases are preserved in the backup directory.")
        sys.exit(1)

if __name__ == "__main__":
    main()
