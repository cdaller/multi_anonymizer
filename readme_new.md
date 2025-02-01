# Anonymizer

Allows to anonymize multiple fields in csv, json, xml or database tables in a consitent way.

## Setup

For full feature, install the  following packages. If no database support is needed, you can skip the sqlalchemy. Same is valid for json, xml and panda (for csv).

```bash
pip install sqlalchemy faker jinja2 pandas psycopg2-binary pymysql jsonpath-ng lxml argparse
```

## Usage

```bash
# simple anonymization of first/last name:
python anonymizer.py \
  --config '{"file": "testfiles/persons.csv", "columns": {"firstname": "first_name", "lastname": "last_name"}, "separator": ";"}'

# use a locale:
python anonymizer.py \
  --locale de_DE \
  --config '{"file": "testfiles/persons.csv", "columns": {"firstname": "first_name", "lastname": "last_name"}, "separator": ";"}'

# simple anonymization of first/last name and use a template for the email address
# for easier configuration, use a environment variable to store the config. This makes the excaping of the various quotes easier and allows a multiline configuration
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
python anonymizer.py --config "${CSV_PERSON_CONFIG}"

# use a jinja2 template to create the email address
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
# anonymize two csv files at once:
CSV_ADDRESS_CONFIG='
{
    "file": "testfiles/addresses.csv",
    "columns": {
        "address": "address",
    },
    "separator": ";"
}
'
python anonymizer.py --config "${CSV_PERSON_CONFIG}" --config "${CSV_ADDRESS_CONFIG}"



python anonymizer.py \
  --config '{"file": "x.csv", "columns": {"firstname": "first_name", "lastname": "last_name"}}' \
  --config '{"file": "y.csv", "columns": {"email": "email", "city": "city"}}'


python anonymizer.py \
  --config '{"table": "users", "id_column": "id", "columns": {"name": "name", "email": "email"}}'


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

* random numbers, min, max
* regexp
* table schema