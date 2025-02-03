#!/usr/bin/env python3

import argparse
import json
from faker import Faker
from jinja2 import Template

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
    from sqlalchemy import create_engine, MetaData, Table, select, update
    from sqlalchemy.orm import sessionmaker
except ImportError:
    create_engine = None


class DataAnonymizer:
    def __init__(self, db_url=None, locale="en_US", encoding="utf-8"):
        """Initialize the anonymizer with a database connection (if provided) and locale."""
        self.fake = Faker(locale)
        self.encoding = encoding
        self.faker_methods = self._get_faker_methods()
        self.faker_cache = {}  # Cache for consistent faker values
        self.engine = None

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

        if original_value.strip() == "":
            return ""  # Keep empty strings as empty

        if faker_type not in self.faker_cache:
            self.faker_cache[faker_type] = {}

        if original_value in self.faker_cache[faker_type]:
            return self.faker_cache[faker_type][original_value]

        # Handle number anonymization with min/max
        if faker_type == "number":
            min_val = kwargs.get("min", 0)
            max_val = kwargs.get("max", 100)
            new_value = self.fake.random_int(min=min_val, max=max_val)
        elif faker_type in self.faker_methods:
            new_value = self.faker_methods[faker_type](**kwargs)
        else:
            new_value = f"INVALID_FAKER_METHOD({faker_type})"

        self.faker_cache[faker_type][original_value] = new_value
        return new_value

    
    def faker_proxy(self):
        """Return a dictionary of Faker functions that can be used in Jinja2 templates."""
        return {method: (lambda m=method: self.faker_methods[m]()) for method in self.faker_methods}


    def anonymize_csv(self, file_path, columns_to_anonymize, overwrite=False, separator=","):
        """Anonymizes a CSV file using Faker and Jinja2 templates."""
        if not pd:
            print("Pandas is required for CSV anonymization. Install it with 'pip install pandas'.")
            return

        df = pd.read_csv(file_path, sep=separator, encoding=self.encoding)

        for col, faker_or_template in columns_to_anonymize.items():
            if col in df.columns:
                if isinstance(faker_or_template, dict) and "type" in faker_or_template:
                    df[col] = df[col].apply(lambda x: self._get_consistent_faker_value(
                        x, faker_or_template["type"], **faker_or_template.get("params", {})
                    ))
                elif faker_or_template in self.faker_methods:
                    df[col] = df[col].apply(lambda x: self._get_consistent_faker_value(x, faker_or_template))
                else:
                    template = Template(faker_or_template)
                    df[col] = df.apply(lambda row: template.render(row=row.to_dict(), faker=self.faker_proxy())
                                       if row[col] not in [None, ""] else row[col], axis=1)  # Preserve empty values

        output_file = file_path if overwrite else file_path.replace(".csv", "_anonymized.csv")
        df.to_csv(output_file, sep=separator, index=False, encoding=self.encoding)
        print(f"CSV file '{file_path}' anonymized. {'Overwritten' if overwrite else f'Saved as {output_file}'}.")


    def anonymize_json_file(self, file_path, json_paths, overwrite=False):
        """Anonymizes a JSON file using JSONPath."""
        if not json_parse:
            print("jsonpath-ng is required for JSON anonymization. Install it with 'pip install jsonpath-ng'.")
            return

        with open(file_path, 'r', encoding=self.encoding) as file:
            data = json.load(file)

        for json_path, faker_or_template in json_paths.items():
            json_expr = json_parse(json_path)
            for match in json_expr.find(data):
                if isinstance(faker_or_template, dict) and "type" in faker_or_template:
                    new_value = self._get_consistent_faker_value(
                        match.value, faker_or_template["type"], **faker_or_template.get("params", {})
                    )
                elif faker_or_template in self.faker_methods:
                    match.full_path.update(data, self._get_consistent_faker_value(match.value, faker_or_template))
                else:
                    template = Template(faker_or_template)
                    new_value = template.render(faker=self.faker_proxy())
                    match.full_path.update(data, new_value)

        output_file = file_path if overwrite else file_path.replace(".json", "_anonymized.json")
        with open(output_file, 'w', encoding=self.encoding) as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

        print(f"JSON file '{file_path}' anonymized. {'Overwritten' if overwrite else f'Saved as {output_file}'}.")
    
    def anonymize_xml_file(self, file_path, xml_paths, overwrite=False):
        """Anonymizes an XML file using XPath for both element text and attributes."""
        if not etree:
            print("lxml is required for XML anonymization. Install it with 'pip install lxml'.")
            return

        with open(file_path, 'r', encoding=self.encoding) as file:
            xml_string = file.read()

        try:
            xml_tree = etree.fromstring(xml_string)
        except etree.XMLSyntaxError:
            print(f"Invalid XML in file: {file_path}")
            return

        for xpath, faker_or_template in xml_paths.items():
            if "@" in xpath:  # If XPath targets an attribute (e.g., //address/@id)
                attr_xpath, attr_name = xpath.rsplit("/@", 1)
                for elem in xml_tree.xpath(attr_xpath):
                    if elem.get(attr_name) is not None:
                        if isinstance(faker_or_template, dict) and "type" in faker_or_template:
                            new_value = self._get_consistent_faker_value(
                                elem.get(attr_name), faker_or_template["type"], **faker_or_template.get("params", {})
                            )
                        elif faker_or_template in self.faker_methods:
                            new_value = self._get_consistent_faker_value(elem.get(attr_name), faker_or_template)
                        else:
                            template = Template(faker_or_template)
                            new_value = template.render(faker=self.faker_proxy()) if elem.get(attr_name) not in [None, ""] else elem.get(attr_name)

                        elem.set(attr_name, str(new_value))  # Update the attribute value

            else:  # Normal text element anonymization
                for elem in xml_tree.xpath(xpath):
                    if isinstance(faker_or_template, dict) and "type" in faker_or_template:
                        elem.text = self._get_consistent_faker_value(
                            elem.text, faker_or_template["type"], **faker_or_template.get("params", {})
                        )
                    elif faker_or_template in self.faker_methods:
                        elem.text = self._get_consistent_faker_value(elem.text, faker_or_template)
                    else:
                        template = Template(faker_or_template)
                        elem.text = template.render(faker=self.faker_proxy()) if elem.text not in [None, ""] else elem.text

        output_file = file_path if overwrite else file_path.replace(".xml", "_anonymized.xml")
        with open(output_file, 'w', encoding=self.encoding) as file:
            file.write(etree.tostring(xml_tree, encoding="utf-8").decode())

        print(f"XML file '{file_path}' anonymized. {'Overwritten' if overwrite else f'Saved as {output_file}'}.")

    def anonymize_db_table(self, db_url, table_name, id_column, columns_to_anonymize):
        """Anonymizes a database table while ensuring consistency."""
        if not create_engine:
            print("SQLAlchemy is required for database anonymization. Install it with 'pip install sqlalchemy'.")
            return

        engine = create_engine(db_url, connect_args={"encoding": self.encoding})
        metadata = MetaData()
        metadata.reflect(bind=engine)
        table = Table(table_name, metadata, autoload_with=engine)
        Session = sessionmaker(bind=engine)
        session = Session()

        query = select(table)
        rows = session.execute(query).fetchall()

        for row in rows:
            row_dict = row._asdict()
            new_values = {}

            for col, faker_or_template in columns_to_anonymize.items():
                if col in row_dict:
                    if isinstance(faker_or_template, dict) and "type" in faker_or_template:
                        # Handle "number" anonymization with min/max
                        new_values[col] = self._get_consistent_faker_value(
                            row_dict[col], faker_or_template["type"], **faker_or_template.get("params", {})
                        )
                    elif faker_or_template in self.faker_methods:
                        new_values[col] = self._get_consistent_faker_value(row_dict[col], faker_or_template)
                    else:
                        template = Template(faker_or_template)
                        new_values[col] = template.render(row=row_dict, faker=self.faker_proxy())

            if new_values:
                update_stmt = update(table).where(table.c[id_column] == row_dict[id_column]).values(**new_values)
                session.execute(update_stmt)

        session.commit()
        session.close()
        print(f"Table '{table_name}' anonymized successfully in database {db_url}.")


    def list_faker_methods(self):
        """Print all available Faker methods and exit."""
        print("Available Faker methods:")
        for method in sorted(self.faker_methods.keys()):
            print(f"- {method}")
        exit(0)


