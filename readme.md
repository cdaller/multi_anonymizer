# Multi Anonymizer

The main target of this script is to anonymize one value consistently in multiple files.
E.g. the id of a bank account is used in multiple files - anonymization should replace a given
bank account id in all files with the same value, so the consistency across all files is not broken by 
the anonymization process.

The anonymization is done by the joe2k/faker library - so in principle all anonymization types of this library are supported. In practice, only a couple are really used:
* name
* last_name
* first_name
* email
* phone_number
* zip code
* street
* street_address
* city
* iban
* number[:min[:max]]
  * min/max is optional (e.g. number:12:99 or number:100)
* text
* sentence
* text
* company

More can be easily added.

Note: As the script now also handles xml files, it was renamed to from csv_anonymizer.py to multi_anonymizer.py

## CSV

CSV Anonymizer: reads one or more csv files and anonymizes one column with a given type (e.g. name, number).
It is able to anonymize different columns that contain the same values from different csv files.

E.g. the account number of a bank account is used in a.csv in column 3 and in b.csv in column 4:

    multi_anonymizer --type=number --input a.csv:3 b.cvs:4 foobar_*.cvs:6

Same, but with different delimter and a wildcard file selector (wildcards are handled by script, not by shell):

    multi_anonymizer --type=name --delimiter "," --input a.csv:3 b.cvs:4 "**/foobar_*.cvs:6"

would anonymize the bank account number in both files in a way that bank account number 123456 is anonymized to a random integer - but to the same random integer in all rows in both files.

Please not that the default values might not be appropriate for you (e.g. delimiter is set to semicolon by default, encoding is set to ISO-8859-15, number of header lines to 0, etc.), so check the command line arguments (```--help```) for possible switches and their default values.

Another tiny tool included in this package is ```csv_filterlines.py``` that can be used to filter lines in a csv file (but still print the header lines untouched). Python has the advantage of being able to handle various encodings quite nice, which is a hassle with other tools/combination of other tools (```head ... | grep ...```).

    csv_filterlines.py --header-lines=1 --encoding UTF-16 input.csv output.csv

## XML

The script can also anonymize values in xml entities/attributes of one or more xml files. Instead of a column as in csv files, an xpath selector is used to define, which entities/attributes will be anonymized. 

    multi_anonymizer --type=last_name --input addresses.xml:./person/lastname

And example for attributes is 

    multi_anonymizer --type=number --input addresses.xml:./person/@id

See the examples below for more and more complicated examples.

### Namespaces

Please note that if the xml uses namespaces the anonymization might not work when the xpath expression does not correctly use the correct namespace.

Use the ```--namespace``` argument to add one or more namespaces to be used during xpath selection. See the example section for - well - an example.

Please note, as the right most colon in the input string is used as a separator between the filename and the selector, you must escape the colon in the xpath expression with a double colon! See examples for details.

## Installation

Script runs with python 3 (3.8.x and above).

Install faker python library and other dependencies:

```bash
pip3 install faker
pip3 install glob2
pip3 install jinja2
# optional, only needed when you want to parse xml files:
pip3 install lxml
```

Might need to do with sudo:

```bash
sudo -H pip3 install faker
sudo -H pip3 install glob2
sudo -H pip3 install jinja2
# optional, only needed when you want to parse xml files:
sudo -H pip3 install lxml
```

## Examples

### CSV

The testfiles directory contains some test csv files that demonstrate the usage:

Anonymize the person id in all files, first and last name in persons file

```sh
# anonymize id columns in mulitple csv files:
./multi_anonymizer.py --header-lines 1 --type number \
  --input testfiles/persons.csv:0 testfiles/addresses.csv:1

# new syntax:
./multi_anonymizer.py --header-lines 1 \
  --input "testfiles/persons.csv:(type=number,column=0)" "testfiles/addresses.csv:(type=number,column=1)"

./multi_anonymizer.py --header-lines 1  --overwrite --type first_name \
  --input testfiles/persons.csv_anonymized:1

./multi_anonymizer.py --header-lines 1 --overwrite --type last_name \
  --input testfiles/persons.csv_anonymized:2

# new syntax
# if same file is modified, '--overwrite' is needed. 
# As the filename does not end in 'csv', 'input_type' is also needed!
./multi_anonymizer.py --header-lines 1 --overwrite \
  --input "testfiles/persons.csv_anonymized:(input_type=csv,type=first_name,column=1)" \
          "testfiles/persons.csv_anonymized:(input_type=csv,type=last_name,column=2)"

# support wildcards in file paths (even recursive directories) - need quotes for wildcards to be passed to script:
./multi_anonymizer.py --header-lines 1 --overwrite --type last_name \
  --input "testfiles/**/?erson*s.csv_anonymized:2"
```

### XML

If xml anonymization is needed, the pyhton lxml package needs to be installed:

```sh
pip install lxml
```

Anonymize element and attribute values in xml files. Use xpath for selection of the element/attribute to be anonymized:

