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
CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    age INTEGER,
    email TEXT,
    json_data TEXT
);
'''
cursor.execute(create_table_query)
conn.commit()

create_table_query = '''
CREATE TABLE IF NOT EXISTS emails (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER,
    subject TEXT,
    email TEXT
);
'''
cursor.execute(create_table_query)
conn.commit()

email_id = 1000

# Generate and insert fake names into the 'persons' table
for person_id in range(1000, 1010):  # Adjust the number of entries you want to add
    first_name = fake.first_name()
    last_name = fake.last_name()
    age = fake.random_int(min=18, max=99)
    email = fake.word() + '@example.com'
    json_obj = {
        "person": {
            "firstname": first_name,
            "lastname": last_name,
            "age": age,
            "email": email,
        }
    }
    json_string_pretty = json.dumps(json_obj, indent=4)
    
    insert_query = "INSERT INTO persons (id, first_name, last_name, age, email, json_data) VALUES (?, ?, ?, ?, ?, ?)"
    cursor.execute(insert_query, (person_id, first_name, last_name, age, email, json_string_pretty))

    # add an email for every person
    insert_query = "INSERT INTO emails (person_id, subject, email) VALUES (?, ?, ?)"
    cursor.execute(insert_query, (person_id, f'Hello {first_name} {last_name}', email))

# insert a null values as a valid test case
insert_query = "INSERT INTO persons (first_name, last_name, age) VALUES (?, ?, ?)"
cursor.execute(insert_query, (None, None, 21))
insert_query = "INSERT INTO persons (first_name, last_name, age) VALUES (?, ?, ?)"
cursor.execute(insert_query, ('Charles', 'No Age', None))
conn.commit()

# Close the database connection
conn.close()

print("Database table 'persons' created and filled with fake names")