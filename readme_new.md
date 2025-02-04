# Anonymizer

Allows to anonymize multiple fields in csv, json, xml or database tables in a consitent way.

## Setup

For full feature, install the  following packages. If no database support is needed, you can skip the sqlalchemy. Same is valid for json, xml and panda (for csv).

```bash
pip install faker jinja2 argparse
# depending on the target systems to be anonymized, one needs to install packages:
# sql  databases:
pip install sqlalchemy sqlalchemy.orm 
# postgresql
pip install psycopg2-binary
# mysql
pip install pymysql

# csv files 
pip install pandas

# json files:
pip install json jsonpath-ng

# xml files
pip install lxml
```

## Usage

Simple anonymization of first/last name. The script tries to anonymize data so the resemblance to the origial is a close as possible. So if there are two persons with the same last name in the csv file, they will get the same anonymized last name after anonymization! By default, the original source file is not modified, but a new file with the extended name `_anonymized` is created. Use `overwrite` to modify the original file.

```bash
python anonymizer.py \
  --config '
  {
    "file": "testfiles/persons.csv",
    "columns": {
      "firstname": "first_name",
      "lastname": "last_name"
    },
    "separator": ";"
  }
  '
```

Using a locale to define the anonymized value's location:

```bash
python anonymizer.py \
  --locale de_DE \
  --config '
  {
    "file": "testfiles/persons.csv",
    "columns": {
      "firstname": "first_name",
      "lastname": "last_name"
    },
    "separator": ";"
  }
'
```

Use a number column and give min/max for the number - this form uses a different syntax giving the faker type as `type`. This allows to add some parameters. Currently, `number` is the only type having parameters (`min` and `max`).

```bash
python anonymizer.py \
  --locale de_DE \
  --config '
  {
    "file": "testfiles/persons.csv",
    "columns": {
      "age": {
        "type": "number",
        "params": {
          "min": 18,
          "max": 40
        }
      }
    },
    "separator": ";"
  }
'
```

The notation using the "type" can be used also for other faker methods:

```bash
python anonymizer.py \
  --config '
  {
    "file": "testfiles/persons.csv",
    "columns": {
      "email": {
        "type": "email"
      }
    },
    "separator": ";"
  }
'
```

The following example shows the usage of a jinja2 template to fill the email address with the anonymized first- and last names of the persons.

```bash
python anonymizer.py \
  --config '
{
    "file": "testfiles/persons.csv",
    "columns": {
        "firstname": "first_name",
        "lastname": "last_name",
        "email": "{{ row[\"firstname\"].lower() }}.{{ row[\"lastname\"].lower() }}@example.com"
    },
    "overwrite": false,
    "separator": ";"
}
'
```

Anonymized multiple csv files in one go:

```bash
# anonymize two csv files at once and replace the address in a second csv file:
python anonymizer.py \
  --config '
  {
    "file": "testfiles/persons.csv",
    "columns": {
        "firstname": "first_name",
        "lastname": "last_name"
    },
    "overwrite": false,
    "separator": ";"
  }
  ' \
  '
  {
    "file": "testfiles/addresses.csv",
    "columns": {
        "address": "address"
    },
    "separator": ";"
  }
  '
```

By default, faker uses a two line address. Use template variables to create an own address by the use of `street_address`, `postcode` and `city` faker methods:

```bash
python anonymizer.py \
  --config '
  {
    "file": "testfiles/addresses.csv",
    "columns": {
        "address": "{{ faker.street_address() }} {{ faker.postcode() }} {{ faker.city() }}"
    },
    "separator": ";"
  }
  '
```

### JSON Files using json paths

Json files can be anonymized by the use of json paths to define what and how to anonymize:

```bash
python anonymizer.py \
  --config '
  {
    "file": "testfiles/persons.json",
    "columns": {
      "$.addressbook.person[*].firstname": "first_name",
      "$.addressbook.person[*].lastname": "last_name"
    }
  }
'
```

### XML Files using xPaths

Same can be done for xml files (xml elements and xml attributes) using xPath expressions:

```bash
python anonymizer.py \
  --config '
  {
    "file": "testfiles/persons.xml",
    "columns": {
      "//person/firstname": "first_name",
      "//person/lastname": "last_name",
      "//person/comment": "{{ faker.sentence() }}",
      "//address/@id": {"type": "number", "params": {"min": 1000, "max": 2000}}
    }
  }
'
```

### Database Tables

One or multiple database tables can be anonymized consistently in one go.

If only part of the table should be anonymized, the rows can be filtered using a `where` clause. Table schema is also supported by the `schema` keyword.

Anonymizing database tables comes in two flavours:
* tables with unique id column: The anonymizer reads all rows (`where` clause applied) and anonymizes all columns selected with their anonymization types.
* tables without id column: as there is no unique id, the script cannot update row by row but needs to update all values in the selected columns (`where` clause is also applied).

#### Database Tables with a unique id column

