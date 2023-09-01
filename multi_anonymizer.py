#!/usr/bin/env python3
"""
CSV Anonymizer: reads one or more csv files and anomyizes one column with a given type (e.g. name, number).
It is able to anonymize different columns that contain the same values from different csv files.

E.g. the account number of a bank account is used in a.csv in column 3 and in b.csv in column 4
and in all files named foobar_* in column 6:
multi_anonymizer --type=number --input a.csv:3 b.cvs:4 foobar_*.cvs:6
would anonymize the bank account number in both files in a way that bank account number 123456 is 
anonymized to a random integer - but to the same random integer in all rows in both files.

Author: Christof Dallermassl
License: Apache License 2.0
"""

import argparse
import csv
import os.path
import random
import shutil
import sys
import re
from collections import defaultdict
import time

import glob2 as glob
from faker import Factory

try:
    from lxml import etree
    xml_available = True
except ImportError:
    xml_available = False

try:
    from sqlalchemy import create_engine, select, update, MetaData, Table, bindparam
    sql_available = True
except ImportError:
    sql_available = False


def parse_args():
    parser = argparse.ArgumentParser(description='Anonymize columns of one ore more csv files', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-i', '--input', nargs='+', dest='input',
                        help="inputfile1:columnindex1 [inputfile2:columnindex2] for csv or \n"
                             "inputfile1:./xpath-selector/@attribute_name for xml\n"
                             "sqlite://[username:password@]server/database:tablename/columnname for database content\n"
                             "use multiple arguments to anonymize a value in multiple files!\n"
                             "Mixing of different types (csv, xml, ...) also works!\n"
                             "Wildcards like '*' or '?' in filenames will also work!")
    parser.add_argument('-t', '--type', dest='type', default='number',
                        help='name, first_name, last_name, email, zip, city, address, number, ... . Default is number')
    parser.add_argument('-e', '--encoding', dest='encoding', default='ISO-8859-15',
                        help='the encoding of the file to read/write. Default is ISO-8859-15')
    parser.add_argument('-d', '--delimiter', dest='delimiter', default=';',
                        help='the delimiter of the csv columns. For tab as delimiter use "--delimiter $\'\\t\'". '
                             'Default is semicolon.')
    parser.add_argument('-l', '--locale', dest='locale', default='de_DE',
                        help='the locale to use to generate fake data. Default is de_DE')
    parser.add_argument('-o', '--overwrite', dest='overwrite', action='store_true',
                        help='overwrite the original file with anonymized file')
    parser.add_argument('-j', '--ignore-missing-file', dest='ignoreMissingFile', action='store_true',
                        help='if set, missing files are ignored')
    parser.add_argument('--header-lines', dest='headerLines', default='0',
                        help='set to number of header lines in csv files to ignore, default = 0')
    parser.add_argument('--namespace', nargs='+', dest='namespace',
                        help='shortname=http://full-url-of-namespace.com add xml namespaces so they can be used in '
                             'xpath selector, sepearate with equals')
    return parser


def getRandomInt(start=0, end=1000000):
    return lambda: random.randint(start, end)


def anonymize_rows(rows, column_index):
    """
    Rows is an iterable of dictionaries that contain name and
    email fields that need to be anonymized.
    """
    # Load the faker and its providers

    # Iterate over the rows and yield anonymized rows.
    for row in rows:
        # Replace the column with faked fields if filled (trim whitespace first):

        if len(row) > column_index:
            if len(row[column_index].strip()) > 0:
                row[column_index] = FAKE_DICT[row[column_index].strip().replace('\n', '')]
        # Yield the row back to the caller
        yield row


def anonymize_csv(source_file_name, target_file_name, column_index, header_lines, encoding, delimiter) -> int:
    """
    The source argument is a path to a CSV file containing data to anonymize,
    while target is a path to write the anonymized CSV data to.
    """
    counter = 0
    with open(source_file_name, 'r', encoding=encoding, newline=None) as inputfile:
        with open(target_file_name, 'w', encoding=encoding) as outputfile:
            # Use the DictReader to easily extract fields
            reader = csv.reader(inputfile, delimiter=delimiter)
            writer = csv.writer(outputfile, delimiter=delimiter, lineterminator='\n')

            # Read and anonymize data, writing to target file.
            skip_lines = header_lines
            while skip_lines > 0:
                writer.writerow(next(reader))
                skip_lines = skip_lines - 1
            for row in anonymize_rows(reader, column_index):
                writer.writerow(row)
                counter += 1
    return counter


def anonymize_xml(source_file_name, target_file_name, selector, encoding, namespaces) -> int:
    """
    The source argument is a path to an XML file containing data to anonymize,
    while target is a path to write the anonymized data to.
    The selector is an xpath string to determine which element/attribute to anonymize.
    """

    if not xml_available:
        print('for xml processing, the library "lxml" is needed - please install with pip!')
        sys.exit(2)

    parser = etree.XMLParser(remove_blank_text=True, encoding=encoding)  # for pretty print
    tree = etree.parse(input_name, parser=parser)

    selector_parts = selector.split('/@')
    element_selector = selector_parts[0]
    attribute_name = None
    if len(selector_parts) > 1:
        attribute_name = selector_parts[1]  # /person/address/@id -> id

    counter = 0
    for element in tree.xpath(element_selector, namespaces=namespaces):
        if attribute_name is None:
            element.text = str(FAKE_DICT[element.text])
        else:
            old_value = element.attrib[attribute_name]
            new_value = str(FAKE_DICT[old_value])  # convert numbers to string
            element.attrib[attribute_name] = new_value
        counter += 1
    result = etree.tostring(tree, pretty_print=True).decode(encoding)
    with open(target_file_name, 'w', encoding=encoding) as outputfile:
        outputfile.write(result)
    return counter

