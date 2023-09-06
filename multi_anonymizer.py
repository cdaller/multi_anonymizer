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

from typing import List, Dict

import argparse
import csv
import os.path
import random
import shutil
import sys
import re
from collections import defaultdict
import time
# from unidecode import unidecode

import glob2 as glob
from jinja2 import Environment
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



FAKER_DICTS = {}


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

class Selector:
    def __init__(self, input_string, legacy_data_type = None):
        self.data_type = legacy_data_type
        self.input_type = None
        self.table = None
        self.column = None
        self.xpath = None
        self.template = '{{__value__}}'
        self.min = 0
        self.max = 1000000
        self.parse_and_set(input_string, legacy_data_type)
    
    def __str__(self):
        base_string = f"Selector[data_type='{self.data_type}', input_type='{self.input_type}', "
        if self.input_type == 'csv':
            base_string = base_string + f"column='{self.column}'"
        elif self.input_type == 'xml':
            base_string = base_string + f"xpath='{self.xpath}'"
        elif self.input_type == 'db':
            base_string = base_string + f"table='{self.table}', column='{self.column}'"
        else:
            base_string = base_string + f"table='{self.table}', column='{self.column}', xpath='{self.xpath}'"
        if self.template is not None:
            base_string = base_string + f", template='{self.template}'"
        return base_string + ']'

    def parse_and_set(self, input_string, legacy_data_type = None):
        if input_string.startswith('(') and not input_string.endswith(')'):
            print(f"Selector string is not correctly put in brackets: '{input_string}'")
            sys.exit(4)

        if input_string.startswith('(') and input_string.endswith(')'):
            input_parts = input_string.strip("()").split(',')

            attributes = {}
            for part in input_parts:
                key, value = part.strip().split('=')
                attributes[key] = value

            self.data_type = attributes.get('type', self.data_type)
            self.table = attributes.get('table', self.table)
            self.column = attributes.get('column', self.column)
            self.xpath = attributes.get('xpath', self.xpath)
            self.input_type = attributes.get('input-type', self.input_type)
            self.template = attributes.get('template', self.template)
            self.min = int(attributes.get('min', self.min))
            self.max = int(attributes.get('max', self.max))

        else:
            # legacy parameter setting:
            if input_string.isnumeric():
                self.input_type = 'csv'
                self.column = input_string
            else:
                self.input_type = 'xml'
                self.xpath = input_string

class Source:
    def __init__(self, name, sub_source):
        self.name = name
        self.sub_source = sub_source
    
    def __hash__(self):
        return hash((self.name, self.sub_source))
    
    def __eq__(self, other):
        return (self.name, self.sub_source) == (other.name, other.sub_source)

    def __str__(self):
        return f"Source: {self.name}, Sub Source: {self.sub_source}"


def get_fake_dict(selector: Selector):
    global FAKER_DICTS

    fake_dict = FAKER_DICTS.get(selector.data_type, None)
    if fake_dict is None:
        fake_dict = create_faker_dict(selector)
        FAKER_DICTS[selector.data_type] = fake_dict
    return fake_dict
    
def anonymize_value(selector: Selector, original_value, context: Dict[str, str] = {}):
    anonymized_value = get_fake_dict(selector)[original_value]
    
    jinja_template = template_env.from_string(selector.template)
    context['__value__'] = anonymized_value
    context['__original_value__'] = original_value
    if selector.column is not None:
        if selector.column.isnumeric():
            context["col_" + selector.column] = anonymized_value
        else:
            context[selector.column] = anonymized_value
    if selector.xpath is not None:
        context[selector.xpath] = anonymized_value    

    return jinja_template.render(context)


def getRandomInt(start: int = 0, end: int = 1000000):
    return lambda: random.randint(start, end)


def anonymize_rows(rows, selectors: List[Selector]):
    """
    Rows is an iterable of dictionaries that contain name and
    email fields that need to be anonymized.
    """

    # Iterate over the rows and yield anonymized rows.
    for row in rows:
        context = {}
        for selector in selectors:

            if selector.column is None:
                print(f'No column given in selector {selector}')
                sys.exit(3)

            column_index = int(selector.column)
            # Replace the column with faked fields if filled (trim whitespace first):
            if column_index < len(row):
                if len(row[column_index].strip()) > 0:
                    original_value = row[column_index].strip().replace('\n', '')
                    anonymized_value = anonymize_value(selector, original_value, context)
                    row[column_index] = anonymized_value
        # Yield the row back to the caller
        yield row