The anonymizer reads all rows (`where` clause applied) and anonymizes all columns selected with their anonymization types. This allows to use column values of the same row as templates (e.g. for the consisten anonymization of email addresses).

The id columns must be set by `id_column` (single value) or `id_columns` (array) properties.

The following creates an sqlite database holding two tables and anonymize the content. In this case, the original values are overwritten!

```bash
rm testfiles/my_database.db
# create test database:
testfiles/create_sqlite.py testfiles/my_database.db

# show content of db:
sqlite3 testfiles/my_database.db "select * from persons"

# anonymize db table
python anonymizer.py \
  --config '
  {
    "db_url": "sqlite:///testfiles/my_database.db",
    "table": "persons",
    "id_column": "id",
    "columns": {
      "first_name": "first_name", 
      "last_name": "last_name"
    }
  }
  '

python anonymizer.py \
  --config '
  {
    "db_url": "sqlite:///testfiles/my_database.db",
    "table": "persons",
    "id_columns": ["id"],
    "columns": {
      "first_name": "first_name", 
      "last_name": "last_name"
    }
  }
  '
```

Using a where clause to filter to specific rows in the database:

```bash
python anonymizer.py \
  --config '
  {
    "db_url": "sqlite:///testfiles/my_database.db",
    "table": "persons",
    "id_column": "id",
    "where": "id > 1005",
    "columns": {"first_name": "first_name", "last_name": "last_name"}
  }'
```

Using templates to anonymize column values consistently from other row values. Please note that the template may also contain non anonymized column values!

```bash
python anonymizer.py \
  --config '{
    "db_url": "sqlite:///testfiles/my_database.db",
    "table": "persons",
    "id_column": "id",
    "columns": {
      "first_name": "first_name",
      "last_name": "last_name",
      "email": "{{ (row[\"first_name\"] or \"\").lower() }}.{{ (row[\"last_name\"] or \"\").lower() }}@example.com"
    }
  }'
```

##### Using JOIN'ed Database Tables

For some more complicated where clauses, the table to be anonymized needs to be joined with another table.
The target table (the one to be anonymized) is called `target_table`

With id column:

```bash
python anonymizer.py \
  --config '
  {
    "db_url": "sqlite:///testfiles/my_database.db",
    "table": "persons",
    "id_column": "id",
    "where": "email.id > 5",
    "join": "EMAILS email ON target_table.id = email.person_id",
    "columns": {
      "first_name": "first_name",
      "last_name": "last_name"
    }
  }'
```

Without id column JOIN is currently not supported as the update command does not support JOINs.


#### Database Tables without a unique id column

As there is no unique id, the script cannot update row by row but needs to update all values in the selected columns. So a distinct set of values of the given column(s) are fetched, all values are anonymized and a single update is then executed for every distinct value to update all rows at once.

This has the advantage that not for every row an update statement is executed (performance!), but has the severe drawback, that there is no "row-context" that can be referenced to set values.

So you can easily set all rows having a first name of "Mike" and last name of "Smith" to its anonymized counterparts. But values are not replaced row by row, one cannot set the email address to "<firstname>.<lastname>@example.com"! One can anonymize the email column, but not with a jinja2 template using values from other columns!

```bash
rm testfiles/my_database.db
# create test database:
testfiles/create_sqlite.py testfiles/my_database.db

# show content of db:
sqlite3 testfiles/my_database.db "select * from persons"

# anonymize db table
python anonymizer.py \
  --config '
  {
    "db_url": "sqlite:///testfiles/my_database.db", 
    "table": "persons", 
    "columns": {
      "first_name": "first_name", 
      "last_name": "last_name"
    }
  }
'
```

#### JSON/XML Contained in Database Table Columns

If a json string is contained in a database table, one can anonymize rows and json/xml content in columns at the same time defining the json columns by `json_column` and `xml_column`.

```bash
# anonymize db table and json strings in the database
python anonymizer.py \
  --config '{
    "db_url": "sqlite:///testfiles/my_database.db",
    "table": "persons",
    "id_column": "id",
    "columns": {"first_name": "first_name", "last_name": "last_name"},
    "json_columns": {
      "json_data": {
        "$.person.firstname": "first_name",
        "$.person.lastname": "last_name"
      }
    }
  }'
```

## Encoding

For xml, csv and json files, use the `--encoding` command line parameter to set the encoding, the files are read and written.

For database data, the encoding needs to be added to the database url. This is dependent on the database.

For MySql this seems to work (untested): `"mysql+pymysql://user:pass@host/test?charset=utf8mb4"`

## TODO

* [x] use faker calls in jinja2 expression (for example `{{ street }} {{ zip }} {{ town}}`)
* [x] random numbers, min, max
* [x] json/xml in database columns
* [ ] xml: support namespaces
* regexp: only anonymize part of the content
* db
  * [x] table schema
  * [x] where clause for db
  * [x] tables without id column
  * [ ] union with other tables for where clause
  * [x] support multiple id columns
* [ ] add counter, how many values were anonymized
* [ ] multiple files using wildcards
