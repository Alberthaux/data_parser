import re
import logging
import sqlite3
from typing import List

logging.basicConfig(level=logging.INFO)


class SQLExporter:
    def __init__(self, db_name: str):
        """Initialize the SQLExporter with a database name."""
        self.db_name = db_name

    def create_table(self, table_name: str, columns: List[str]):
        """Create a table with the given name and columns."""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            column_definitions = ", ".join(columns)
            query = f"CREATE TABLE IF NOT EXISTS {table_name} ({column_definitions});"
            print(f"Creating table '{table_name}' with query: {query}")  # Debug print
            try:
                cursor.execute(query)
                print(f"Table '{table_name}' created successfully.")
            except sqlite3.OperationalError as e:
                print(f"Failed to create table '{table_name}': {e}")

    def insert_data(self, table_name: str, data: List[dict]):
        """Insert data into the specified table.

        Args:
            table_name (str): Name of the table.
            data (List[dict]): List of dictionaries, where keys match column names.
        """
        if not data:
            print("No data provided for insertion.")
            return

        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()

            # Extract column names from the first dictionary
            columns = data[0].keys()
            placeholders = ", ".join(["?" for _ in columns])
            column_names = ", ".join(columns)

            query = (
                f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders});"
            )

            # Prepare data as tuples
            values = [tuple(item.values()) for item in data]

            cursor.executemany(query, values)
            conn.commit()
            print(f"Inserted {len(data)} rows into table '{table_name}'.")

    def export_to_sql(self, table_name: str, columns: List[str], data: List[dict]):
        """High-level function to create a table and insert data.

        Args:
            table_name (str): Name of the table.
            columns (List[str]): List of column definitions (e.g., "id INTEGER PRIMARY KEY").
            data (List[dict]): List of dictionaries to insert into the table.
        """
        self.create_table(table_name, columns)
        self.insert_data(table_name, data)
