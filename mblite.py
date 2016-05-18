#!/usr/bin/env python
from __future__ import print_function
import sys
import re
import sqlite3
import os
import subprocess
import requests

SQLITE3 = 'sqlite3'
OUT_DB = 'mblite.db'
GIT_URL = 'https://github.com/metabrainz/musicbrainz-server/raw/master/'
CREATE_TABLES_PATH = 'admin/sql/CreateTables.sql'
CREATE_INDICES_PATH = 'admin/sql/CreateIndexes.sql'
DUMP_URL = 'http://ftp.musicbrainz.org/pub/musicbrainz/data/fullexport/'
DUMP_LATEST_FILE = 'LATEST'
DUMP_FILE = 'mbdump.tar.bz2'


def convert_createtables(fh):
    fields = []
    constraints = []
    for line in fh:
        if line.startswith('    '):
            # Inside a table declaration.

            # Parse the line.
            line = line.strip()
            line = re.sub('\s*--.+$', '', line)  # Strip comments.
            if not line:
                continue
            m = re.match(r'(\S+)\s+(.+?),?$', line)
            if m is None:
                print(repr(line))
            name, kind = m.groups()

            # Deal with table constraints.
            if name in ('CONSTRAINT', 'CHECK'):
                constraints.append('    %s %s' % (name, kind))
                continue

            # Translate a column declaration.
            kind = kind.lower()
            if name == 'id' or 'serial' in kind:
                newkind = 'INTEGER PRIMARY KEY'
            elif 'text' in kind or 'char' in kind or 'uuid' in kind:
                newkind = 'TEXT'
            elif 'int' in kind:
                newkind = 'INTEGER'
            elif 'timestamp' in kind or 'date' in kind:
                newkind = 'INTEGER'  # ???
            elif 'bool' in kind:
                newkind = 'BOOLEAN'  # == integer
            elif 'real' in kind:
                newkind = 'REAL'
            elif 'cube' in kind:
                newkind = 'TEXT'  # Actually a vector.
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
    """Given a file-like object referring to an index creation SQL file,
    yields a list of SQLite-valid commands in that file.
    """
    lines = []
    for line in fh:
        # Strip comments.
        line = re.sub(r'--.*', '', line).strip()

        if line.startswith('\\') or not line:
            continue
        elif line.startswith("CREATE "):
            if 'lower(' in line.lower() or 'page_index(' in line \
                    or 'musicbrainz_collate(' in line:
                # SQLite doesn't support functions in index columns.
                continue
            if 'artistalias_nameindex' in line:
                # Strange error: the artistalias.name index is not unique.
                line = line.replace('UNIQUE ', '')
            if 'USING' in line:
                # Ignore custom index types.
                line = re.sub(r'USING\s+\w+', '', line)
            lines.append(line)
        else:
            lines.append(line)

    # Split into commands.
    for command in ''.join(lines).split(';'):
        command = command.strip()
        if command and command.lower() not in ('begin', 'commit'):
            yield command


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


def download_url(url, filename):
    """Download an HTTP URL to a local file."""
    req = requests.get(url, stream=True)
    with open(filename, 'wb') as f:
        for chunk in req.iter_content(chunk_size=1024):
            f.write(chunk)


def fetch_data(outdir='.'):
    """Download and extract a MusicBrainz data snapshot."""
    # Download the mbdump archive.
    dirname = requests.get(DUMP_URL + DUMP_LATEST_FILE).text.strip()
    dump_url = DUMP_URL + dirname + '/' + DUMP_FILE
    print('downloading:', dump_url)
    download_url(dump_url, DUMP_FILE)

    # Extract it.
    print('extracting archive')
    if not os.path.exists(outdir):
        os.mkdir(outdir)
    subprocess.check_call(['tar', '-xf', DUMP_FILE, '-C', outdir])


if __name__ == '__main__':
    mode = sys.argv[1]
    tables_sql = os.path.basename(CREATE_TABLES_PATH)
    indices_sql = os.path.basename(CREATE_INDICES_PATH)

    if mode == '--schema':
        for line in convert_createtables(open(tables_sql)):
            sys.stdout.write(line)
        for command in convert_createindices(open(indices_sql)):
            print(command + ';')

    elif mode == '--init':
        script = ''.join(convert_createtables(open(tables_sql)))
        db = sqlite3.connect(OUT_DB)
        db.executescript(script)
        db.commit()
        db.close()

    elif mode == '--import':
        dumpdir = os.path.expanduser(sys.argv[2])
        for basename in os.listdir(dumpdir):
            if not basename.startswith('.'):
                fn = os.path.join(dumpdir, basename)
                print('importing: %s' % basename)
                import_dump(fn, OUT_DB)

    elif mode == '--index':
        commands = convert_createindices(open(indices_sql))
        db = sqlite3.connect(OUT_DB)
        for command in commands:
            name_match = re.search(r' INDEX\s+(\S*)', command)
            if name_match:
                print('indexing: %s' % name_match.group(1))
            else:
                print('executing: %s' % command)
            db.execute(command)
        db.commit()
        db.close()

    elif mode == '--fetch-sql':
        for path in (CREATE_TABLES_PATH, CREATE_INDICES_PATH):
            fn = os.path.basename(path)
            url = GIT_URL + path
            download_url(url, fn)

    elif mode == '--fetch-data':
        fetch_data()

    else:
        print('unknown mode')
