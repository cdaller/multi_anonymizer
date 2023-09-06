#!/usr/bin/env python3

import sqlite3
from faker import Faker
import sys
import json

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
    first_name TEXT,
    last_name TEXT,
    age INTEGER,
    email TEXT,
    json TEXT,
);
'''
cursor.execute(create_table_query)
conn.commit()

# Generate and insert fake names into the 'people' table
for _ in range(10):  # Adjust the number of entries you want to add
    first_name = fake.first_name()
    last_name = fake.last_name()
    age = fake.random_int(min=18, max=99)
    email = fake.word() + '@example.com'
    json_obj = {
        "person": {
            "lastname": last_name,
            "firstname": first_name,
            "age": age,
            "email": email,
        }
    }
    json_string_pretty = json.dumps(json_obj, indent=4)
    
    insert_query = "INSERT INTO people (first_name, last_name, age, email, json) VALUES (?, ?, ?, ?, ?)"
    cursor.execute(insert_query, (first_name, last_name, age, email, json_string_pretty))

# insert a null values as a valid test case
insert_query = "INSERT INTO people (first_name, last_name, age) VALUES (?, ?, ?)"
cursor.execute(insert_query, (None, None, 21))
insert_query = "INSERT INTO people (first_name, last_name, age) VALUES (?, ?, ?)"
cursor.execute(insert_query, ('Charles', 'No Age', None))
conn.commit()

# Close the database connection
conn.close()

print("Database table 'people' created and filled with fake names")