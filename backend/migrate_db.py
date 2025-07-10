import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

def get_db_config():
    url = urlparse(os.getenv('DATABASE_URL'))
    return {
        'dbname': url.path[1:],
        'user': url.username,
        'password': url.password,
        'host': url.hostname,
        'port': url.port
    }

def run_migration():
    try:
        # Get database configuration from URL
        db_config = get_db_config()
        
        # Database connection
        conn = psycopg2.connect(**db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("Starting database migration...")
        
        # Check if is_active column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='is_active';
        """)
        
        if not cursor.fetchone():
            # Add is_active column
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN is_active BOOLEAN DEFAULT TRUE;
            """)
            print("✓ Added is_active column to users table")
            
            # Update existing users to be active
            cursor.execute("""
                UPDATE users SET is_active = TRUE WHERE is_active IS NULL;
            """)
            print("✓ Updated existing users to active status")
        else:
            print("✓ is_active column already exists")
        
        # Check if phone column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='phone';
        """)
        
        if not cursor.fetchone():
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN phone VARCHAR(20);
            """)
            print("✓ Added phone column to users table")
        else:
            print("✓ phone column already exists")
        
        # Add indexes for better performance
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
                CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
                CREATE INDEX IF NOT EXISTS idx_users_created_by ON users(created_by);
            """)
            print("✓ Added database indexes")
        except Exception as e:
            print(f"Note: Some indexes may already exist: {e}")
        
        # Add constraints
        try:
            cursor.execute("""
                ALTER TABLE users 
                ADD CONSTRAINT chk_users_role 
                CHECK (role IN ('superadmin', 'admin', 'employee'));
            """)
            print("✓ Added role constraint")
        except Exception as e:
            print(f"Note: Role constraint may already exist: {e}")
        
        cursor.close()
        conn.close()
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    run_migration()