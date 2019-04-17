#!/usr/bin/env python3

"""
CSV filter lines: reads a csv files, filters on a given expression and prints all lines that match 
the expression and the header line(s) of the csv files if wanted.
Nothing that cannot be done with a combination of 'head' and 'grep' - but both did not work
correctly with csv files in UTF-16LE.

Author: Christof Dallermassl
License: MIT
"""

import sys
import argparse
import contextlib

def parseArgs():
    parser = argparse.ArgumentParser(description = 'Filter a csv file but keep the header as is')
    parser.add_argument('filterExpression',
                        help='the filter to be used.')
    parser.add_argument('infile', nargs='?', default='-',
                        help='inputfile if given, otherwise reading from stdin. Use "-" to use stdin if an outfile is used but stdin should be used to read.')
    parser.add_argument('outfile', nargs='?', default='-',
                        help='outputfile to print result to. If not given prints to stdout. Use "-" to print to stdout.')
    parser.add_argument('-e', '--encoding', dest='encoding', default='ISO-8859-15',
                        help='the encoding of the file to read/write. Default is ISO-8859-15')
    parser.add_argument('--header-lines', dest='headerLines', default='0',
                        help='set to number of header lines to ignore, default = 0')
    return parser.parse_args()

@contextlib.contextmanager
def smart_open(filename: str = None, mode: str = 'r', *args, **kwargs):
    if filename == '-':
        if 'r' in mode:
            stream = sys.stdin
        else:
            stream = sys.stdout
        if 'b' in mode:
            fh = stream.buffer
        else:
            fh = stream
    else:
        fh = open(filename, mode, *args, **kwargs)

    try:
        yield fh
    finally:
        try:
            fh.close()
        except AttributeError:
            pass

if __name__ == '__main__':
    ARGS = parseArgs()

    if ARGS.filterExpression is None:
        ARGS.help
        sys.exit(1)

    with smart_open(ARGS.infile, 'r', encoding=ARGS.encoding) as file_in:
        with smart_open(ARGS.outfile, 'w', encoding=ARGS.encoding) as file_out:
            skipLines = int(ARGS.headerLines)
            while (skipLines > 0):
                file_out.write(next(file_in))
                skipLines = skipLines - 1 
            file_out.writelines(line for line in file_in if ARGS.filterExpression in line)