```sh
# anonymize element values in xml files:
./multi_anonymizer.py --type last_name \
  --input testfiles/addresses.xml:./person/lastname

./multi_anonymizer.py --type first_name \
  --input testfiles/addresses.xml_anonymized:./person/firstname

# anonymize attribute value usind /@attributeName syntax:
./multi_anonymizer.py --overwrite --type number \
  --input testfiles/addresses.xml_anonymized:./person/address/@id

./multi_anonymizer.py --overwrite --type zip \
  --input testfiles/addresses.xml_anonymized:./person/address/zip
```

Use xpath selector (filter) for elements, then choose the attribute to be anonymized:

```sh
# do advanced xpath filtering (need single quotes for braces):
# filter on id
./multi_anonymizer.py --type number \
  --input 'testfiles/addresses.xml:./person/address[@id="123"]/@id'

# filter on name, then choose another element's attribute to be anonymized:
./multi_anonymizer.py --type number \
  --input 'testfiles/addresses.xml:.//person/lastname[text()="Riegler"]/../address/@id'  
```

#### Namespaces

NOTE: Colons in xpath expressions need to be escaped by a double colon to allow proper separation between the input file and the xpath expression (right most colon):

```sh
./multi_anonymizer.py --type last_name \
  --namespace adr=https://github.com/cdaller/csv_anonymizer/addressbook  \
  --input testfiles/addresses_ns.xml:./adr::person/lastname

# new syntax allows to anonymize two different properties at once (needs --overwrite)!
./multi_anonymizer.py --overwrite \
  --namespace adr=https://github.com/cdaller/csv_anonymizer/addressbook  \
  --input "testfiles/addresses_ns.xml:(type=last_name,xpath=./adr::person/lastname)" \
          "testfiles/addresses_ns.xml:(type=first_name,xpath=./adr::person/firstname)"

```

As there is no such thing as default namespaces in xpath, just use any prefix for the namespace mapping and for the xpath expression. 

### Database

If database anonymization is needed, the python SQLAlchemy package needs to be installed:

```sh
pip install SQLAlchemy
```

Depending on the database you want to use, you might need further installations!
SQLAlchemy is used internally, so please see https://docs.sqlalchemy.org/en/20/dialects/index.html for details, how to connect to different database dialects.

Please note that for database anonymization, the anonymized values always replace the original values!

```sh
# create test database:
testfiles/create_sqlite.py testfiles/my_database.db

# anonymize name column in table people
./multi_anonymizer.py \
  --input "sqlite:///testfiles/my_database.db:(input_type=db,type=name,table=people,column=name)"

# anonymize age column using a min/max age  
./multi_anonymizer.py \
  --input "sqlite:///testfiles/my_database.db:(type=number,min=18,max=48,table=people,column=age)"
```

Note: for MSSql you need to install the odbc driver (on Linux/Mac) and then pass the parameters url-encoded as odbc_connect query parameter:

```bash
./multi_anonymizer.py --type word \
  --input "mssql+pyodbc://?odbc_connect=DRIVER%3D%7BODBC+Driver+18+for+SQL+Server%7D%3BSERVER%3Dlocalhost%3BPORT%3D1433%3BDATABASE%3Dliferay-db%3BUID%3Dsa%3BPWD%3Dxxxx%3BEncrypt%3DYES%3BTrustServerCertificate%3DYES;MARS_Connection%3DYes:User_/screenName"
```

The "MARS_Connection=YES" is necessary to prevent some strange SQLAlchemy cursor problems on MSSql!

### Multiple anonymized values and templates

If you have a table of columns ```first_name```, ```last_name```, ```email``` and the content of column ```email``` needs to be in sync with the first and last name, you can use the template feature which also allows some string modifications like upper-, lowercasing. The templating is done by jinja2.

The special variables ```__value__``` and ```___original_value___``` can also be used in the templates. ```___value___``` is the anonymized value and this is also the default template if no other is given.

Apart from that, all column names that were used **before** can be used. The replacement works in the order of the given input arguments. So you cannot access the value of a column of an input selector that is defined after the current input selector!

```bash
./multi_anonymizer.py --header-lines 1  --overwrite \
  --input \
    "sqlite:///testfiles/my_database.db:(input_type=db,type=last_name,table=people,column=last_name)" \
    "sqlite:///testfiles/my_database.db:(input_type=db,type=first_name,table=people,column=first_name,template={{__value__|lower}})" \
    "sqlite:///testfiles/my_database.db:(input_type=db,type=email,table=people,column=email,template={{first_name|unidecode|lower}}.{{last_name|unidecode|lower}}@example.com)" \
    "sqlite:///testfiles/my_database.db:(input_type=db,type=number,min=18,max=60,table=people,column=age)"
```

## Thanks

Thanks to joke2k for https://joke2k.net/faker/
and to Benjamin Bengfort for inspiration 
(http://blog.districtdatalabs.com/a-practical-guide-to-anonymizing-datasets-with-python-faker)

## TODO

  * number start/end
  * delete column
  * set fixed value in column
  * create person dict from id (like person_id), then use firstname, lastname, etc. of this person in columns
