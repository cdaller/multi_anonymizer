#!/usr/bin/env python3

import argparse
import json
import re
import os
import logging
from faker import Faker
from jinja2 import Template
from time import perf_counter

# Lazy imports
try:
    import pandas as pd
except ImportError:
    pd = None

try:
    from jsonpath_ng import parse as json_parse
except ImportError:
    json_parse = None

try:
    from lxml import etree
except ImportError:
    etree = None

try:
    from sqlalchemy import create_engine, MetaData, Table, select, update, text, bindparam
    from sqlalchemy.orm import sessionmaker
except ImportError:
    create_engine = None


class DataAnonymizer:
    def __init__(self, db_url=None, locale="en_US", encoding="utf-8", cache_file=None):
        """Initialize the anonymizer with a database connection (if provided) and locale."""
        self.fake = Faker(locale)
        self.encoding = encoding
        self.faker_methods = self._get_faker_methods()
        self.faker_cache = {}  # Cache for consistent faker values
        self.cache_file = cache_file
        self.engine = None
        self.sql_logger = logging.getLogger('sql')
        self.json_logger = logging.getLogger('json')

        self.env_context = {"env": {key: value for key, value in os.environ.items()}}


        # Load cache file if provided
        if self.cache_file:
            self._load_cache()

    def _load_cache(self):
        """Loads the faker cache from a file if it exists."""
        if self.cache_file and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as file:
                    self.faker_cache = json.load(file)
                print(f"Loaded faker cache from '{self.cache_file}' ({sum(len(v) for v in self.faker_cache.values())} entries)")
            except Exception as e:
                print(f"⚠️ Warning: Failed to load faker cache from '{self.cache_file}': {e}")
                self.faker_cache = {}

    def _save_cache(self):
        """Saves the faker cache to a file at the end of execution."""
        if self.cache_file:
            try:
                with open(self.cache_file, "w", encoding="utf-8") as file:
                    json.dump(self.faker_cache, file, indent=4, ensure_ascii=False)
                print(f"Faker cache saved to '{self.cache_file}' ({sum(len(v) for v in self.faker_cache.values())} entries)")
            except Exception as e:
                print(f"⚠️ Warning: Failed to save faker cache to '{self.cache_file}': {e}")


    def _get_faker_methods(self):
        """Fetch all available Faker methods, filtering out internal methods."""
        faker_methods = {}
        for method in dir(self.fake):
            if not method.startswith("_"):
                try:
                    attr = getattr(self.fake, method)
                    if callable(attr):
                        faker_methods[method] = attr
                except TypeError:
                    continue
        return faker_methods
    
    def _get_consistent_faker_value(self, original_value, faker_type, **kwargs):
        """Ensures that empty or null original values return empty or null faker values,
        and that the same original value gets the same anonymized value across all sources.
        """
        if original_value is None:
            return None  # Keep None values as None

        if isinstance(original_value, str) and original_value.strip() == "":
            return ""  # Keep empty strings as empty

        if faker_type not in self.faker_cache:
            self.faker_cache[faker_type] = {}

        if original_value in self.faker_cache[faker_type]:
            return self.faker_cache[faker_type][original_value]

        # Handle number anonymization with min/max
        if faker_type == "number":
            min_val = kwargs.get("min", 0)
            max_val = kwargs.get("max", 100)
            anonymized_value = self.fake.random_int(min=min_val, max=max_val)
        elif faker_type == "zip_city":
            min_val = kwargs.get("min", 0)
            max_val = kwargs.get("max", 100)
            anonymized_value = self.fake.random_int(min=min_val, max=max_val)
        elif faker_type in self.faker_methods:
            anonymized_value = self.faker_methods[faker_type](**kwargs)
        else:
            anonymized_value = f"INVALID_FAKER_METHOD({faker_type})"

        self.faker_cache[faker_type][original_value] = anonymized_value
        return anonymized_value

    
    def faker_proxy(self):
        """Return a dictionary of Faker functions that can be used in Jinja2 templates."""
        return {method: (lambda *args, m=method, **kwargs: self.faker_methods[m](*args, **kwargs)) for method in self.faker_methods}

    def anonymize_value(self, originial_value, faker_or_template, context={}):
        if isinstance(faker_or_template, dict) and "type" in faker_or_template:
            anonymized_value = self._get_consistent_faker_value(originial_value, faker_or_template["type"], **faker_or_template.get("params", {}))
        elif faker_or_template in self.faker_methods:
            anonymized_value = self._get_consistent_faker_value(originial_value, faker_or_template)
        else:
            template = Template(faker_or_template)
            # print(f" original_value: {originial_value}, faker_or_template: {faker_or_template}, rows: {context}")
            # add utils that handle null values better than jinja2 methods
            anonymized_value = template.render(faker=self.faker_proxy(), row=context, re=re, str=str, int=int, len=len, **self.env_context)
            if anonymized_value == "None":
                anonymized_value = None
        return anonymized_value

    def eval_template_with_environment(self, template):
        """Evaluates a Jinja2 template with environment variables."""
        return self.eval_template(template, context=self.env_context)

    def eval_template(self, template, context={}):
        """Evaluates a Jinja2 template with the provided context."""
        return Template(template).render(**context)

    def anonymize_csv(self, file_path, columns_to_anonymize, overwrite=False, separator=","):
        """Anonymizes a CSV file using Faker and Jinja2 templates."""
        if not pd:
            print("Pandas is required for CSV anonymization. Install it with 'pip install pandas'.")
            return

        df = pd.read_csv(file_path, sep=separator, encoding=self.encoding)

        for col, faker_or_template in columns_to_anonymize.items():
            if col in df.columns:
                df[col] = df.apply(lambda row: self.anonymize_value(row[col], faker_or_template, row.to_dict()), axis=1)

        output_file = file_path if overwrite else file_path.replace(".csv", "_anonymized.csv")
        df.to_csv(output_file, sep=separator, index=False, encoding=self.encoding)
        print(f"CSV file '{file_path}' anonymized {len(df)} rows. {'Overwritten' if overwrite else f'Saved as {output_file}'}.")


    def anonymize_json_string(self, json_string, json_paths):
        """Anonymizes a JSON string using JSONPath."""
        if not json_parse:
            print("jsonpath-ng is required for JSON anonymization. Install it with 'pip install jsonpath-ng'.")
            return json_string

        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON configuration: {e} in \n{json_string}")
            exit(1)

        count = 0
        for json_path, faker_or_template in json_paths.items():
            json_expr = json_parse(json_path)
            matches = json_expr.find(data)
            if len(matches) == 0:
                self.json_logger.info(f"JSONPath '{json_path}' not found in JSON data - skipping.")
                self.json_logger.debug(f"in json string: {json_string}")
            for match in matches:
                originial_value = match.value
                anonymized_value = self.anonymize_value(originial_value, faker_or_template)                    
                match.full_path.update(data, anonymized_value)
                count += 1

        return (count, json.dumps(data, ensure_ascii=False, indent=4))  # Return anonymized JSON string


    def anonymize_json_file(self, file_path, json_paths, overwrite=False):
        """Anonymizes a JSON file using JSONPath."""
        if not json_parse:
            print("jsonpath-ng is required for JSON anonymization. Install it with 'pip install jsonpath-ng'.")
            return

        with open(file_path, 'r', encoding=self.encoding) as file:
            json_string = file.read()

        (count, anonymized_json) = self.anonymize_json_string(json_string, json_paths)

        output_file = file_path if overwrite else file_path.replace(".json", "_anonymized.json")
        with open(output_file, 'w', encoding=self.encoding) as file:
            file.write(anonymized_json)

        print(f"JSON file '{file_path}' anonymized {count} elements. {'Overwritten' if overwrite else f'Saved as {output_file}'}.")
    

    def anonymize_xml_string(self, xml_string, xml_paths):
        """Anonymizes an XML string using XPath."""
        if not etree:
            print("lxml is required for XML anonymization. Install it with 'pip install lxml'.")
            return xml_string

        try:
            xml_tree = etree.fromstring(xml_string)
        except etree.XMLSyntaxError:
            print(f"Invalid XML!")
            return xml_string  # Return unchanged if invalid XML

        count = 0
        for xpath, faker_or_template in xml_paths.items():
            if "@" in xpath:  # If XPath targets an attribute (e.g., //address/@id)
                attr_xpath, attr_name = xpath.rsplit("/@", 1)
                for elem in xml_tree.xpath(attr_xpath):
                    if elem.get(attr_name) is not None:
                        originial_value = elem.get(attr_name)
                        anonymized_value = self.anonymize_value(originial_value, faker_or_template)
                        elem.set(attr_name, str(anonymized_value))  # Update the attribute value
                        count += 1

            else:  # Normal text element anonymization
                for elem in xml_tree.xpath(xpath):
                    originial_value = elem.text
                    anonymized_value = self.anonymize_value(originial_value, faker_or_template)
                    elem.text = str(anonymized_value)  # Update the element text
                    count += 1

        return (count, etree.tostring(xml_tree, encoding=self.encoding).decode())  # Return anonymized XML string

    def anonymize_xml_file(self, file_path, xml_paths, overwrite=False):
        """Anonymizes an XML file using XPath for both element text and attributes."""
        if not etree:
            print("lxml is required for XML anonymization. Install it with 'pip install lxml'.")
            return

        with open(file_path, 'r', encoding=self.encoding) as file:
            xml_string = file.read()

        (count, anonymized_xml) = self.anonymize_xml_string(xml_string, xml_paths)

        output_file = file_path if overwrite else file_path.replace(".xml", "_anonymized.xml")
        with open(output_file, 'w', encoding=self.encoding) as file:
            file.write(anonymized_xml)

        print(f"XML file '{file_path}' anonymized {count} elements. {'Overwritten' if overwrite else f'Saved as {output_file}'}.")

    def parse_sqlalchemy_joins(self, engine, metadata, table_alias, join_definitions):
        """Parses join definitions from CLI into SQLAlchemy joins."""
        join_tables = {}
        join_conditions = []

        for join_def in join_definitions:
            try:
                table_name, alias, on_clause = join_def.split(" ", 2)  # Split into parts
                if "." in table_name:  # Handle schema.table format
                    schema_name, table_name = table_name.split(".", 1)
                else:
                    schema_name = None
                on_clause = on_clause.replace("ON ", "").strip()  # Remove "ON" prefix

                #print(f"Joining {table_alias} with {schema_name + '.' or ''}{table_name} alias '{alias}' ON '{on_clause}'")

                join_table = Table(table_name, metadata, schema=schema_name, autoload_with=engine).alias(alias)
                join_tables[alias] = join_table
                join_conditions.append((alias, join_table, on_clause))
            except ValueError as e:
                raise ValueError(f"Invalid join format: {join_def}. Expected format: '<table/view> <alias> ON <condition>': {str(e)}")

        return join_conditions
    
    def add_where_clause(self, query, where_clause):
        if where_clause:
            query = query.where(text(where_clause))
        return query
    
    def add_joins(self, query, join_conditions):
        for alias, join_table, on_clause in join_conditions:
            print(f"Joining {join_table} {alias} with {join_table} ON {on_clause}")
            query = query.join(join_table, text(on_clause))
        return query

    def anonymize_db_table(self, db_url, table_schema, table_name, id_columns, where_clause, joins, columns_to_anonymize, json_columns=None, xml_columns=None):
        """Anonymizes a database table, including JSON and XML inside table columns."""
        table_full_name = f"{table_schema}.{table_name}" if table_schema else table_name
        print(f"Anonymizing table '{table_full_name}'...", flush=True, end="")

        if not create_engine:
            print("SQLAlchemy is required for database anonymization. Install it with 'pip install sqlalchemy'.")
            return
        
        print(f" connecting...", end="", flush=True)
        start_time = perf_counter()
        engine = create_engine(db_url)
        metadata = MetaData()
        # no need to load whole database table definitions! metadata.reflect(bind=engine)
                
        table = Table(table_name, metadata, autoload_with=engine, schema=table_schema)
        if len(joins) > 0:
            # some sql servers do not support alias names on updates! So use them only if necessary (when using joins)
            table = table.alias('target_table')

        Session = sessionmaker(bind=engine)
        with Session() as session:

            # Parse and apply JOINs if provided
            join_conditions = self.parse_sqlalchemy_joins(engine, metadata, "target_table", joins)

            count = 0
            if id_columns:
                # workaround for sql servers that do not support alias names in update statements (and as id column is used, it is not needed for update statement!)
                update_table = Table(table_name, metadata, autoload_with=engine, schema=table_schema)
                count = self.anonymize_db_with_id_column(session, table, update_table, id_columns, where_clause, join_conditions, columns_to_anonymize, json_columns, xml_columns)
            else:
                count = self.anonymize_db_without_id_column(session, table, where_clause, join_conditions, columns_to_anonymize)

            session.commit()

        duration = perf_counter() - start_time
        print(f" DONE - anonymized {count} rows/values successfully in {duration:.2f} seconds")

    def extract_column_names_from_template(self, template):
        # Regular expression to extract keys inside row["..."] within Jinja2 curly braces
        pattern = r'\{\{[^}]*?row\[(?:\"|\')(.+?)(?:\"|\')\][^}]*?\}\}'

        # Find all matches
        matches = re.findall(pattern, template)
        return matches

    def anonymize_db_with_id_column(self, session, table, update_table, id_columns, where_clause, join_conditions, columns_to_anonymize, json_columns=None, xml_columns=None):
        # which columns to load:
        columns_to_load = set(id_columns)
        columns_to_load.update(json_columns.keys() if json_columns else [])
        columns_to_load.update(xml_columns.keys() if json_columns else [])
        for col, faker_or_template in columns_to_anonymize.items():
            columns_to_load.add(col)
            if isinstance(faker_or_template, str):
                columns_to_load.update(self.extract_column_names_from_template(faker_or_template))

        # Check if all columns to load are valid columns of the table
        table_columns = set(table.columns.keys())
        invalid_columns = columns_to_load - table_columns
        if invalid_columns:
            raise ValueError(f"Invalid columns specified: {', '.join(invalid_columns)}")
                
        query = select(table)
        query = query.with_only_columns(*[table.c[col] for col in columns_to_load])

        query = self.add_joins(query, join_conditions)

        query = self.add_where_clause(query, where_clause)
        self.sql_logger.debug(f"Executing query: {query}")
        rows = session.execute(query).fetchall()

        count_result = {}

        row_count = 0
        count_json = 0
        count_xml = 0
        print(f" processing {len(rows)} rows ..", end="", flush=True)
        for row in rows:
            row_dict = row._asdict()
            anonymized_values = {}

            # Standard column anonymization
            for col, faker_or_template in columns_to_anonymize.items():
                if col in row_dict:
                    original_value = row_dict[col]
                    # merge original row and already changed values - use this as a template context
                    context = {**row_dict, **anonymized_values}
                    anonymized_value = self.anonymize_value(original_value, faker_or_template, context)
                    anonymized_values[col] = anonymized_value

            # JSON Column Anonymization
            if json_columns:
                for col, json_paths in json_columns.items():
                    if col in row_dict and isinstance(row_dict[col], str):  # Ensure it's a valid JSON string
                        self.json_logger.debug(f"Working on json in row { {id_col: row_dict.get(id_col) for id_col in id_columns} }")
                        (count, anonymized_json) = self.anonymize_json_string(row_dict[col], json_paths)
                        anonymized_values[col] = anonymized_json
                        count_json += count

            # XML Column Anonymization
            if xml_columns:
                for col, xml_paths in xml_columns.items():
                    if col in row_dict and isinstance(row_dict[col], str):  # Ensure it's a valid XML string
                        (count, anonymized_xml) = self.anonymize_xml_string(row_dict[col], xml_paths)
                        anonymized_values[col] = anonymized_xml
                        count_xml += count

            if anonymized_values:
                id_conditions = [update_table.c[id_col] == row_dict[id_col] for id_col in id_columns]
                update_stmt = update(update_table).where(*id_conditions).values(**anonymized_values)
                #self.sql_logger.debug(f"Executing update: {update_stmt}")
                session.execute(update_stmt)
            
            row_count += 1
            percent = int((row_count / len(rows)) * 100)
            if row_count == len(rows) or (percent % 5 == 0 and percent != int(((row_count - 1) / len(rows)) * 100)):
                print(f"{percent}%..", end="", flush=True)

        print(f" {row_count} rows ", end="", flush=True)
        count_result['rows'] = row_count
        if count_json > 0:
            count_result['json_values'] = count_json
        if count_xml > 0:
            count_result['xml_values'] = count_xml 
        return count_result


    def anonymize_db_without_id_column(self, session, table, where_clause, join_conditions, columns_to_anonymize):
        count = 0
        for column_name, faker_or_template in columns_to_anonymize.items():
            column = getattr(table.c, column_name)
            query = select(column).distinct()

            query = self.add_where_clause(query, where_clause)

            # Select all distinct values in the column
            distinct_values = session.execute(query).scalars().all()
            anonymized_map = {}
            for original_value in distinct_values:
                anonymized_value = self.anonymize_value(original_value, faker_or_template)
                anonymized_map[original_value] = anonymized_value

            # Update table with anonymized values
            for original_value, anonymized_value in anonymized_map.items():
                update_stmt = (
                        update(table)
                        .where(table.c[column_name] == bindparam('orig_value'))
                        .values({column_name: bindparam('new_value')})
                    )
                update_stmt = self.add_where_clause(update_stmt, where_clause)
                self.sql_logger.debug(f"Executing update: {update_stmt}")

                result = session.execute(update_stmt, [{"orig_value": original_value, "new_value": anonymized_value}])
                count += result.rowcount
                #print(f'replaced {column_name}: {original_value} with {anonymized_value}')

            # TODO: add xml/json??? Does not make sense without id column???

        return { "rows": count }


    def list_faker_methods(self, with_example_values=True):
        """Print all available Faker methods and exit."""
        print("Available Faker methods:")
        for method in sorted(self.faker_methods.keys()):
            if with_example_values:
                try:
                    example_value = self.faker_methods[method]() if method not in ["binary", "get_providers", "image", "items", "tar", "xml", "zip"] and not method.startswith("py") else "<skipped>"
                except TypeError:
                    example_value = "N/A"
                print(f"- {method}: {example_value}")
            else:
                print(f"- {method}")
        exit(0)

    def process_config(self, config, anonymizer):

        if "enabled" in config and not config["enabled"]:
            print("Config disabled. Skipping...")
            return

        if "file" in config:
            print(f"Anonymizing file '{config['file']}'...")
            if config["file"].endswith(".json"):
                anonymizer.anonymize_json_file(config["file"], config["columns"], config.get("overwrite", False))
            elif config["file"].endswith(".xml"):
                anonymizer.anonymize_xml_file(config["file"], config["columns"], config.get("overwrite", False))
            elif config["file"].endswith(".csv"):
                anonymizer.anonymize_csv(config["file"], config["columns"], config.get("overwrite", False), config.get("separator", ","))
            else:
                print("Could not detect file type from the name. Supports *.csv, *.json and *.xml files!")
                exit(-2)            
        elif "table" in config or "tables" in config:
            if 'db_url' not in config:
                print("Database anonymization needs 'db_url' set!")
                exit(-1)

            id_columns = config.get("id_columns", [])
            if "id_column" in config:
                id_columns.append(config["id_column"])

            table_joins = config.get("joins", [])
            if "join" in config:
                table_joins.append(config["join"])

            table_list = config.get("tables", [])
            if "table" in config:
                table_list.append(config["table"])

            # handle jinja2 templates in parameters:
            db_url = anonymizer.eval_template_with_environment(config["db_url"])
            where_clause = config.get("where", None)
            if where_clause:
                where_clause = anonymizer.eval_template_with_environment(where_clause)
            schema = config.get("schema", None)
            if schema:
                schema = anonymizer.eval_template_with_environment(schema)

            for table in table_list:
                anonymizer.anonymize_db_table(
                    db_url,
                    schema, 
                    table, 
                    id_columns, 
                    where_clause, 
                    table_joins, 
                    config.get("columns", {}),
                    config.get("json_columns", {}),
                    config.get("xml_columns", {}),
                )
        
        # Save the faker cache at the end
        anonymizer._save_cache()



