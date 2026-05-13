#!/usr/bin/env python

import sys

if len(sys.argv) > 1:
    param = sys.argv[1]
else:
    param = 'DefaultParam'

from jinja2 import Template
import os
import sys

template = Template("{{ env['DB_URL'] or 'DefaultVal' }}")
r = template.render(env=os.environ)
print(f"in code: {r}")


template = Template(param)
r = template.render(env=os.environ)
print(f"command line param: {r}")