#!/usr/bin/env python3
import json
from jsonpath_ng import jsonpath, parse

data = {
    "person": {
        "lastname": "Ortiz",
        "firstname": "Jeremy",
        "age": 90,
        "email": "about@example.com"
    }
}

# Create the JSONPath expression to match last names
jsonpath_expression = parse('$.person.lastname')

# Extract the last names
last_names = [match.value for match in jsonpath_expression.find(data)]

print(last_names)  # Outputs: ['Riegler', 'Auer']

file_encoding='UTF-8'

with open('testfiles/testoutput.json', 'w', encoding=file_encoding) as file:
    json.dump(data, file, indent=4, ensure_ascii=False)

