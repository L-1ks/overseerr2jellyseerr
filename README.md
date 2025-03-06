# overseerr2jellyseerr
-----------


A utility script to facilitate the migration of data from [Overseerr](https://github.com/sct/overseerr) to [Jellyseerr](https://github.com/Fallenbagel/jellyseerr) databases. This tool was created to help users transition from Overseerr (which hasn't had new releases in over a year) to Jellyseerr, which has emerged as an excellent fork and successor with active development.

Description
-----------

This Python script automates the process of migrating data from an Overseerr database to a Jellyseerr database. Rather than modifying your existing databases, it creates a new Jellyseerr database containing your migrated data, keeping your original databases intact. The script:

*   Creates backups of your original databases
    
*   Clones the structure of your Jellyseerr database to a new file
    
*   Intelligently transfers data from your Overseerr database to the new Jellyseerr database
    
*   Handles column differences between the databases
    
*   Provides detailed feedback about the migration process
    

Prerequisites
-------------

*   Python 3.6 or higher
    
*   Access to both Overseerr and Jellyseerr database files
    

Usage
-----

1.  Edit the configuration variables at the top of the script:
    

```python
# Configuration - update these paths as needed
JELLYSEERR_DB_PATH = "/path/to/jellyseerr/config/db/db.sqlite3"
OVERSEERR_DB_PATH = "/path/to/overseerr/config/db/db.sqlite3"
NEW_JELLYSEERR_DB_PATH = "./newjelly_db.sqlite3"
# Path for the new database
BACKUP_DIR = "./backups"
```

1.  Run the script:
    

```BASH
python3 jellyseerr_migration.py
```

1.  After successful migration, replace your existing Jellyseerr database with the newly created one.
    

### Docker Setup Example

If your Overseerr and Jellyseerr are running in Docker containers, you can access the database files by:

```BASH
# For Overseerr
docker cp overseerr:/app/config/db/db.sqlite3 ./over_db.sqlite3
# For Jellyseerr
docker cp jellyseerr:/app/config/db/db.sqlite3 ./jelly_db.sqlite3 
```
Then run the migration tool:

```BASH
python jellyseerr_migration.py 
```
After migration, copy the new database back to the container:

```BASH
# First stop the container
docker stop jellyseerr
# Copy the new database to the container
docker cp ./newjelly_db.sqlite3 jellyseerr:/app/config/db/db.sqlite3
# Start the container again
docker start jellyseerr
```


Tables Migrated
---------------

The tool migrates the following tables in this specific order:

1.  media
    
2.  user
    
3.  issue
    
4.  issue\_comment
    
5.  media\_request
    
6.  season
    
7.  season\_request
    
8.  user\_settings
    
9.  user\_push\_subscription
    
10.  session
    
11.  watchlist
    
12.  discover\_slider
    


Features
--------

*   **Non-destructive operation**: Creates a new database rather than modifying your existing one
    
*   **Database backups**: Automatically backs up your original databases before migration
    
*   **Column compatibility checks**: Detects and reports differences in table structures
    
*   **Error handling**: Provides detailed error messages and continues migration when possible
    
*   **SQL keyword handling**: Properly escapes column names to avoid SQL syntax errors
    
*   **Migration summary**: Produces a report of column differences and migration status
    


Troubleshooting
---------------

### Error: "near 'order': syntax error"

This is handled by the script through proper column name escaping.

### Table structure differences

The script will display warnings about column differences between databases and continue with the migration where possible.

### Permission errors when accessing database files

Make sure you have permission to read/write to the database files and backup directory.



License
-------

This project is licensed under the MIT License - see the LICENSE file for details.

Acknowledgments
---------------

*   The Overseerr team for creating the original project
    
*   The Jellyseerr team for continuing development and improvements
