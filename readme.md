# CSV Anonymizer

CSV Anonymizer: reads one or more csv files and anomyizes one column with a given type (e.g. name, number).
It is able to anonymize different columns that contain the same values from different csv files.

E.g. the account number of a bank account is used in a.csv in column 3 and in b.csv in column 4:

    csv_anonymizer --type=number --input a.csv:3 b.cvs:4 foobar_*.cvs:6

Same, but with different delimter and a wildcard file selector (wildcards are handled by script, not by shell):

    csv_anonymizer --type=name --delimiter "," --input a.csv:3 b.cvs:4 "**/foobar_*.cvs:6"

would anonymize the bank account number in both files in a way that bank account number 123456 is anonymized to a random integer - but to the same random integer in all rows in both files.

Please not that the default values might not be appropriate for you (e.g. delimiter is set to semicolon by default, encoding is set to ISO-8859-15, number of header lines to 0, etc.), so check the command line arguments (```--help```) for possible switches and their default values.

Another tiny tool included in this package is ```csv_filterlines.py``` that can be used to filter lines in a csv file (but still print the header lines untouched). Python has the advantage of being able to handle various encodings quite nice, which is a hassle with other tools/combination of other tools (```head ... | grep ...```).

    csv_filterlines.py --header-lines=1 --encoding UTF-16 input.csv output.csv
    
## XML

FIXME: add namespace notation
xpath selector: ./person/address[@id=123]/@id

### Namespaces

Please note that if the xml uses namespaces the anonymization might not work when the xpath expression does not correctly use the correct namespace.

Use the ```--namespace``` argument to add one or more namespaces to be used during xpatht selection. See the example section for - well - an example.

## Installation

Install faker python library and other dependencies:

```
pip3 install Faker
pip3 install glob2
```

## Examples

### CSV

The testfiles directory contains some test csv files that demonstrate the usage:

Anonymize the person id in all files, first and last name in persons file

``` sh
# anonymize columns in mulitple csv files:
./csv_anonymizer.py --header-lines 1 \
  --input testfiles/persons.csv:0 testfiles/addresses.csv:1 

./csv_anonymizer.py --header-lines 1  --overwrite --type first_name \
  --input testfiles/persons.csv_anonymized:1

./csv_anonymizer.py --header-lines 1 --overwrite --type last_name \
  --input testfiles/persons.csv_anonymized:2

# support wildcards in file paths (even recursive directories) - need quotes for wildcards to be passed to script:
./csv_anonymizer.py --header-lines 1 --overwrite --type last_name \
  --input "testfiles/**/?erson*s.csv_anonymized:2"
```

### XML

Anonymize element and attribute values in xml files. Use xpath for selection of the element/attribute to be anonymized:

``` sh
# anonymize element values in xml files:
./csv_anonymizer.py --type last_name \
  --input testfiles/addresses.xml:./person/lastname

./csv_anonymizer.py --type firat_name \
  --input testfiles/addresses.xml_anonymized:./person/firstname

# anonymize attribute value usind /@attributeName syntax:
./csv_anonymizer.py --overwrite --type number \
  --input testfiles/addresses.xml_anonymized:./person/address/@id

./csv_anonymizer.py --overwrite --type zip \
  --input testfiles/addresses.xml_anonymized:./person/address/zip
```

Use selector (filter) for elements, then choose the attribute to be anonymized:

``` sh
# do advanced xpath filtering (need single quotes for braces):
# filter on id
./csv_anonymizer.py --type number \
  --input 'testfiles/addresses.xml:./person/address[@id="123"]/@id'

# filter on name, then choose another element's attribute to be anonymized:
./csv_anonymizer.py --type number \
  --input 'testfiles/addresses.xml:.//person/lastname[text()="Riegler"]/../address/@id'  
```

#### Namespaces

``` sh
./csv_anonymizer.py --type last_name \
  --namespace adr=https://github.com/cdaller/csv_anonymizer/addressbook \
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
