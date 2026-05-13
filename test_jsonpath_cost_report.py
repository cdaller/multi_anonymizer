#!/usr/bin/env python3
import json
from jsonpath_ng import jsonpath, parse

with open("costreport.json", 'r', encoding='utf-8') as file:
    json_data = file.read()
    data = json.loads(json_data)

    # Create the JSONPath expression to match last names
    # jsonpath_expression = parse("$.costs.additionalCosts[*].entries[*].units[*].residents[*].name")
    # jsonpath_expression = parse("$.costs.additionalCosts[*]..units[*].residents[*].name")
    # jsonpath_expression = parse("$..residents[*].name")
    jsonpath_expression = parse("$..units[*].alternativeAddress.street")

    # Extract the last names
    names = [match.value for match in jsonpath_expression.find(data)]

    print(names)  # Outputs: ['Riegler', 'Auer']

    # file_encoding='UTF-8'

    # with open('testfiles/testoutput.json', 'w', encoding=file_encoding) as file:
    #     json.dump(data, file, indent=4, ensure_ascii=False)

