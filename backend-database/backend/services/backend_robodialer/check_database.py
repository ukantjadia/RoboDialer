#!/usr/bin/env python3
"""
Check database table structure
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from sqlalchemy import text

def check_agents_table():
    """Check if agents table exists and its structure"""
    
    try:
        from app import create_app
        from models.lead_model import db
        
        app = create_app()
        with app.app_context():
            # Check if table exists
            result = db.session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'agents'
                );
            """))
            table_exists = result.scalar()
            
            if table_exists:
                print("✅ Agents table exists")
                
                # Get column information
                result = db.session.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'agents'
                    ORDER BY ordinal_position;
                """))
                columns = result.fetchall()
                
                print("\nTable structure:")
                for col in columns:
                    print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
                    
                # Check if score_given column exists
                score_given_exists = any(col[0] == 'score_given' for col in columns)
                if not score_given_exists:
                    print("\n❌ Missing 'score_given' column")
                    return False
                else:
                    print("\n✅ All required columns exist")
                    return True
                    
            else:
                print("❌ Agents table does not exist")
                return False
                
    except Exception as e:
        print(f"Error checking table: {e}")
        return False

if __name__ == "__main__":
    check_agents_table()