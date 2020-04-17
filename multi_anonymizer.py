#!/usr/bin/env python3
"""
CSV Anonymizer: reads one or more csv files and anomyizes one column with a given type (e.g. name, number).
It is able to anonymize different columns that contain the same values from different csv files.

E.g. the account number of a bank account is used in a.csv in column 3 and in b.csv in column 4
csv_anonymizer --type=number --input a.csv:3 b.cvs:4 foobar_*.cvs:6
would anonymize the bank account number in both files in a way that bank account number 123456 is 
anonymized to a random integer - but to the same random integer in all rows in both files.

Author: Christof Dallermassl
License: MIT
"""

import sys
import shutil
import os.path
import csv
import glob2 as glob
import faker
import re
from faker.providers import BaseProvider
from faker.providers import date_time

from lxml import etree

from faker import Faker
from faker import Factory
from collections import defaultdict
import argparse
import random

import string


def parseArgs():
    parser = argparse.ArgumentParser(description = 'Anonymize columns of one ore more csv files')
    parser.add_argument('-i', '--input', nargs='+', dest='input',
                        help='inputfile1:columnindex1 [inputfile2:columnindex2] for csv or inputfile1:./xpath-selector/@attribute_name for xml, use multiple arguments to replace in multiple files!')
    parser.add_argument('-t', '--type', dest='type', default='number',
                        help='name, first_name, last_name, email, zip, city, address, number, ... . Default is number')
    parser.add_argument('-e', '--encoding', dest='encoding', default='ISO-8859-15',
                        help='the encoding of the file to read/write. Default is ISO-8859-15')
    parser.add_argument('-d', '--delimiter', dest='delimiter', default=';',
                        help='the delimiter of the csv columns. For tab as delimiter use "--delimiter $\'\\t\'". Default is semicolon.')
    parser.add_argument('-l', '--locale', dest='locale', default='de_DE',
                        help='the locale to use to generate fake data. Default is de_DE')
    parser.add_argument('-o', '--overwrite', dest='overwrite', action='store_true',
                        help='overwrite the original file with anonymized file')
    parser.add_argument('-j', '--ignore-missing-file', dest='ignoreMissingFile', action='store_true',
                        help='if set, missing files are ignored')
    parser.add_argument('--header-lines', dest='headerLines', default='0',
                        help='set to number of header lines in csv files to ignore, default = 0')
    parser.add_argument('--namespace', nargs='+', dest='namespace',
                        help='shortname=http://full-url-of-namespace.com add xml namespaces so they can be used in xpath selector, sepearate with equals')
    return parser.parse_args()


if len(sys.argv) < 1:
    print('Usage: anon.py <source> [<source> ...]')
    sys.exit(1)

def getRandomInt(start=0, end=1000000):
    return lambda: random.randint(start, end)


def anonymize_rows(rows, columnIndex):
    """
    Rows is an iterable of dictionaries that contain name and
    email fields that need to be anonymized.
    """
    # Load the faker and its providers

    # Iterate over the rows and yield anonymized rows.
    for row in rows:
        # Replace the column with faked fields if filled (trim whitespace first):
        if len(row[columnIndex].strip()) > 0:
            row[columnIndex] = FAKE_DICT[row[columnIndex].strip()]
        # Yield the row back to the caller
        yield row


def anonymize_csv(source, target, columnIndex, headerLines, encoding, delimiter):
    """
    The source argument is a path to a CSV file containing data to anonymize,
    while target is a path to write the anonymized CSV data to.
    """
    with open(source, 'r', encoding=encoding, newline=None) as inputfile:
        with open(target, 'w', encoding=encoding) as outputfile:
            # Use the DictReader to easily extract fields
            reader = csv.reader(inputfile, delimiter=delimiter)
            writer = csv.writer(outputfile, delimiter=delimiter, lineterminator='\n')

            # Read and anonymize data, writing to target file.
            skipLines = headerLines
            while (skipLines > 0):
                writer.writerow(next(reader))
                skipLines = skipLines - 1
            for row in anonymize_rows(reader, columnIndex):
                writer.writerow(row)

def anonymize_xml(source, target, selector, encoding, namespaces):
    """
    The source argument is a path to an XML file containing data to anonymize,
    while target is a path to write the anonymized data to.
    The selector is an xpath string to determine which element/attribute to anonymize.
    """

    parser = etree.XMLParser(remove_blank_text = True, encoding = encoding) # for pretty print
    tree = etree.parse(filename, parser=parser)

    selector_parts = selector.split('/@')
    element_selector = selector_parts[0]
    attribute_name = None
    if len(selector_parts) > 1:
        attribute_name = selector_parts[1] # /person/address/@id -> id
    
    for element in tree.xpath(element_selector, namespaces = namespaces):
        if attribute_name is None:
            element.text = str(FAKE_DICT[element.text])
        else:
            old_value = element.attrib[attribute_name]
            new_value = str(FAKE_DICT[old_value]) # convert numbers to string
            element.attrib[attribute_name] = new_value 
    result = etree.tostring(tree, pretty_print=True).decode(encoding)
    with open(target, 'w', encoding=encoding) as outputfile:
        outputfile.write(result)

if __name__ == '__main__':
    ARGS = parseArgs()

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
    # special handling for tab delimiter to allow easier passing as command line:
    if ARGS.delimiter == "\t":
        print('Detected tab as delimiter')
#        delimiter = '\t'
    delimiter = ARGS.delimiter

    if ARGS.input is None:
        print("Inputfiles are missing!")
        sys.exit(1)
    for infile in ARGS.input:
        parts = infile.split(':', 1)
        if len(parts) < 2:
            print('Missing csv column or xpath expression!')
            sys.exit(2)
        filename = parts[0]
        selector = parts[1]
        # extend wildcards in filename:
        files_to_read = glob.glob(filename)
        if len(files_to_read) == 0 and not ARGS.ignoreMissingFile:
            print('no files found: %s' % filename)
            sys.exit(1)
        for extendedFile in files_to_read:
            source = extendedFile
            target = source + '_anonymized'
            if os.path.isfile(source):
                print('anonymizing file %s selector %s as type %s to file %s' %
                    (source, selector, ARGS.type, target))

                # depending on selector, read csv or xml:
                if selector.isnumeric():
                    anonymize_csv(source, target, int(selector), int(ARGS.headerLines), ARGS.encoding, delimiter)
                else:
                    namespaces = {}
                    if ARGS.namespace is not None:
                        for value in ARGS.namespace:
                            entry = value.split('=')
                            namespaces[entry[0]] = entry[1]
                    anonymize_xml(source, target, selector, ARGS.encoding, namespaces)

                # move anonymized file to original file
                if ARGS.overwrite:
                    print('overwriting original file %s with anonymized file!' % source)
                    shutil.move(src=target, dst=source)
            else:
                if ARGS.ignoreMissingFile:
                    print('ignoring missing file %s' % source)
                else:
                    print('file %s does not exist!' % source)
                    sys.exit(1)
    
