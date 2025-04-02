# Multi Anonymizer

This is a completely rewrite (new syntax, better configurability, more faker methods supported) of the anonymizer. For the old version, see readme in the archive folder [[archive/readme.md]].

Allows to anonymize multiple fields in csv, json, xml files or database tables in one pass and in a consistent way.

The important thing is that the anonymization is replacing the same values with the same anonymized values in multiple files or tables! This means that for example a name like Sam Smith would be replaced across all files/tables with its anonymized value (like John Doe).

Please note that this is only valid for one run of the script: all values of the same type (last name, first name, postcode, etc.) will be anonymized with the same anonymized value. This ensured consistency across multiple data sources. This also means that you have to anonymize all sources in one run and cannot split it up across multiple invocations of the script!

The configurations for the fields to anonymize are in json and can be passed via command line parameter (`--config`) or as a file (`--config-file`). Each config can contain one configuration definition or an array of configuration definitions.

The following example shows how to anonymize a json and an xml file that both contain an addressbook with the same entries could be anonymizes, so that the same entries before will be equal (but anonymized) in the same way:

```bash
python anonymizer.py \
  --config '
  {
    "file": "testfiles/persons.json",
    "columns": {
      "$.addressbook.person[*].firstname": "first_name",
      "$.addressbook.person[*].lastname": "last_name",
      "$.addressbook.person[*].comment": "{{ faker.sentence() }}",
      "$.addressbook.person[*].address[*].id": {"type": "number", "params": {"min": 1000, "max": 2000}}
    }
  }
' \
'
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

All types that the faker library supports, can be used. For a full list of supported faker methods use 

```bash
./anonymizer.py --list-faker-methods
```

See below for the full list!

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
# in case of azure identity is needed
pip install azure-identity pyodbc

# csv files 
pip install pandas

# json files:
pip install json jsonpath-ng

# xml files
pip install lxml
```

## Usage

Simple anonymization of first/last name. The script tries to anonymize data so the resemblance to the origial is a close as possible. 

### CSV Files

