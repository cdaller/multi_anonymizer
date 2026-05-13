#!/usr/bin/env python3

import re

def search_and_replace_dynamic(input_string: str, pattern: str, replacement: str) -> str:
    """
    The input string is matched against the given pattern. The group(1) is then replaced.
    If the pattern did not match, the input string is returned.
    """
    p = re.compile(pattern)
    m = p.match(input_string)
    if m is None:
        print(f"Regexp did not match inputstring '{input_string}' - no change!")
        return input_string
    
    found = m.group(1)
    start_pos = m.start(1)
    return f"{input_string[:m.start(1)]}{replacement}{input_string[m.end(1):]}"
    
    # Perform the search and replace using the replacement function
    result_string = re.sub(pattern, replacement_func, input_string)
    return result_string

# Example usage
original_string = "card no: xxx and then another text"
pattern = r"card no: (\S+).*"
replacement = "1234567"
result_dynamic = search_and_replace_dynamic(original_string, pattern, replacement)
print(result_dynamic)

original_string = "Hubert Auer"
pattern = "\\w*\\s(\\w*)"
replacement = "Dallermassl"
result_dynamic = search_and_replace_dynamic(original_string, pattern, replacement)
print(result_dynamic)
