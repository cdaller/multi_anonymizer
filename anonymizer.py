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
    def __init__(self, db_url=None, locale="en_US"):
        """Initialize the anonymizer with a database connection (if provided) and locale."""
        self.fake = Faker(locale)  # Set Faker locale
        self.faker_methods = self._get_faker_methods()
        self.engine = None

        if db_url and create_engine:
            self.engine = create_engine(db_url)
            self.metadata = MetaData()
            self.Session = sessionmaker(bind=self.engine)
            self.session = self.Session()

    def _get_faker_methods(self):
        """Fetch all available Faker methods, filtering out internal methods."""
        faker_methods = {}
        for method in dir(self.fake):
            if not method.startswith("_"):  # Exclude internal methods
                try:
                    attr = getattr(self.fake, method)
                    if callable(attr):  # Ensure it's a callable Faker method
                        faker_methods[method] = attr
                except TypeError:
                    continue  # Skip attributes that raise TypeError

        return faker_methods

    def anonymize_csv(self, file_path, columns_to_anonymize, overwrite=False, separator=","):
        """Anonymizes a CSV file using Faker and Jinja2 templates, supporting custom separators."""
        if not pd:
            print("Pandas is required for CSV anonymization. Install it with 'pip install pandas'.")
            return

        df = pd.read_csv(file_path, sep=separator)

        for col, faker_or_template in columns_to_anonymize.items():
            if col in df.columns and faker_or_template in self.faker_methods:
                df[col] = df[col].apply(lambda _: self.faker_methods[faker_or_template]())

        for col, faker_or_template in columns_to_anonymize.items():
            if col in df.columns and faker_or_template not in self.faker_methods:
                template = Template(faker_or_template)
                df[col] = df.apply(lambda row: template.render(row=row.to_dict()), axis=1)

        output_file = file_path if overwrite else file_path.replace(".csv", "_anonymized.csv")
        df.to_csv(output_file, sep=separator, index=False)
        print(f"CSV file '{file_path}' anonymized. {'Overwritten' if overwrite else f'Saved as {output_file}'}.")

    def anonymize_json_file(self, file_path, json_paths, overwrite=False):
        """Anonymizes a JSON file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        data = self.anonymize_json_data(data, json_paths)

        output_file = file_path if overwrite else file_path.replace(".json", "_anonymized.json")
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=4)

        print(f"JSON file '{file_path}' anonymized. {'Overwritten' if overwrite else f'Saved as {output_file}'}.")

    def anonymize_xml_file(self, file_path, xml_paths, overwrite=False):
        """Anonymizes an XML file."""
        with open(file_path, 'r', encoding='utf-8') as file:
            xml_string = file.read()

        xml_string = self.anonymize_xml_data(xml_string, xml_paths)

        output_file = file_path if overwrite else file_path.replace(".xml", "_anonymized.xml")
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(xml_string)

        print(f"XML file '{file_path}' anonymized. {'Overwritten' if overwrite else f'Saved as {output_file}'}.")

    def anonymize_json_column(self, json_string, json_paths):
        """Anonymizes a JSON column using Faker and Jinja2 templates."""
        if not json_parse:
            print("jsonpath-ng is required for JSON anonymization. Install it with 'pip install jsonpath-ng'.")
            return json_string

        try:
            json_data = json.loads(json_string)
        except json.JSONDecodeError:
            return json_string  # Skip if not valid JSON

        for json_path, faker_or_template in json_paths.items():
            json_expr = json_parse(json_path)
            for match in json_expr.find(json_data):
                match.path.update(json_data, self.faker_methods.get(faker_or_template, faker_or_template)())

        return json.dumps(json_data)

    def anonymize_xml_column(self, xml_string, xml_paths):
        """Anonymizes an XML column using Faker and Jinja2 templates."""
        if not etree:
            print("lxml is required for XML anonymization. Install it with 'pip install lxml'.")
            return xml_string

        try:
            xml_tree = etree.fromstring(xml_string)
        except etree.XMLSyntaxError:
            return xml_string  # Skip if not valid XML

        for xpath, faker_or_template in xml_paths.items():
            for elem in xml_tree.xpath(xpath):
                elem.text = self.faker_methods.get(faker_or_template, faker_or_template)()

        return etree.tostring(xml_tree, encoding="utf-8").decode()

    def anonymize_db_table(self, table_name, id_column, columns_to_anonymize, json_columns=None, xml_columns=None):
        """Anonymizes a database table, including JSON and XML inside table columns."""
        if not self.engine:
            print("SQLAlchemy is required for database anonymization. Install it with 'pip install sqlalchemy'.")
            return

        table = Table(table_name, self.metadata, autoload_with=self.engine)
        query = select(table)
        rows = self.session.execute(query).fetchall()

        for row in rows:
            row_dict = row._asdict()  # ✅ Convert Row object to dictionary
            new_values = {}

            # Standard column anonymization
            for col, faker_or_template in columns_to_anonymize.items():
                if col in row_dict and faker_or_template in self.faker_methods:
                    new_values[col] = self.faker_methods[faker_or_template]()

            # Jinja2 templating for custom values
            for col, faker_or_template in columns_to_anonymize.items():
                if col in row_dict and faker_or_template not in self.faker_methods:
                    template = Template(faker_or_template)
                    new_values[col] = template.render(row=row_dict, faker=self.fake)

            # JSON Column Anonymization
            if json_columns:
                for col, json_paths in json_columns.items():
                    if col in row_dict and isinstance(row_dict[col], str):
                        new_values[col] = self.anonymize_json_column(row_dict[col], json_paths)

            # XML Column Anonymization
            if xml_columns:
                for col, xml_paths in xml_columns.items():
                    if col in row_dict and isinstance(row_dict[col], str):
                        new_values[col] = self.anonymize_xml_column(row_dict[col], xml_paths)

            # Apply updates if there are changes
            if new_values:
                update_stmt = update(table).where(table.c[id_column] == row_dict[id_column]).values(**new_values)
                self.session.execute(update_stmt)

        self.session.commit()
        print(f"Table '{table_name}' anonymized successfully.")

    def list_faker_methods(self):
        """Print all available Faker methods and exit."""
        print("Available Faker methods:")
        for method in sorted(self.faker_methods.keys()):
            print(f"- {method}")
        exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="Anonymize CSV, JSON, XML files, and database tables using Faker and Jinja2 templates.",
        epilog="Example:\n"
               "  python anonymizer.py --config '{\"file\": \"x.csv\", \"columns\": {\"name\": \"name\"}}'\n"
               "  python anonymizer.py --config '{\"db_url\": \"sqlite:///testfiles/my_database.db\", \"table\": \"persons\", \"columns\": {\"name\": \"name\"}}'\n"
               "  python anonymizer.py --list-faker-methods\n"
               "  python anonymizer.py --locale de_DE --config '{\"file\": \"x.csv\", \"columns\": {\"email\": \"{{ faker.email() }}\"}}'\n",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument("--config", nargs="+", help="JSON configurations as command-line arguments.")
    parser.add_argument("--locale", type=str, default="en_US", help="Set Faker's locale (default: en_US)")
    parser.add_argument("--list-faker-methods", action="store_true", help="List all available Faker methods and exit.")

    args = parser.parse_args()


    if args.list_faker_methods:
        anonymizer = DataAnonymizer(locale=args.locale)
        anonymizer.list_faker_methods()

    if not args.config:
        print("No configuration provided. Use --config or --list-faker-methods.")
        return

    for config_str in args.config:
        config = json.loads(config_str)
        anonymizer = DataAnonymizer(config.get("db_url"), args.locale)

        if "file" in config:
            print(f'Working on file {config["file"]}')
            if config["file"].endswith(".csv"):
                anonymizer.anonymize_csv(
                    config["file"],
                    config["columns"],
                    config.get("overwrite", False),
                    config.get("separator", ",")  # Default separator: comma
                )
            elif config["file"].endswith(".json"):
                anonymizer.anonymize_json_file(config["file"], config["columns"], config.get("overwrite", False))
            elif config["file"].endswith(".xml"):
                anonymizer.anonymize_xml_file(config["file"], config["columns"], config.get("overwrite", False))
        elif "table" in config:
            if "db_url" not in config:
                print("For database anonymization, parameter 'db_url' needs to be set in configuration!")
                exit(-2)
            anonymizer.anonymize_db_table(
                config["table"], 
                config["id_column"], 
                config.get("columns", {}), 
                config.get("json_columns", {}), 
                config.get("xml_columns", {})
            )


if __name__ == "__main__":
    main()