def main():
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

5. List all available Faker methods:
   python anonymizer.py --list-faker-methods

For further details and examples, see the readme.md file!
""",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--config", nargs="+", help="JSON configurations as command-line arguments.")
    parser.add_argument("--locale", type=str, default="en_US", help="Set Faker's locale (default: en_US)")
    parser.add_argument("--encoding", type=str, default="utf-8", help="Set file/database encoding (default: utf-8)")
    parser.add_argument("--list-faker-methods", action="store_true", help="List all available Faker methods and exit.")

    args = parser.parse_args()

    anonymizer = DataAnonymizer(locale=args.locale, encoding=args.encoding)

    if args.list_faker_methods:
        anonymizer.list_faker_methods()

    if not args.config:
        print("No configuration provided. Use --config or --list-faker-methods.")
        return

    for config_str in args.config:
        config = json.loads(config_str)

        if "file" in config:
            if config["file"].endswith(".json"):
                anonymizer.anonymize_json_file(config["file"], config["columns"], config.get("overwrite", False))
            elif config["file"].endswith(".xml"):
                anonymizer.anonymize_xml_file(config["file"], config["columns"], config.get("overwrite", False))
            elif config["file"].endswith(".csv"):
                anonymizer.anonymize_csv(config["file"], config["columns"], config.get("overwrite", False), config.get("separator", ","))
            else:
                print("Could not detect file type from the name. Supports *.csv, *.json and *.xml files!")
                exit(-2)            
        elif "table" in config:
            if 'db_url' not in config:
                print("Database anonymization needs 'db_url' set!")
                exit(-1)
            anonymizer.anonymize_db_table(
                config["db_url"], 
                config["table"], 
                config["id_column"], 
                config.get("columns", {})
            )

if __name__ == "__main__":
    main()
