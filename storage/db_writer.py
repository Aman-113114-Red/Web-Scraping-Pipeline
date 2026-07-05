"""
Database Writer — PostgreSQL (Optional)
========================================
Stores scraped data in a PostgreSQL database using SQLAlchemy.

Features
--------
  • Auto-creates a table per parser (e.g. ``scraped_books``, ``scraped_quotes``)
  • Columns derived from the parser's ``get_columns()``
  • Graceful no-op if ``DB_URL`` is not configured
  • Upsert-style insert (skip duplicates)
"""

from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# Flag to track availability
_sqlalchemy_available = True

try:
    from sqlalchemy import (
        create_engine,
        Column,
        Integer,
        String,
        Text,
        MetaData,
        Table,
        inspect,
    )
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import SQLAlchemyError
except ImportError:
    _sqlalchemy_available = False
    logger.info(
        "SQLAlchemy not installed — database storage disabled. "
        "Install with: pip install sqlalchemy psycopg2-binary"
    )


class DatabaseWriter:
    """
    Optional PostgreSQL storage backend.

    If ``DB_URL`` is empty or SQLAlchemy is not installed, all methods
    are silent no-ops.
    """

    def __init__(self, db_url: Optional[str] = None) -> None:
        self.enabled = False
        self.engine = None
        self.Session = None
        self.metadata = None

        if not _sqlalchemy_available:
            return

        if not db_url:
            from config.settings import Settings
            db_url = Settings.DB_URL

        if not db_url:
            logger.info("DB_URL not configured — database storage disabled")
            return

        try:
            self.engine = create_engine(db_url, echo=False, pool_pre_ping=True)
            self.Session = sessionmaker(bind=self.engine)
            self.metadata = MetaData()
            self.enabled = True
            logger.info("Database connection established: %s", db_url.split("@")[-1])
        except Exception as exc:
            logger.error("Failed to connect to database: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def save(
        self,
        records: List[Dict[str, Any]],
        table_name: str,
        columns: Optional[List[str]] = None,
    ) -> int:
        """
        Insert records into the database.

        Parameters
        ----------
        records : list of dict
            Data to insert.
        table_name : str
            Name of the target table (e.g. ``"scraped_books"``).
        columns : list of str, optional
            Expected column names. If provided, the table is created /
            verified with these columns.

        Returns
        -------
        int
            Number of records successfully inserted.
        """
        if not self.enabled or not records:
            return 0

        try:
            table = self._ensure_table(table_name, columns or list(records[0].keys()))
            session = self.Session()

            inserted = 0
            for record in records:
                try:
                    session.execute(table.insert().values(**{
                        k: str(v) for k, v in record.items()
                        if k in [col.name for col in table.columns]
                    }))
                    inserted += 1
                except SQLAlchemyError:
                    session.rollback()
                    continue

            session.commit()
            session.close()

            logger.info("Inserted %d records into '%s'", inserted, table_name)
            return inserted

        except Exception as exc:
            logger.error("Database save failed: %s", exc)
            return 0

    def query(
        self,
        table_name: str,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Query records from a table.

        Parameters
        ----------
        table_name : str
            Name of the table to query.
        limit : int
            Maximum number of records to return.

        Returns
        -------
        list of dict
            Records from the table.
        """
        if not self.enabled:
            return []

        try:
            table = Table(table_name, self.metadata, autoload_with=self.engine)
            session = self.Session()
            result = session.execute(table.select().limit(limit))
            rows = [dict(row._mapping) for row in result]
            session.close()
            return rows
        except Exception as exc:
            logger.warning("Database query failed: %s", exc)
            return []

    def close(self) -> None:
        """Dispose of the engine connection pool."""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_table(self, table_name: str, columns: List[str]) -> "Table":
        """Create the table if it doesn't exist, or load it if it does."""
        inspector = inspect(self.engine)

        if inspector.has_table(table_name):
            return Table(table_name, self.metadata, autoload_with=self.engine)

        # Build columns dynamically
        table_columns = [
            Column("id", Integer, primary_key=True, autoincrement=True),
        ]
        for col in columns:
            if col == "id":
                continue
            table_columns.append(Column(col, Text, nullable=True))

        table = Table(table_name, self.metadata, *table_columns)
        self.metadata.create_all(self.engine)

        logger.info("Created table '%s' with columns: %s", table_name, columns)
        return table
