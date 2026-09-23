"""
SQL Server -> PostgreSQL migration for the Attendance app.

IMPORTANT:
- This is NOT a full 1:1 migration of the entire IERPSystem database.
- It migrates ONLY the 14 application tables listed in TABLES below.
- Column names, source data values, NULLs, and binary employee photos are copied.
- SQL Server-specific database objects (all other tables, views, procedures,
  triggers, jobs, permissions, etc.) are NOT migrated.
- The SQL Server source is READ ONLY. Nothing is deleted or modified there.

The target PostgreSQL database should already exist.

Required environment variables for SQL Server:
    DATABASE_USER
    DATABASE_PASSWORD
    DATABASE_HOST
    DATABASE_NAME=IERPSystem
    DATABASE_INSTANCE   (optional for named SQL Server instances)
    DATABASE_PORT       (default 1433)
    ODBC_DRIVER         (default: ODBC Driver 18 for SQL Server)

Required environment variables for local PostgreSQL:
    PG_USER
    PG_PASSWORD

Optional PostgreSQL settings:
    PG_HOST=localhost
    PG_PORT=5432
    PG_DATABASE=attendance_app

Optional:
    MIGRATION_BATCH_SIZE=500
    MIGRATION_REPLACE_EXISTING=false

If MIGRATION_REPLACE_EXISTING=true, ONLY the 14 selected PostgreSQL tables
are dropped/recreated. The SQL Server source is never touched.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import (
    Boolean,
    CHAR,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    BigInteger,
    LargeBinary,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    Time,
    create_engine,
    inspect,
    text,
)
from sqlalchemy.engine import URL


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


TABLES = [
    "SalEmployee",
    "SalStructureTest",
    "AttendancePunch",
    "SalEmpContact",
    "SalEmpDocuments",
    "SalEmpRelation",
    "ContDepartment",
    "ContDesignation",
    "ContQualification",
    "ContRelationship",
    "ContMOC",
    "ContCommon",
    "AcctAccount",
    "DocMasRecords",
]

BATCH_SIZE = int(os.getenv("MIGRATION_BATCH_SIZE", "500"))
REPLACE_EXISTING = (
    os.getenv("MIGRATION_REPLACE_EXISTING", "false").lower() == "true"
)


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def build_sqlserver_engine():
    user = require_env("DATABASE_USER")
    password = require_env("DATABASE_PASSWORD")
    host = os.getenv("DATABASE_HOST", "localhost")
    instance = os.getenv("DATABASE_INSTANCE", "")
    database = os.getenv("DATABASE_NAME", "IERPSystem")
    port = os.getenv("DATABASE_PORT", "1433")
    driver = os.getenv("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")

    if instance:
        host = f"{host}\\{instance}"
        port_value = None
    else:
        port_value = int(port)

    url = URL.create(
        drivername="mssql+pyodbc",
        username=user,
        password=password,
        host=host,
        port=port_value,
        database=database,
        query={
            "driver": driver,
            "TrustServerCertificate": "yes",
        },
    )

    return create_engine(url, pool_pre_ping=True)


def build_postgres_engine():
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=require_env("PG_USER"),
        password=require_env("PG_PASSWORD"),
        host=os.getenv("PG_HOST", "localhost"),
        port=int(os.getenv("PG_PORT", "5432")),
        database=os.getenv("PG_DATABASE", "attendance_app"),
    )

    return create_engine(url, pool_pre_ping=True)


def map_sqlserver_type(source_type):
    """
    Map the SQL Server types used by the selected tables to PostgreSQL types.
    The migration is data-oriented; SQL Server-specific behavior is not copied.
    """
    name = source_type.__class__.__name__.lower()
    length = getattr(source_type, "length", None)
    precision = getattr(source_type, "precision", None)
    scale = getattr(source_type, "scale", None)

    if "money" in name:
        return Numeric(19, 4)

    if "bigint" in name:
        return BigInteger()

    if "smallint" in name:
        return SmallInteger()

    if name == "integer":
        return Integer()

    if "tinyint" in name:
        return SmallInteger()

    if "bit" in name:
        return Boolean()

    if "decimal" in name or "numeric" in name:
        if precision is not None:
            return Numeric(precision, scale or 0)
        return Numeric()

    if "float" in name or "real" in name:
        return Float()

    if "datetime" in name or "smalldatetime" in name:
        return DateTime()

    if name == "date":
        return Date()

    if name == "time":
        return Time()

    if name in {"char", "nchar"}:
        return CHAR(length)

    if "nvarchar" in name or "varchar" in name:
        return String(length)

    if "ntext" in name or name == "text":
        return Text()

    # SQL Server image/varbinary fields -> PostgreSQL bytea.
    if (
        "image" in name
        or "binary" in name
        or "varbinary" in name
        or "rowversion" in name
        or name == "timestamp"
    ):
        return LargeBinary()

    if "uniqueidentifier" in name:
        return String(36)

    if "xml" in name:
        return Text()

    # Safe fallback for anything unexpected in the selected tables.
    return Text()


def reflect_source_table(sql_engine, table_name: str):
    source_metadata = MetaData()

    source_table = Table(
        table_name,
        source_metadata,
        schema="dbo",
        autoload_with=sql_engine,
        quote=True,
    )

    inspector = inspect(sql_engine)
    pk_columns = inspector.get_pk_constraint(
        table_name,
        schema="dbo",
    ).get("constrained_columns", [])

    if not source_table.columns:
        raise RuntimeError(f"No columns found for dbo.{table_name}")

    pg_metadata = MetaData()
    pg_columns = []

    for source_column in source_table.columns:
        pg_columns.append(
            Column(
                source_column.name,
                map_sqlserver_type(source_column.type),
                nullable=source_column.nullable,
                primary_key=source_column.name in pk_columns,
                quote=True,
            )
        )

    target_table = Table(
        table_name,
        pg_metadata,
        *pg_columns,
        quote=True,
    )

    return source_table, target_table


def target_exists(pg_engine, table_name: str) -> bool:
    return inspect(pg_engine).has_table(
        table_name,
        schema="public",
    )


def copy_table(sql_conn, pg_conn, source_table, target_table, table_name):
    source_columns = [column.name for column in source_table.columns]

    result = sql_conn.execute(source_table.select())
    insert_stmt = target_table.insert()

    total = 0

    while True:
        rows = result.fetchmany(BATCH_SIZE)

        if not rows:
            break

        payload = [
            dict(zip(source_columns, row))
            for row in rows
        ]

        pg_conn.execute(insert_stmt, payload)
        total += len(payload)

        print(f"    {table_name}: {total} rows")

    return total


def setup_attendance_sequence(pg_conn):
    """
    Configure future AttendancePunch inserts.

    We intentionally DO NOT drop the sequence. The previous implementation
    failed because PostgreSQL refuses to drop a sequence while a column
    default depends on it.

    Instead:
      1. remove the current column default,
      2. create the sequence if it does not already exist,
      3. set it to MAX(pkEAId),
      4. attach it as the default.

    This is safe to repeat.
    """
    pg_conn.execute(
        text(
            'ALTER TABLE "AttendancePunch" '
            'ALTER COLUMN "pkEAId" DROP DEFAULT'
        )
    )

    pg_conn.execute(
        text(
            'CREATE SEQUENCE IF NOT EXISTS "AttendancePunch_pkEAId_seq" '
            'AS bigint'
        )
    )

    max_id = pg_conn.execute(
        text(
            'SELECT MAX("pkEAId") '
            'FROM "AttendancePunch"'
        )
    ).scalar()

    max_id = int(max_id or 0)

    if max_id == 0:
        pg_conn.execute(
            text(
                'SELECT setval('
                '\'"AttendancePunch_pkEAId_seq"\', '
                '1, false)'
            )
        )
        next_id = 1
    else:
        pg_conn.execute(
            text(
                'SELECT setval('
                '\'"AttendancePunch_pkEAId_seq"\', '
                ':max_id, true)'
            ),
            {"max_id": max_id},
        )
        next_id = max_id + 1

    pg_conn.execute(
        text(
            'ALTER TABLE "AttendancePunch" '
            'ALTER COLUMN "pkEAId" '
            'SET DEFAULT nextval('
            '\'"AttendancePunch_pkEAId_seq"\''
            ')'
        )
    )

    print(
        f'AttendancePunch.pkEAId sequence ready; '
        f'next generated ID = {next_id}'
    )


def verify_counts(sql_engine, pg_engine):
    print("\n=== Row-count verification ===")

    with sql_engine.connect() as sql_conn, pg_engine.connect() as pg_conn:
        mismatches = []

        for table_name in TABLES:
            source_count = sql_conn.execute(
                text(
                    f'SELECT COUNT(*) '
                    f'FROM dbo."{table_name}"'
                )
            ).scalar()

            target_count = pg_conn.execute(
                text(
                    f'SELECT COUNT(*) '
                    f'FROM public."{table_name}"'
                )
            ).scalar()

            print(
                f"{table_name}: "
                f"SQL Server={source_count}, "
                f"PostgreSQL={target_count}"
            )

            if source_count != target_count:
                mismatches.append(
                    (table_name, source_count, target_count)
                )

        if mismatches:
            raise RuntimeError(
                "Row-count mismatch detected: "
                + repr(mismatches)
            )


def main():
    source_db = os.getenv("DATABASE_NAME", "IERPSystem")
    target_db = os.getenv("PG_DATABASE", "attendance_app")

    print("=== SQL Server -> PostgreSQL migration ===")
    print(f"Source DB: {source_db}")
    print(f"Target DB: {target_db}")
    print(f"Tables: {', '.join(TABLES)}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Replace existing PostgreSQL tables: {REPLACE_EXISTING}")
    print()

    sql_engine = build_sqlserver_engine()
    pg_engine = build_postgres_engine()

    # Verify both connections before touching the PostgreSQL target.
    with sql_engine.connect() as sql_conn:
        sql_conn.execute(text("SELECT 1"))
        print(f"SQL Server connection OK: {source_db}")

    with pg_engine.connect() as pg_conn:
        pg_conn.execute(text("SELECT 1"))
        print(f"PostgreSQL connection OK: {target_db}")

    source_tables = {}
    target_tables = {}

    # Build reflected table definitions first.
    for table_name in TABLES:
        source_table, target_table = reflect_source_table(
            sql_engine,
            table_name,
        )
        source_tables[table_name] = source_table
        target_tables[table_name] = target_table

    # Recreate selected target tables only when explicitly requested.
    if REPLACE_EXISTING:
        with pg_engine.begin() as pg_conn:
            for table_name in reversed(TABLES):
                if target_exists(pg_engine, table_name):
                    print(
                        f'Dropping PostgreSQL table: "{table_name}"'
                    )
                    target_tables[table_name].drop(
                        pg_conn,
                        checkfirst=True,
                    )

        print("Existing selected PostgreSQL tables dropped.")

    # Create tables.
    target_metadata = MetaData()

    # Copy the columns from the reflected target tables into one metadata
    # collection so create_all can create them together.
    final_targets = []

    for table_name in TABLES:
        target = target_tables[table_name]

        # Re-bind to a single metadata collection.
        rebound_columns = [
            Column(
                column.name,
                column.type,
                nullable=column.nullable,
                primary_key=column.primary_key,
                quote=True,
            )
            for column in target.columns
        ]

        rebound_table = Table(
            table_name,
            target_metadata,
            *rebound_columns,
            quote=True,
        )

        final_targets.append(rebound_table)
        target_tables[table_name] = rebound_table

    target_metadata.create_all(pg_engine)
    print("PostgreSQL tables created.")

    # Copy rows in one transaction.
    with sql_engine.connect() as sql_conn, pg_engine.begin() as pg_conn:
        for table_name in TABLES:
            print(f"\nCopying {table_name}...")

            count = copy_table(
                sql_conn,
                pg_conn,
                source_tables[table_name],
                target_tables[table_name],
                table_name,
            )

            print(f"  -> {table_name}: {count} rows copied")

        setup_attendance_sequence(pg_conn)

    # Verify every selected table has the same row count.
    verify_counts(sql_engine, pg_engine)

    print("\nMigration complete.")
    print(
        "The SQL Server source database was READ ONLY; "
        "no source rows were modified."
    )
    print(
        "This migration is table/data selective, not a complete "
        "1:1 copy of IERPSystem."
    )


if __name__ == "__main__":
    main()
