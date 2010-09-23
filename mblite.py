#!/usr/bin/env python
import sys
import re
import sqlite3
import os
import subprocess

SQLITE3 = 'sqlite3'
CREATE_TABLES_SQL = 'CreateTables.sql'
CREATE_INDICES_SQL = 'CreateIndexes.sql'
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
                newkind = 'BOOLEAN' # == integer
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
                # Currently, constraints are dropped for speed because
                # the DB is supposed to be used in a read-only way anyway.
                yield ',\n'.join(fields) + '\n'
                fields = []
                constraints = []
            yield line

def convert_createindices(fh):
    for line in fh:
        if line.startswith('\\'):
            continue
        elif line.startswith("CREATE "):
            if 'lower(' in line:
                # SQLite doesn't support functions in index columns.
                continue
            if 'artistalias_nameindex' in line:
                # Strange error: the artistalias.name index is not unique.
                line = line.replace('UNIQUE ', '')
            yield line
        else:
            yield line

def import_dump(dumpfn, dbfn):
    # Run the CLI .import command to actually import the data.
    table = os.path.basename(dumpfn)
    sql = [
        '.separator "\\t"',
        'PRAGMA synchronous = OFF;',
        ".import '%s' %s" % (dumpfn.replace("'", "''"), table),
    ]
    proc = subprocess.Popen((SQLITE3, dbfn), stdin=subprocess.PIPE)
    out, err = proc.communicate(input='\n'.join(sql))
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    
    # Now fix up the data. Replace \N marker with null; t and f with
    # 1 and 0.
    db = sqlite3.connect(dbfn)
    c = db.execute('PRAGMA table_info(%s)' % table)
    fields = [row[1:3] for row in c]
    for field, kind in fields:
        db.execute("UPDATE %s SET %s=NULL WHERE %s='\\N';" %
                   (table, field, field))
        if kind == 'BOOLEAN':
            db.execute("UPDATE %s SET %s=(%s is 't');" %
                       (table, field, field))
    db.commit()

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == '--schema':
        for line in convert_createtables(open(CREATE_TABLES_SQL)):
            sys.stdout.write(line)
        for line in convert_createindices(open(CREATE_INDICES_SQL)):
            sys.stdout.write(line)
    elif mode == '--init':
        script = ''.join(convert_createtables(open(CREATE_TABLES_SQL)))
        db = sqlite3.connect(OUT_DB)
        db.executescript(script)
        db.commit()
        db.close()
    elif mode == '--import':
        dumpdir = os.path.expanduser(sys.argv[2])
        for basename in os.listdir(dumpdir):
            if not basename.startswith('.'):
                fn = os.path.join(dumpdir, basename)
                print 'importing: %s' % basename
                import_dump(fn, OUT_DB)
    elif mode == '--index':
        script = ''.join(convert_createindices(open(CREATE_INDICES_SQL)))
        db = sqlite3.connect(OUT_DB)
        db.executescript(script)
        db.commit()
        db.close()
    else:
        print 'unknown mode'