So if there are two persons with the same last name in the csv file, they will get the same anonymized last name after anonymization! By default, the original source file is not modified, but a new file with the extended name `_anonymized` is created. Use `overwrite` to modify the original file.

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
  --config '
  {
    "file": "testfiles/persons.csv",
    "columns": {
      "age": {
        "type": "number",
        "params": {
          "min": 18,
          "max": 80
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
      "$.addressbook.person[*].lastname": "last_name",
      "$.addressbook.person[*].comment": "{{ faker.sentence() }}",
      "$.addressbook.person[*].address[*].id": {"type": "number", "params": {"min": 1000, "max": 2000}}
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

Anonymize multiple tables with same configuration use `tables` and pass an array of table names.

```bash
python anonymizer.py \
  --config '
  {
    "db_url": "sqlite:///testfiles/my_database.db",
    "tables": ["persons", "employees"],
    "id_column": "id",
    "columns": {
      "first_name": "first_name", 
      "last_name": "last_name"
    }
  }
  '
```

If no id column exists, the replacement is not done row-by-row but all values of the columns are read and each avlue is replaced by its anonymized version in bulk. So one update statement is executed for each different value.

```bash
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

##### Using JOIN'ed Database Tables

For some more complicated where clauses, the table to be anonymized needs to be joined with another table.
The target table (the one to be anonymized) is always aliased with `target_table`!

The `join` syntax must also always have an alias for the joined table!

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
  --config '
  {
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
  }
  '
```

#### Microsoft Sql Server

Note: for Microsoft Sql Server you need to install the odbc driver (on Linux/Mac) and then pass the parameters url-encoded as odbc_connect query parameter: 

```
mssql+pyodbc://?odbc_connect=DRIVER%3D%7BODBC+Driver+18+for+SQL+Server%7D%3BSERVER%3Dlocalhost%3BPORT%3D1433%3BDATABASE%3Dtest-db%3BUID%3Dsa%3BPWD%3DDSmdM%40ORF1%3BEncrypt%3DYES%3BTrustServerCertificate%3DYES;MARS_Connection%3DYes"
```

```bash
python anonymizer.py \
  --locale de_DE \
  --config '
  {
    "db_url": "mssql+pyodbc://?odbc_connect=DRIVER%3D%7BODBC+Driver+18+for+SQL+Server%7D%3BSERVER%3Dlocalhost%3BPORT%3D1433%3BDATABASE%3Dtest-db%3BUID%3Dsa%3BPWD%3DDSmdM%40ORF1%3BEncrypt%3DYES%3BTrustServerCertificate%3DYES;MARS_Connection%3DYes",
    "schema": "dbo_anon",
    "table": "Users",
    "id_column": "userId",
    "where": "companyId = 40201",
    "columns": {
      "firstName": "first_name",
      "lastName": "last_name"
    }
  }
  '
```

The "MARS_Connection=YES" is necessary to prevent some strange SQLAlchemy cursor problems on MSSql!

Please note that bash requires double quotes to expand the environment variable, but JSON also requires double quotes, so all double quotes need to be escaped in this example.


## Config Files

Instead of passing multiple config files on the command line, it might be easier to define the configuration(s) in one or multiple files.

### Configuration Syntax

The following shows all possible configuration properties. Not all of them make sense when used together (e.g. `file` and `table`)!

```json
    {
        "enabled": true,
        "db_url": "xxx",                // db: connection url
        "db_authenticatino": "xxx",     // db authentication: AzureActiveDirectory or None
        "schema": "xxx",                // db: schema
        "table": "xxx",                 // db: table to anonymize
        "tables": ["xxx" "yyy"],        // db: multiple db tables to anonymize
        "id_column": "xxx",             // db: id column 
        "id_columns": [ "xxx", "yyy" ], // db: multiple id columns
        "where": "companyId = 40201",   // db: where clauses
        "join": "xxx",                  // db: join
        "joins": [ "xxx", "yyy" ],      // db: multiple joins
        "columns": {                    // general: define columns to anonymize
            "xxx": "yyy",               // general: column name and value, name can be column name or json/xml path expression
            "zzz": {                    // general: column name and detailed value definition
                "type": "xxx",          // general: type of anonymization
                "params": {             // optional parameters for type
                    "xxx": "yyy"        // parameter key/value
                }
            }
        }
        "separator": "x",               // csv: separator
        "overwrite": false,             // files: overwrite original source file (csv, xml, json)
    }
]

```

### Usage of Environment Variables in Configuration

Some configuration values can also use jinja2 template, especially the usage of special variables can be used to simplify the configuration.

Due to the fact that one cannot escape single quotes within single quotes, a different approch is used to pass the configuration in the command line:

```bash
export DB_FILE=my_database.db
export FILTER_COUNTRY=AT
export NAME_SUFFIX=xyz
python anonymizer.py --config "$(cat <<EOF
{
  "db_url": "sqlite:///testfiles/{{ env[\"DB_FILE\"] }}",
  "table": "persons",
  "where": "COUNTRY='{{ env[\"FILTER_COUNTRY\"] }}'",
  "columns": {
    "first_name": "first_name",
    "last_name": "{{ faker.last_name() }}{{ env['NAME_SUFFIX'] }}"
  }
}
EOF
)"
```

Currently, jinja2 templates are only allowed in the `db_url`, `schema`, and in the `where` keys of the configuration.
The `env` context is also usable in the anonymization value jinja2 templates.

## Special jinja2 Mechanism

If a jinja2 template returns the string `"None"`, it is replaced by `None` (`null` value). Otherwise it would be impossible to set a (database column) value to `null`.

## Encoding

For xml, csv and json files, use the `--encoding` command line parameter to set the encoding, the files are read and written.

For database data, the encoding needs to be added to the database url. This is dependent on the database.

For MySql this seems to work (untested): `"mysql+pymysql://user:pass@host/test?charset=utf8mb4"`

## Consistency across multiple runs

If consistency across multiple runs should be achieved, the mapping between original values and anonymized values can be exported at the end of an anonymization run and imported at the beginning of the next using the `--cache-file` parameter. This will import/export a json file. Please not that the locale should be coded into the filename to not mixup the mapping between different anonymization runs.

```bash
 ./anonymizer.py --locale de_AT --config-file db_anonymization.json --cache-file database_anonymization_de_AT.json
 ```

## Unique Value Generation

In case an anonymized value has to be unique, the faker method can be prefixed with `unique/`. This guarantees that all values created are unique and will not be repeated during a run.

This comes handy if a database table has a unique key constraint on a column and duplicate values need to be prevented at any case.

Please notice that for the most faker methods uniqueness might be hard to achieve as there are only a limited number of fake values available. For example, there are only 1000 last names available in faker. In this case, uniqueness cannot be achieved when there are more than 1000 values needed and an error is thrown.

For other faker methods, this works better (like `ascii_company_email`). So using `unique/ascii_company_email` guarantees unique email addresses (as long as possible).

```bash
python anonymizer.py \
--config '
  {
    "file": "testfiles/persons.csv",
    "columns": {
      "email": "unique/ascii_company_email"
    },
    "separator": ";"
  }
'
```

## Available Faker Methods

The script is able to list all faker methods. If `--list-faker-methods-and-examples`is used, an example for the faker method is also printed. Set the `--locale` to get example values in a different locale.

```bash
./anonymizer.py --list-faker-methods
Available Faker methods:
- aba
- add_provider
- address
- administrative_unit
- am_pm
- android_platform_token
- ascii_company_email
- ascii_email
- ascii_free_email
- ascii_safe_email
- bank_country
- basic_phone_number
- bban
- binary
- boolean
- bothify
- bs
- building_number
- catch_phrase
- century
- chrome
- city
- city_prefix
- city_suffix
- color
- color_hsl
- color_hsv
- color_name
- color_rgb
- color_rgb_float
- company
- company_email
- company_suffix
- coordinate
- country
- country_calling_code
- country_code
- credit_card_expire
- credit_card_full
- credit_card_number
- credit_card_provider
- credit_card_security_code
- cryptocurrency
- cryptocurrency_code
- cryptocurrency_name
- csv
- currency
- currency_code
- currency_name
- currency_symbol
- current_country
- current_country_code
- date
- date_between
- date_between_dates
- date_object
- date_of_birth
- date_this_century
- date_this_decade
- date_this_month
- date_this_year
- date_time
- date_time_ad
- date_time_between
- date_time_between_dates
- date_time_this_century
- date_time_this_decade
- date_time_this_month
- date_time_this_year
- day_of_month
- day_of_week
- del_arguments
- dga
- domain_name
- domain_word
- dsv
- ean
- ean13
- ean8
- ein
- email
- emoji
- enum
- file_extension
- file_name
- file_path
- firefox
- first_name
- first_name_female
- first_name_male
- first_name_nonbinary
- fixed_width
- format
- free_email
- free_email_domain
- future_date
- future_datetime
- get_arguments
- get_formatter
- get_providers
- get_words_list
- hex_color
- hexify
- hostname
- http_method
- http_status_code
- iana_id
- iban
- image
- image_url
- internet_explorer
- invalid_ssn
- ios_platform_token
- ipv4
- ipv4_network_class
- ipv4_private
- ipv4_public
- ipv6
- isbn10
- isbn13
- iso8601
- items
- itin
- job
- job_female
- job_male
- json
- json_bytes
- language_code
- language_name
- last_name
- last_name_female
- last_name_male
- last_name_nonbinary
- latitude
- latlng
- lexify
- license_plate
- linux_platform_token
- linux_processor
- local_latlng
- locale
- localized_ean
- localized_ean13
- localized_ean8
- location_on_land
- longitude
- mac_address
- mac_platform_token
- mac_processor
- md5
- military_apo
- military_dpo
- military_ship
- military_state
- mime_type
- month
- month_name
- msisdn
- name
- name_female
- name_male
- name_nonbinary
- nic_handle
- nic_handles
- null_boolean
- numerify
- opera
- paragraph
- paragraphs
- parse
- passport_dates
- passport_dob
- passport_full
- passport_gender
- passport_number
- passport_owner
- password
- past_date
- past_datetime
- phone_number
- port_number
- postalcode
- postalcode_in_state
- postalcode_plus4
- postcode
- postcode_in_state
- prefix
- prefix_female
- prefix_male
- prefix_nonbinary
- pricetag
- profile
- provider
- psv
- pybool
- pydecimal
- pydict
- pyfloat
- pyint
- pyiterable
- pylist
- pyobject
- pyset
- pystr
- pystr_format
- pystruct
- pytimezone
- pytuple
- random_choices
- random_digit
- random_digit_above_two
- random_digit_not_null
- random_digit_not_null_or_empty
- random_digit_or_empty
- random_element
- random_elements
- random_int
- random_letter
- random_letters
- random_lowercase_letter
- random_number
- random_sample
- random_uppercase_letter
- randomize_nb_elements
- rgb_color
- rgb_css_color
- ripe_id
- safari
- safe_color_name
- safe_domain_name
- safe_email
- safe_hex_color
- sbn9
- secondary_address
- seed_instance
- seed_locale
- sentence
- sentences
- set_arguments
- set_formatter
- sha1
- sha256
- simple_profile
- slug
- ssn
- state
- state_abbr
- street_address
- street_name
- street_suffix
- suffix
- suffix_female
- suffix_male
- suffix_nonbinary
- swift
- swift11
- swift8
- tar
- text
- texts
- time
- time_delta
- time_object
- time_series
- timezone
- tld
- tsv
- unix_device
- unix_partition
- unix_time
- upc_a
- upc_e
- uri
- uri_extension
- uri_page
- uri_path
- url
- user_agent
- user_name
- uuid4
- vin
- windows_platform_token
- word
- words
- xml
- year
- zip
- zipcode
- zipcode_in_state
- zipcode_plus4
```


## TODOs

* [x] use faker calls in jinja2 expression (for example `{{ street }} {{ zip }} {{ town}}`)
* [x] random numbers, min, max
* [x] json/xml in database columns
* [ ] xml: support namespaces
* [ ] regexp: only anonymize part of the content
* db
  * [x] table schema
  * [x] where clause for db
  * [x] tables without id column
  * [ ] union with other tables for where clause
  * [x] support multiple id columns
  * [ ] only load columns that are used (to be anonymized or referenced!)
* [x] add counter, how many values were anonymized and duration of anonymization
  * [x] add progress info for lots of rows!
* [ ] multiple files using wildcards
* [ ] support csv files without header
* [x] cache faker dictionaries, so one can anonymize across multiple runs!
  * include keep language (set in filename)
* json
  * [ ] allow references to other json_path elements (like row['xy'])
* config
  * [ ] allow to set environment variables on execution that are replacing variables used in the configuration
