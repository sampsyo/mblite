#!/usr/bin/env python
import sys
import re
import sqlite3
import os

CREATE_TABLES_SQL = 'CreateTables.sql'
OUT_DB = 'mblite.db'
SKIP_TABLES = (
    'clientversion', # just causes problems
    'replication_control',
)

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

def convert_dump(fh, table):
    for line in fh:
        line = line.strip()
        values = line.split('\t')
        exprs = []
        for value in values:
            if value == '\\N':
                exprs.append('null')
            else:
                expr = None
                
                # Is the value an integer?
                try:
                    int(value)
                except ValueError:
                    pass
                else:
                    expr = value
                
                if expr is None:
                    # Is the value a float?
                    if value.lower() not in ('infinity', 'nan'):
                        try:
                            float(value)                    
                        except ValueError:
                            pass
                        else:
                            expr = value
                
                if expr is None:
                    # Not a number. Treat as text.
                    expr = value.replace('\\', '\\\\').replace("'", "''")
                    expr = "'" + expr + "'"
                    
                exprs.append(expr)
        yield 'INSERT INTO %s VALUES (%s);\n' % (table, ', '.join(exprs))

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
    elif mode == '--undump':
        fn = os.path.expanduser(sys.argv[2])
        table = os.path.basename(fn)
        for line in convert_dump(open(fn), table):
            sys.stdout.write(line)
    elif mode == '--import':
        db = sqlite3.connect(OUT_DB)
        dumpdir = os.path.expanduser(sys.argv[2])
        for basename in os.listdir(dumpdir):
            if not basename.startswith('.') and basename not in SKIP_TABLES:
                fn = os.path.join(dumpdir, basename)
                print 'importing: %s' % basename
                for line in convert_dump(open(fn), basename):
                    try:
                        db.execute(line)
                    except sqlite3.OperationalError, exc:
                        print 'sqlite error on line: %s' %  repr(line)
                        print exc
                        sys.exit(1)
                db.commit()
        db.close()
    else:
        print 'unknown mode'
