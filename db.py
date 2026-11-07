import mysql.connector
from mysql.connector import pooling
import certifi
from config import Config

dbconfig = {
    "host": Config.DB_HOST,
    "port": int(Config.DB_PORT) if getattr(Config, 'DB_PORT', None) else 4000,
    "user": Config.DB_USER,
    "password": Config.DB_PASSWORD,
    "database": Config.DB_NAME,
    "autocommit": True,
    "ssl_ca": certifi.where(),
    "ssl_verify_identity": True
}

try:
    db_pool = mysql.connector.pooling.MySQLConnectionPool(
        pool_name="fintrack_pool",
        pool_size=5,
        **dbconfig
    )
except Exception as e:
    print(f"Error initializing DB pool: {e}")
    db_pool = None

def get_db_connection():
    """Returns a connection from the pool, falling back to direct connect if needed."""
    if db_pool:
        return db_pool.get_connection()
    return mysql.connector.connect(**dbconfig)