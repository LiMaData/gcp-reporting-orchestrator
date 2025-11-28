import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv()

def run_sql_file(filename):
    conn = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA'),
        role=os.getenv('SNOWFLAKE_ROLE')
    )
    
    try:
        cursor = conn.cursor()
        with open(filename, 'r') as f:
            sql_commands = f.read().split(';')
            
        for sql in sql_commands:
            if sql.strip():
                print(f"Executing: {sql[:50]}...")
                cursor.execute(sql)
        print("SQL execution complete.")
        
    finally:
        conn.close()

if __name__ == "__main__":
    run_sql_file('setup/create_insights_table.sql')
