# CSV Anonymizer

CSV Anonymizer: reads one or more csv files and anomyizes one column with a given type (e.g. name, number).
It is able to anonymize different columns that contain the same values from different csv files.

E.g. the account number of a bank account is used in a.csv in column 3 and in b.csv in column 4
csv_anonymizer --type=number --input a.csv:3 b.cvs:4 foobar_*.cvs:6
would anonymize the bank account number in both files in a way that bank account number 123456 is 
anonymized to a random integer - but to the same random integer in all rows in both files.

## Installation

Install faker python library and other dependencies:

```
pip3 install Faker
pip3 install glob2
```

## Examples

The testfiles directory contains some test csv files:

Anonymize the person id in all files, first and last name in persons file

``` sh
./csv_anonymizer.py --header-lines 1 \
  --input testfiles/persons.csv:0 testfiles/adresses.csv:1 

./csv_anonymizer.py --header-lines 1  --overwrite --type first_name \
  --input testfiles/persons.csv_anonymized:1

./csv_anonymizer.py --header-lines 1 --overwrite --type last_name \
  --input testfiles/persons.csv_anonymized:2

# support wildcards in file paths (even recursive directories):
./csv_anonymizer.py --header-lines 1 --overwrite --type last_name \
  --input testfiles/**/?erson*s.csv_anonymized:2

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
