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

## Requirements

I want Python script to anonymize data. The following is a list of requirements. I want you to generate a script that fulfilles all requirements, not only parts of them!
* Python script should have a shebang "#!/usr/bin/env python3"
* User can pass one or multiple command line parameters to define the source data to be anonymized.
* These configuration can define files (csv, json, xml files) or tables in database connections.
* For anonymization, the faker library should be used.
* For database connetion, the sqlalchemy library should be used.
* The python imports should be optional. If I do not want database or xml/json anonymization, the libraries must not be mandatory.
* For anonymization in files (csv, json or xml) I want to allow "overwrite" to overwrite the source file. Default should be to create a new file.
* Anonymization should be consistent across multiple anonymization targets. So I want to give multiple configs and for example all last names "Huber" should be replaced by the same faker values.
* I want to use jinja2 templates to be able to create new values. In the templates, I want to reference values from other columns in the table or csv file using syntax like the following:
```
{
    "file": "testfiles/persons.csv",
    "columns": {
        "firstname": "first_name",
        "lastname": "last_name",
        "email": "{{ row["firstname"].lower() }}.{{ row["lastname"].lower() }}@example.com"
    },
    "overwrite": false,
    "separator": ";"
}
```
* I also want to be able to create new values from faker values like "{{ faker.zip }} {{ faker.city }}" using faker methods in specific columns.
* for json anonymization, I want to give json-paths to define, which fields should be anonymized.
* for xml anonymization, I want to give xml paths to define, which fields should be anonymized.
* For database anonymization, I want to define an id_column that can be used to reference the row to anonymize.
* I want to be able to anonymize json or xml strings, that are contained in a database table column.
* I want to set the locale that is used to anonymize values with faker library
* as a command line parameter to the script I want to get a list of valid faker methods. If this parameter is used, the script should exist and ignore all configuration that are passed.
* faker anonymization should be extended by the type "number" to give a random number. In this cases, a min and a max value should be definable. This is usefull to set a random age between 20 and 80 years old. The min and max number should be optionally settable by the user when defining the type in the configuration.
* For csv files I want to define the separator.
* For csv files I want to define if the file contains a header line.
* The command line help should print examples to let the user know how to use anonymization for csv files (including explamples for jinja2 templates), json and xml files. And also for database usage using an sqlite database with a table "persons" with columns "firstname", "lastname", "age", "email" and "json_data" having an object "person" with properties "firstname", "lastname", "age" and "email". The examples should include how to set the anonymized email address to "firstname.lastname@example.com" all in lowercase using jinja2 templates.

## Usage

```bash
# simple anonymization of first/last name:
python anonymizer.py \
  --config '{"file": "testfiles/persons.csv", "columns": {"firstname": "first_name", "lastname": "last_name"}, "separator": ";"}'

# use a locale:
python anonymizer.py \
  --locale de_DE \
  --config '{"file": "testfiles/persons.csv", "columns": {"firstname": "first_name", "lastname": "last_name"}, "separator": ";"}'

# use a number column and give min/max for the number:
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

# the notation using the "type" can be used also for other faker methods:
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

# simple anonymization of first/last name and use a template for the email address
# for easier configuration, use a environment variable to store the config. This makes the excaping of the various quotes easier and allows a multiline configuration
CSV_PERSON_CONFIG='
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
python anonymizer.py --config "${CSV_PERSON_CONFIG}"

# same execution without passing the config as environment variable:
python anonymizer.py \
  --config '{"file": "testfiles/persons.csv", "columns": {"firstname": "first_name", "lastname": "last_name", "email": "{{ row[\"firstname\"].lower() }}.{{ row[\"lastname\"].lower() }}@example.com"},"separator": ";"}'
```

```bash
# anonymize two csv files at once and replace the address in a second csv file:
CSV_PERSON_CONFIG='
{
    "file": "testfiles/persons.csv",
    "columns": {
        "firstname": "first_name",
        "lastname": "last_name"
    },
    "overwrite": false,
    "separator": ";"
}
'

CSV_ADDRESS_CONFIG='
{
    "file": "testfiles/addresses.csv",
    "columns": {
        "address": "address"
    },
    "separator": ";"
}
'
python anonymizer.py --config "${CSV_PERSON_CONFIG}" "${CSV_ADDRESS_CONFIG}"

# by default, faker uses a two line address. Use template variables to create an own address:
CSV_ADDRESS_CONFIG='
{
    "file": "testfiles/addresses.csv",
    "columns": {
        "address": "{{ faker.street_address() }} {{ faker.postcode() }} {{ faker.city() }}"
    },
    "separator": ";"
}
'
python anonymizer.py --config "${CSV_PERSON_CONFIG}" "${CSV_ADDRESS_CONFIG}"
```

### JSON Files using json paths

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

Anonymization can be done for xml elements and xml attributes:

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

```bash
python anonymizer.py \
  --config '
  {
    "file": "testfiles/persons.xml",
    "columns": {
      "//address/@id": {"type": "number", "params": {"min": 1000, "max": 2000}}
    }
  }
'
```


### Database Tables

```bash
rm testfiles/my_database.db
# create test database:
testfiles/create_sqlite.py testfiles/my_database.db

# show content of db:
sqlite3 testfiles/my_database.db "select * from persons"

# anonymize db table
python anonymizer.py \
  --config '{"db_url": "sqlite:///testfiles/my_database.db", "table": "persons", "id_column": "id", "columns": {"first_name": "first_name", "last_name": "last_name"}}'
```

#### Json Contained in Database Tables

```bash
# anonymize db table
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

```json
{
    "file": "testfiles/persons.csv",
    "columns": {
        "age": { "type": "number", "params": { "min": 20, "max": 80 } }
    },
    "overwrite": false
}
```

python anonymizer.py \
  --config '{"table": "users", "id_column": "id", "json_columns": {"user_data": {"$.users[*].phone": "phone_number"}}}'


python anonymizer.py \
  --config '{"table": "users", "id_column": "id", "xml_columns": {"user_data": {"//user/email": "email"}}}'


python anonymizer.py \
  --config '{"file": "x.csv", "columns": {"firstname": "first_name", "lastname": "last_name"}}' \
  --config '{"table": "users", "id_column": "id", "columns": {"name": "name", "email": "email"}}' \
  --config '{"table": "users", "id_column": "id", "json_columns": {"user_data": {"$.users[*].phone": "phone_number"}}}' \
  --config '{"table": "users", "id_column": "id", "xml_columns": {"user_data": {"//user/email": "email"}}}'


```

## TODO

* [x] use faker calls in jinja2 expression (for example `{{ street }} {{ zip }} {{ town}}`)
* [x] random numbers, min, max
* regexp
* db
  * table schema
  * where clause for db
