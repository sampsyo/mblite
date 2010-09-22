#!/usr/bin/env python
import sys
import re
import sqlite3

CREATE_TABLES_SQL = 'CreateTables.sql'
OUT_DB = 'mblite.db'

def convert_createtables(fh):
    fields = []
    constraints = []
    for line in fh:
        if line.startswith('    '):
            # Inside a table declaration.
            
            # Parse the line.
            line = line.strip()
            line = re.sub('\s*--.+$', '', line) # strip comments
            if not line:
                continue
            m = re.match(r'(\S+)\s+(.+?),?$', line)
            if m is None:
                print repr(line)
            name, kind = m.groups()
            
            # Deal with table constraints.
            if name in ('CONSTRAINT', 'CHECK'):
                constraints.append('    %s %s' % (name, kind))
                continue
            
            # Translate a column declaration.
            kind = kind.lower()
            if name == 'id' or 'serial' in kind:
                newkind = 'INTEGER PRIMARY KEY'
            elif 'text' in kind or 'char' in kind:
                newkind = 'TEXT'
            elif 'int' in kind:
                newkind = 'INTEGER'
            elif 'timestamp' in kind or 'date' in kind:
                newkind = 'INTEGER' #???
            elif 'bool' in kind:
                newkind = 'INTEGER'
            elif 'real' in kind:
                newkind = 'REAL'
            else:
                raise ValueError('unknown kind in %s' % repr(line))
            fields.append('    %s %s' % (name, newkind))
        
        else:
            # Non-declaration line. Probably leave it alone.
            if line.startswith('\\'):
                continue
            elif line.startswith(')'):
                # Yield all the table elements.
                yield ',\n'.join(fields + constraints) + '\n'
                fields = []
                constraints = []
            yield line

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == '--schema':
        for line in convert_createtables(open(CREATE_TABLES_SQL)):
            sys.stdout.write(line)
    elif mode == '--init':
        script = ''.join(convert_createtables(open(CREATE_TABLES_SQL)))
        db = sqlite3.connect(OUT_DB)
        db.executescript(script)
        db.commit()
        db.close()
    else:
        print 'unknown mode'
