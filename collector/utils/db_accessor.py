import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.extras import execute_values
import logging


class DBAccessor:
    def __init__(self, db_name):
        self.conn = None
        if not db_name:
            raise ValueError("db_name is required")
        self.db_name = db_name
        self.db_user = os.environ.get("POSTGRE_USER")
        self.db_password = os.environ.get("POSTGRE_PASSWORD")
        self.db_host = os.environ.get("POSTGRE_HOST")
        self.db_port = os.environ.get("POSTGRE_PORT", "5432")
        self.logger = logging.getLogger(__name__)
        self._db_ensured = False  # Track if database existence has been checked

    def _connect_to_postgres_db(self):
        """Connect to the default 'postgres' database (for creating databases)."""
        try:
            conn = psycopg2.connect(
                dbname='postgres',  # Connect to default postgres database
                user=self.db_user,
                password=self.db_password,
                host=self.db_host,
                port=self.db_port
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            self.logger.info("Connected to postgres database")
            return conn
        except Exception as e:
            self.logger.error(f"Failed to connect to postgres database: {e}")
            raise

    def create_database_if_not_exists(self):
        """Create the database if it doesn't exist."""
        conn = None
        try:
            conn = self._connect_to_postgres_db()

            # Check if database exists
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (self.db_name,)
                )
                exists = cur.fetchone()

                if not exists:
                    # Create database
                    cur.execute(f'CREATE DATABASE "{self.db_name}"')
                    self.logger.info(f"Created database: {self.db_name}")
                else:
                    self.logger.info(f"Database already exists: {self.db_name}")
                    

        except Exception as e:
            self.logger.error(f"Failed to create database: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def connect(self):
        """Connect to PostgreSQL database. Creates database if it doesn't exist."""
        if self.conn is None:
            # Ensure database exists on first connection
            if not self._db_ensured:
                self.create_database_if_not_exists()
                self._db_ensured = True

            try:
                self.conn = psycopg2.connect(
                    dbname=self.db_name,
                    user=self.db_user,
                    password=self.db_password,
                    host=self.db_host,
                    port=self.db_port
                )
                self.logger.info(f"Connected to database: {self.db_name}")
            except Exception as e:
                self.logger.error(f"Failed to connect to database: {e}")
                raise
        return self.conn

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.logger.info("Database connection closed")

    def enable_postgis(self):
        """Enable PostGIS extension in the database."""
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
                self.conn.commit()
                self.logger.info("PostGIS extension enabled")
        except Exception as e:
            self.logger.error(f"Failed to enable PostGIS: {e}")
            raise

    def execute(self, query, params=None):
        """Execute a SQL query."""
        try:
            self.connect()
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Query execution failed: {e}")
            raise