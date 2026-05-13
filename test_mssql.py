#!/usr/bin/env python3
from sqlalchemy import create_engine, select, update, MetaData, Table, bindparam

from sqlalchemy.engine import URL
connection_string = ("DRIVER={ODBC Driver 18 for SQL Server};"
                    "SERVER=localhost;"
                    "PORT=1433;"
                    "DATABASE=liferay-db;"
                    "UID=sa;"
                    "PWD=DSmdM@ORF1;"
                    "Encrypt=YES;"
                    "TrustServerCertificate=YES")
db_url = URL.create("mssql+pyodbc", 
                            # username="sa", 
                            # password="DSmdM@ORF1",
                            # host="localhost",
                            # port=1433,
                            # database="liferay-db",
                            query={"odbc_connect": connection_string})

print(db_url)



engine = create_engine(db_url)


# Define the SQLite database connection
#db_url = "mssql+pyodbc://sa:DSmdM@ORF1@myhost:port/databasename?driver=ODBC+Driver+17+for+SQL+Server"
engine = create_engine(db_url, echo=False)

# Define the table name and column names
table_name = "User_"
name_column = "screenName"

# Create a SQLAlchemy MetaData object
metadata = MetaData()

# Reflect the existing table
people_table = Table(table_name, metadata, autoload_with=engine)

select_stmt = select(people_table.c[name_column])
print(select_stmt)

# Connect to the database and execute a select statement
with engine.connect() as connection:
    select_stmt = select(people_table.c[name_column])
    result = connection.execute(select_stmt)

    for row in result:
        original_name = row[0]
        print(original_name)
        
    #connection.commit()

print("Updated names with their hashes")
