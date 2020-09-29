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
* number
* text
* sentence
* text

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

Use the ```--namespace``` argument to add one or more namespaces to be used during xpatht selection. See the example section for - well - an example.

## Installation

Script runs with python 3 (3.8.x and above).

Install faker python library and other dependencies:

```
pip3 install faker
pip3 install glob2
pip3 install lxml
```

Might need to do with sudo:

```
sudo -H pip3 install faker
sudo -H pip3 install glob2
sudo -H pip3 install lxml
```

## Examples

### CSV

The testfiles directory contains some test csv files that demonstrate the usage:

Anonymize the person id in all files, first and last name in persons file

``` sh
# anonymize columns in mulitple csv files:
./multi_anonymizer.py --header-lines 1 \
  --input testfiles/persons.csv:0 testfiles/addresses.csv:1 

./multi_anonymizer.py --header-lines 1  --overwrite --type first_name \
  --input testfiles/persons.csv_anonymized:1

./multi_anonymizer.py --header-lines 1 --overwrite --type last_name \
  --input testfiles/persons.csv_anonymized:2

# support wildcards in file paths (even recursive directories) - need quotes for wildcards to be passed to script:
./multi_anonymizer.py --header-lines 1 --overwrite --type last_name \
  --input "testfiles/**/?erson*s.csv_anonymized:2"
```

### XML

Anonymize element and attribute values in xml files. Use xpath for selection of the element/attribute to be anonymized:

``` sh
# anonymize element values in xml files:
./multi_anonymizer.py --type last_name \
  --input testfiles/addresses.xml:./person/lastname

./multi_anonymizer.py --type firat_name \
  --input testfiles/addresses.xml_anonymized:./person/firstname

# anonymize attribute value usind /@attributeName syntax:
./multi_anonymizer.py --overwrite --type number \
  --input testfiles/addresses.xml_anonymized:./person/address/@id

./multi_anonymizer.py --overwrite --type zip \
  --input testfiles/addresses.xml_anonymized:./person/address/zip
```

Use selector (filter) for elements, then choose the attribute to be anonymized:

``` sh
# do advanced xpath filtering (need single quotes for braces):
# filter on id
./multi_anonymizer.py --type number \
  --input 'testfiles/addresses.xml:./person/address[@id="123"]/@id'

# filter on name, then choose another element's attribute to be anonymized:
./multi_anonymizer.py --type number \
  --input 'testfiles/addresses.xml:.//person/lastname[text()="Riegler"]/../address/@id'  
```

#### Namespaces

``` sh
./multi_anonymizer.py --type last_name \
  --namespace adr=https://github.com/cdaller/multi_anonymizer/addressbook \
  --input testfiles/addresses_ns.xml:./adr:person/lastname
```

As there is no such thing as default namespaces in xpath, just use any prefix for the namespace mapping and for the xpath expression. 

## Thanks

Thanks to joke2k for https://joke2k.net/faker/
and to Benjamin Bengfort for inspiration 
(http://blog.districtdatalabs.com/a-practical-guide-to-anonymizing-datasets-with-python-faker)

## TODO

  * number start/end
  * delete column
  * set fixed value in column
  * create person dict from id (like person_id), then use firstname, lastname, etc. of this person in columns
