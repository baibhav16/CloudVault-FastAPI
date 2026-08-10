from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


# ============================================================
# DATABASE CONNECTIONS
# ============================================================

SQLITE_URL = "sqlite:///./cloudvault.db"

POSTGRES_URL = (
    "postgresql+psycopg://"
    "postgres:Baibhav%4016"
    "@localhost:5432/cloudvault"
)


sqlite_engine = create_engine(
    SQLITE_URL
)

postgres_engine = create_engine(
    POSTGRES_URL
)


# ============================================================
# TABLES IN FOREIGN-KEY ORDER
# ============================================================

TABLES = [
    "users",
    "folders",
    "files",
    "file_versions",
    "shares",
]


# ============================================================
# GET ROWS FROM SQLITE
# ============================================================

def get_sqlite_rows(
    connection,
    table_name: str
):
    result = connection.execute(
        text(f"SELECT * FROM {table_name}")
    )

    rows = result.mappings().all()

    # SQLite stores Boolean values as 0/1.
    # PostgreSQL expects actual True/False values.

    if table_name == "files":

        rows = [
            {
                **dict(row),
                "deleted": bool(row["deleted"])
            }
            for row in rows
        ]

    return rows


# ============================================================
# INSERT ROWS INTO POSTGRES
# ============================================================

def insert_rows(
    connection,
    table_name: str,
    rows
):

    if not rows:
        print(
            f"{table_name}: 0 rows - skipped"
        )
        return

    columns = list(
        rows[0].keys()
    )

    column_list = ", ".join(
        columns
    )

    parameter_list = ", ".join(
        f":{column}"
        for column in columns
    )

    query = text(
        f"""
        INSERT INTO {table_name}
        ({column_list})
        VALUES
        ({parameter_list})
        """
    )

    connection.execute(
        query,
        [
            dict(row)
            for row in rows
        ]
    )

    print(
        f"{table_name}: "
        f"{len(rows)} rows migrated"
    )


# ============================================================
# RESET POSTGRES SEQUENCES
# ============================================================

def reset_sequences(
    connection
):

    for table in TABLES:

        sequence_name = (
            f"{table}_id_seq"
        )

        try:

            connection.execute(
                text(
                    f"""
                    SELECT setval(
                        '{sequence_name}',
                        COALESCE(
                            (SELECT MAX(id)
                             FROM {table}),
                            1
                        ),
                        true
                    )
                    """
                )
            )

        except Exception:

            # Some tables/databases may not
            # have the conventional sequence.
            pass


# ============================================================
# VERIFY COUNTS
# ============================================================

def verify_counts(
    sqlite_connection,
    postgres_connection
):

    print("\n==============================")
    print("VERIFYING ROW COUNTS")
    print("==============================")

    for table in TABLES:

        sqlite_count = sqlite_connection.execute(
            text(
                f"SELECT COUNT(*) FROM {table}"
            )
        ).scalar()

        postgres_count = postgres_connection.execute(
            text(
                f"SELECT COUNT(*) FROM {table}"
            )
        ).scalar()

        print(
            f"{table:15} "
            f"SQLite={sqlite_count:<5} "
            f"Postgres={postgres_count:<5}"
        )

        if sqlite_count != postgres_count:

            raise RuntimeError(
                f"COUNT MISMATCH for {table}: "
                f"SQLite={sqlite_count}, "
                f"Postgres={postgres_count}"
            )


# ============================================================
# MAIN MIGRATION
# ============================================================

def main():

    print(
        "Starting SQLite → PostgreSQL migration..."
    )

    with (
        sqlite_engine.connect() as sqlite_connection,
        postgres_engine.begin() as postgres_connection
    ):

        # ----------------------------------------------------
        # SAFETY CHECK
        # ----------------------------------------------------

        existing_count = postgres_connection.execute(
            text(
                "SELECT COUNT(*) FROM users"
            )
        ).scalar()

        if existing_count > 0:

            raise RuntimeError(
                "PostgreSQL already contains data. "
                "Migration stopped for safety."
            )

        # ----------------------------------------------------
        # READ + INSERT
        # ----------------------------------------------------

        for table in TABLES:

            rows = get_sqlite_rows(
                sqlite_connection,
                table
            )

            insert_rows(
                postgres_connection,
                table,
                rows
            )

        # ----------------------------------------------------
        # RESET ID SEQUENCES
        # ----------------------------------------------------

        reset_sequences(
            postgres_connection
        )

    # --------------------------------------------------------
    # VERIFY
    # --------------------------------------------------------

    with (
        sqlite_engine.connect() as sqlite_connection,
        postgres_engine.connect() as postgres_connection
    ):

        verify_counts(
            sqlite_connection,
            postgres_connection
        )

    print(
        "\n================================"
    )

    print(
        "MIGRATION SUCCESSFUL"
    )

    print(
        "================================"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()