def anonymize_csv(source_file_name, target_file_name, selectors: List[Selector], header_lines, encoding, delimiter) -> int:
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
            for row in anonymize_rows(reader, selectors):
                writer.writerow(row)
                counter += 1
    return counter


def anonymize_xml(source_file_name, target_file_name, selectors: List[Selector], encoding, namespaces) -> int:
    """
    The source argument is a path to an XML file containing data to anonymize,
    while target is a path to write the anonymized data to.
    The selector holds an xpath string to determine which element/attribute to anonymize.
    """

    if not xml_available:
        print('for xml processing, the library "lxml" is needed - please install with pip!')
        sys.exit(2)

    parser = etree.XMLParser(remove_blank_text=True, encoding=encoding)  # for pretty print
    tree = etree.parse(input_name, parser=parser)

    counter = 0
    context = {}
    for selector in selectors:

        if selector.xpath is None:
            print(f'No xpath given in selector {selector}')
            sys.exit(3)

        selector_parts = selector.xpath.split('/@')
        element_selector = selector_parts[0]
        attribute_name = None
        if len(selector_parts) > 1:
            attribute_name = selector_parts[1]  # /person/address/@id -> id

        for element in tree.xpath(element_selector, namespaces=namespaces):
            if attribute_name is None:
                element.text = str(anonymize_value(selector, element.text, context))
            else:
                original_value = element.attrib[attribute_name]
                anonymized_value = str(anonymize_value(selector, original_value, context))  # convert numbers to string
                element.attrib[attribute_name] = anonymized_value
            counter += 1

    result = etree.tostring(tree, pretty_print=True).decode(encoding)
    with open(target_file_name, 'w', encoding=encoding) as outputfile:
        outputfile.write(result)
    return counter

def anonymize_db(connection_string, selector: List[Selector], encoding) -> int:

    if not sql_available:
        print('for database processing, the library "sqlalchemy" (and possible some drivers) are needed - please install with pip!')
        sys.exit(2)

    engine = create_engine(connection_string, echo = False)

    counter = 0

    # Connect to the database
    with engine.connect() as connection:

        # all selectors operate on the same table
        metadata = MetaData()
        table = Table(selectors[0].table, metadata, autoload_with = engine)

        columns_to_select = []
        for selector in selectors:

            if selector.table is None:
                print(f'No table given in selector {selector}')
                sys.exit(3)

            columns_to_select.append(selector.column)

        # Convert column names to actual table columns
        selected_columns = [getattr(table.c, col_name) for col_name in columns_to_select]

        select_stmt = select(*selected_columns)
        result = connection.execute(select_stmt)

        # Iterate over the rows and anonymize the value
        for row in result:
            context = {}
            for selector in selectors:
                original_value = row._mapping[selector.column]
                if original_value != None:
                    anonymized_value = str(anonymize_value(selector, original_value, context))
                    
                    update_stmt = (
                        update(table)
                        .where(table.c[selector.column] == bindparam('orig_value'))
                        .values({selector.column: bindparam('new_value')})
                    )
                    connection.execute(update_stmt, [{"orig_value": original_value, "new_value": anonymized_value}])    
                    print(f'replacing {selector.column}: {original_value} with {anonymized_value}')
                    counter += 1

        connection.commit()
    
    return counter


def create_faker_dict(selector: Selector) -> {}:
    # Create mappings of names & emails to faked names & emails.
    data_type = selector.data_type
    if data_type == 'name':
        fake_dict = defaultdict(FAKER.name)
    if data_type == 'first_name':
        fake_dict = defaultdict(FAKER.first_name)
    if data_type == 'last_name':
        fake_dict = defaultdict(FAKER.last_name)
    if data_type.startswith('number'):
        fake_dict = defaultdict(getRandomInt(selector.min, selector.max))
    if data_type == 'email':
        fake_dict = defaultdict(FAKER.email)
    if data_type == 'phone_number':
        fake_dict = defaultdict(FAKER.phone_number)
    if data_type == 'zip':
        fake_dict = defaultdict(FAKER.postcode)
    if data_type == 'postcode':
        fake_dict = defaultdict(FAKER.postcode)
    if data_type == 'city':
        fake_dict = defaultdict(FAKER.city)
    if data_type == 'street':
        fake_dict = defaultdict(FAKER.street_address)
    if data_type == 'street_address':
        fake_dict = defaultdict(FAKER.street_address)
    if data_type == 'iban':
        fake_dict = defaultdict(FAKER.iban)
    if data_type == 'sentence':
        fake_dict = defaultdict(FAKER.sentence)
    if data_type == 'word':
        fake_dict = defaultdict(FAKER.word)
    if data_type == 'text':
        fake_dict = defaultdict(FAKER.text)
    if data_type == 'date':
        fake_dict = defaultdict(FAKER.date)
    if data_type == 'uuid4':
        fake_dict = defaultdict(FAKER.uuid4)
    if data_type == 'company':
        fake_dict = defaultdict(FAKER.company)

    return fake_dict

