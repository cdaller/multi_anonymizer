#!/usr/bin/env python3

from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, select
import copy

DATABASE_URL = "sqlite:///example.db"
DATABASE_URL = "sqlite:///testfiles/my_database.db"

engine = create_engine(DATABASE_URL)
metadata = MetaData()

# Define the User table
users = Table('users', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String)
)

people = Table('people', metadata, autoload_with = engine)

# Create the table
# metadata.create_all(engine)

# Insert sample data
with engine.connect() as conn:
    # conn.execute(users.insert(), [
    #     {"name": "John"},
    #     {"name": "Jane"},
    #     {"name": "Doe"}
    # ])

    result = conn.execute(select(people))
    
    for row in result:
        print(row)

        # Clone the row._mapping object
        cloned_row = copy.deepcopy(dict(row._mapping))
        
        # Modify the cloned object
        cloned_row['last_name'] = "Modified_" + str(cloned_row['last_name'])
        
        print(cloned_row)