def main():
    logging.basicConfig() # initializiation needed!!!!

    parser = argparse.ArgumentParser(
        description="Anonymize CSV, JSON, XML files, and database tables using Faker and Jinja2 templates.",
        epilog="""
Examples:

1. CSV file anonymization:
   python anonymizer.py --config '{"file": "testfiles/persons.csv", "columns": {"firstname": "first_name", "lastname": "last_name", "email": "{{ row['firstname'].lower() }}.{{ row['lastname'].lower() }}@example.com" }, "overwrite": false, "separator": ";" }'

2. JSON file anonymization:
   python anonymizer.py --config '{"file": "testfiles/persons.json", "columns": {"$.addressbook.person[*].firstname": "first_name", "$.addressbook.person[*].lastname": "last_name"}}'

3. XML file anonymization:
   python anonymizer.py --config '{"file": "testfiles/persons.xml", "columns": {"//person/firstname": "first_name", "//person/lastname": "last_name"}}'

4. Database table anonymization:
   python anonymizer.py --config '{"db_url": "sqlite:///test.db", "table": "persons", "id_column": "id", "columns": {"firstname": "first_name", "lastname": "last_name", "email": "{{ row['firstname'].lower() }}.{{ row['lastname'].lower() }}@example.com" }, "json_columns": {"json_data": {"$.person.email": "email"}}}'
   python anonymizer.py --config '{"db_url": "sqlite:///test.db", "table": "persons", "id_columns": ["id", "foobar"], "columns": {"firstname": "first_name", "lastname": "last_name", "email": "{{ row['firstname'].lower() }}.{{ row['lastname'].lower() }}@example.com" }, "json_columns": {"json_data": {"$.person.email": "email"}}}'

5. List all available Faker methods:
   python anonymizer.py --list-faker-methods

For further details and examples, see the readme.md file!
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--config", nargs="+", help="JSON configurations as command-line arguments.")
    parser.add_argument("--config-file", nargs="+", help="Paths to JSON configuration files.")
    parser.add_argument("--locale", type=str, default="en_US", help="Set Faker's locale (default: en_US)")
    parser.add_argument("--encoding", type=str, default="utf-8", help="Set file/database encoding (default: utf-8)")
    parser.add_argument("--list-faker-methods", action="store_true", help="List all available Faker methods and exit.")
    parser.add_argument("--list-faker-methods-and-examples", action="store_true", help="List all available Faker methods including example values and exit.")
    parser.add_argument('--debug-sql', dest='debug_sql', default = False, action='store_true', help='If enabled, prints sql statements. (default: %(default)d)')
    parser.add_argument('--debug-json', dest='debug_json', default = False, action='store_true', help='If enabled, prints json infos. (default: %(default)d)')
    parser.add_argument("--cache-file", type=str, help="Set a file to store and reuse Faker anonymized values.")

    args = parser.parse_args()

    anonymizer = DataAnonymizer(locale=args.locale, encoding=args.encoding, cache_file=args.cache_file)

    if args.list_faker_methods or args.list_faker_methods_and_examples:
        anonymizer.list_faker_methods(args.list_faker_methods_and_examples)

    if not args.config and not args.config_file:
        print("No configuration provided. Use --config/--configfile, or --list-faker-methods/--list-faker-methods-and-examples.")
        return

    if args.debug_sql:
        anonymizer.sql_logger.setLevel(logging.DEBUG)
    if args.debug_json:
        anonymizer.json_logger.setLevel(logging.DEBUG)
        
    try:
        # test all configs
        all_configs = args.config if args.config else []
        if args.config_file:
            for config_file in args.config_file:
                try:
                    with open(config_file, 'r', encoding=args.encoding) as file:
                        all_configs.append(file.read())
                except FileNotFoundError as e:
                    print(f"Error reading configuration file: {e}")
                    exit(1)

        for config_str in all_configs:
            try:
                config = json.loads(config_str)
                if isinstance(config, list):
                    for single_config in config:
                        anonymizer.process_config(single_config, anonymizer)
                else:
                    anonymizer.process_config(config, anonymizer)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON configuration: {e} in \n{config_str}")
                exit(1)

    except KeyboardInterrupt:
        print("\nProcess interrupted. Exiting gracefully.")
        exit(0)
    except Exception as e:
        print(f"An error occurred: {e}")
        exit(1)


if __name__ == "__main__":
    main()