def find_rightmost_colon(input_string):
    # Use a negative lookbehind assertion to exclude '::'
    pattern = r'(?<!:):(?!:)'
    
    matches = re.finditer(pattern, input_string)
    positions = [match.start() for match in matches]
    
    if positions:
        return max(positions)
    else:
        return None

def print_selector_map(map):
    for key in map.keys():
        selectors = map[key]
        print(f"input '{key}':")
        for sel in selectors:
            print(f'  selector: {sel}')


# Define the custom filter
def unidecode_filter(text):
#    return unidecode(string)
    # unidecode for the poor:
    replacements = {
            'ä': 'ae',
            'ö': 'oe',
            'ü': 'ue',
            'Ä': 'Ae',
            'Ö': 'Oe',
            'Ü': 'Ue',
            'ß': 'ss'
        }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


if __name__ == '__main__':
    parser = parse_args()
    ARGS = parser.parse_args()

    if ARGS.input is None:
        parser.print_help(sys.stderr)
        sys.exit(1)

    # Set up Jinja2 environment and add the filter
    template_env = Environment()  # Assuming your templates are in a 'templates' directory
    template_env.filters['unidecode'] = unidecode_filter


    FAKER = Factory.create(ARGS.locale)

    # special handling for tab delimiter to allow easier passing as command line:
    if ARGS.delimiter == "\t":
        print('Detected tab as delimiter')
    #        delimiter = '\t'
    delimiter = ARGS.delimiter

    source_selector_map = {}

    for input_source in ARGS.input:
        # split file name and selector by the right most colon (allow escaping of colons in selector by using double colons):
        split_index = find_rightmost_colon(input_source)
        if split_index is None:
            print('Syntax error: no colon found as separator between input source and selector!')
            sys.exit(2)
        input_name = input_source[:split_index]
        selector_string = input_source[split_index+1:]
        selector_string = selector_string.replace('::', ':')

        # FIXME: remove source_is_database?? read from selector
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

        for source_name in inputs_to_read:

            selector = Selector(selector_string, ARGS.type)
            if selector.input_type is None:
                if source_name.endswith('.csv'): 
                    selector.input_type = 'csv'
                if source_name.endswith('.xml'):
                    selector.input_type = 'xml'
                if '://' in source_name:
                    selector.input_type = 'db'

            # collect all collectors for a given source:
            source = Source(source_name, None)
            # database sources are only one source, if the operate on the same table:
            if (selector.input_type == "db"):
                source.sub_source = selector.table

            if source not in source_selector_map.keys():
                source_selector_map[source] = []

            source_selector_map[source].append(selector)

    # now process all files and apply all selectors to each value to anonymize:
    print('All anonymizations:')
    print_selector_map(source_selector_map)

    for source in source_selector_map.keys():
        selectors = source_selector_map[source]

        print(f"Processing '{source.name}' with the selectors:")
        for selector in selectors:
            print(f'  {selector}')

        counter = 0
        # database handling:
        if source_is_database:
            counter = anonymize_db(source.name, selectors, ARGS.encoding)

        # file handling:
        else:
            target = source.name + '_anonymized' # fixme: allow to set the targetfilename following a pattern
            if os.path.isfile(source.name) or source_is_database:
                print('anonymizing file %s selector %s to file %s' %
                    (source.name, selector, target))

                # depending on selector, read csv or xml:
                if selector.input_type == 'csv':
                    counter = anonymize_csv(source.name, target, selectors, int(ARGS.headerLines), ARGS.encoding, delimiter)
                else:
                    namespaces = {}
                    if ARGS.namespace is not None:
                        for value in ARGS.namespace:
                            entry = value.split('=')
                            namespaces[entry[0]] = entry[1]
                    counter = anonymize_xml(source.name, target, selectors, ARGS.encoding, namespaces)

                # move anonymized file to original file
                if ARGS.overwrite:
                    print('overwriting original file %s with anonymized file!' % source.name)
                    shutil.move(src=target, dst=source.name)

            else:
                if ARGS.ignoreMissingFile:
                    print('ignoring missing file %s' % source.name)
                else:
                    print('file %s does not exist!' % source.name)
                    sys.exit(1)

        total_counter += counter
        end_time = time.process_time()
        print(f'Anonymized {total_counter} values in {(end_time - start_time):.{2}}s')

