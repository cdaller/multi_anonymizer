#!/usr/bin/env python3

import sqlite3
from faker import Faker
import sys

# Define the SQLite database connection
if len(sys.argv) > 1:
    db_file = sys.argv[1]
else:
    db_file = "my_database.db"

# Create a Faker instance
fake = Faker()

# Create a connection to the database
conn = sqlite3.connect(db_file)
cursor = conn.cursor()

# Create the 'people' table
create_table_query = '''
CREATE TABLE IF NOT EXISTS people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    age INTEGER
);
'''
cursor.execute(create_table_query)
conn.commit()

# Generate and insert fake names into the 'people' table
for _ in range(10):  # Adjust the number of entries you want to add
    name = fake.name()
    age = fake.random_int(min=18, max=99)
    
    insert_query = "INSERT INTO people (name, age) VALUES (?, ?)"
    cursor.execute(insert_query, (name, age))
    conn.commit()

# Close the database connection
conn.close()

print("Database table 'people' created and filled with fake names")