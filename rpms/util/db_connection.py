import os

import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": os.getenv("RPMS_DB_HOST", "localhost"),
    "port": int(os.getenv("RPMS_DB_PORT", "3306")),
    "user": os.getenv("RPMS_DB_USER", "root"),
    "password": os.getenv("RPMS_DB_PASSWORD", ""),
    "database": os.getenv("RPMS_DB_NAME", "recruitment_portal"),
}
ACTOR_USER_ID = int(os.getenv("RPMS_ACTOR_USER_ID", "1"))

def get_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)
    except Error as exc:
        raise RuntimeError(f"Database connection failed: {exc}") from exc