def anonymize_db(connection_string, selector, encoding) -> int:

    [table_name, column_name] = selector.split('/')

    engine = create_engine(connection_string, echo = False)
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with = engine)

    counter = 0

    # Connect to the database
    with engine.connect() as connection:
        select_stmt = select(table.c[column_name])
        result = connection.execute(select_stmt)

        # Iterate over the rows and anonymize the value
        for row in result:
            original_value = row[0]
            # FIXME: handle numeric values
            anonymized_value = str(FAKE_DICT[original_value.encode()])
            
            update_stmt = (
                update(table)
                .where(table.c[column_name] == bindparam('orig_value'))
                .values({column_name: bindparam('new_value')})
            )
            connection.execute(update_stmt, [{"orig_value": original_value, "new_value": anonymized_value}])    
            counter += 1

        connection.commit()
    
    return counter

if __name__ == '__main__':
    parser = parse_args()
    ARGS = parser.parse_args()

    if ARGS.input is None:
        parser.print_help(sys.stderr)
        sys.exit(1)

    FAKER = Factory.create(ARGS.locale)

    # Create mappings of names & emails to faked names & emails.
    if ARGS.type == 'name':
        FAKE_DICT = defaultdict(FAKER.name)
    if ARGS.type == 'first_name':
        FAKE_DICT = defaultdict(FAKER.first_name)
    if ARGS.type == 'last_name':
        FAKE_DICT = defaultdict(FAKER.last_name)
    if ARGS.type == 'number':
        FAKE_DICT = defaultdict(getRandomInt())
    if ARGS.type == 'email':
        FAKE_DICT = defaultdict(FAKER.email)
    if ARGS.type == 'phone_number':
        FAKE_DICT = defaultdict(FAKER.phone_number)
    if ARGS.type == 'zip':
        FAKE_DICT = defaultdict(FAKER.postcode)
    if ARGS.type == 'postcode':
        FAKE_DICT = defaultdict(FAKER.postcode)
    if ARGS.type == 'city':
        FAKE_DICT = defaultdict(FAKER.city)
    if ARGS.type == 'street':
        FAKE_DICT = defaultdict(FAKER.street_address)
    if ARGS.type == 'street_address':
        FAKE_DICT = defaultdict(FAKER.street_address)
    if ARGS.type == 'iban':
        FAKE_DICT = defaultdict(FAKER.iban)
    if ARGS.type == 'sentence':
        FAKE_DICT = defaultdict(FAKER.sentence)
    if ARGS.type == 'word':
        FAKE_DICT = defaultdict(FAKER.word)
    if ARGS.type == 'text':
        FAKE_DICT = defaultdict(FAKER.text)
    if ARGS.type == 'date':
        FAKE_DICT = defaultdict(FAKER.date)
    if ARGS.type == 'uuid4':
        FAKE_DICT = defaultdict(FAKER.uuid4)
    # special handling for tab delimiter to allow easier passing as command line:
    if ARGS.delimiter == "\t":
        print('Detected tab as delimiter')
    #        delimiter = '\t'
    delimiter = ARGS.delimiter

    for input_source in ARGS.input:
        parts = input_source.rsplit(':', 1)
        if len(parts) < 2:
            print('Missing csv column, xpath expression or table/column name!')
            sys.exit(2)
        input_name = parts[0]
        selector = parts[1]

        source_is_database = False
        if '://' in input_name:
            source_is_database = True

        if source_is_database:
            # no wildcards in database urls!
            inputs_to_read = [input_name]
        else:
            # extend wildcards in filename:
            inputs_to_read = glob.glob(input_name)
        if len(inputs_to_read) == 0 and not ARGS.ignoreMissingFile:
            print('no input sources found: %s' % input_name)
            sys.exit(1)

        total_counter = 0
        start_time = time.process_time()

        for input in inputs_to_read:
            source = input
            target = source + '_anonymized' # fixme: allow to set the targetfilename following a pattern
            if os.path.isfile(source) or source_is_database:
                print('anonymizing file %s selector %s as type %s to file %s' %
                      (source, selector, ARGS.type, target))

                counter = 0
                # depending on selector, read csv or xml:
                if selector.isnumeric():
                    counter = anonymize_csv(source, target, int(selector), int(ARGS.headerLines), ARGS.encoding, delimiter)
                else:
                    if source_is_database:
                        counter = anonymize_db(source, selector, ARGS.encoding)
                    else:
                        namespaces = {}
                        if ARGS.namespace is not None:
                            for value in ARGS.namespace:
                                entry = value.split('=')
                                namespaces[entry[0]] = entry[1]
                        counter = anonymize_xml(source, target, selector, ARGS.encoding, namespaces)

                # move anonymized file to original file
                if ARGS.overwrite:
                    print('overwriting original file %s with anonymized file!' % source)
                    shutil.move(src=target, dst=source)

                total_counter += counter
                end_time = time.process_time()
                print(f'Anonymized {total_counter} values in {(end_time - start_time):.{2}}s')
            else:
                if ARGS.ignoreMissingFile:
                    print('ignoring missing file %s' % source)
                else:
                    print('file %s does not exist!' % source)
                    sys.exit(1)
