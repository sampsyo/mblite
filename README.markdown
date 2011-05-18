mblite
======

This is a probably-doomed experiment intending to import the entire
[MusicBrainz][mb] dataset into an [SQLite][sqlite] database. The primary reason
is to *read* the database quickly and conveniently. (Note that I have no
illusions of being able to efficiently support writes.) Currently, if you want
a local copy of the MusicBrainz database, you need a PostgreSQL server and a
bunch of complicated Perl and Java software. The goal here is that, by using
SQLite, a local MB database will be much easier to set up. In fact, mblite only
needs Python and SQLite, which are ubiquitous on modern OSes.

If all goes well, then this infrastructure could even be used to quickly and
easily set up read-only MusicBrainz mirrors. While its scalability is
questionable, SQLite can be much less
resource-intensive than "production" databases like PostreSQL, which are
designed to support frequent, concurrent writes.

[mb]: http://musicbrainz.org/
[sqlite]: http://sqlite.org/

Creating a Database
-------------------

To create an SQLite MusicBrainz database, first fetch a recent `mbdump` [from
the horse's mouth][mbdownload]. Then run these commands:

    $ ./mblite.py --fetch-sql
    $ ./mblite.py --init
    $ ./mblite.py --import /path/to/mbdump
    $ ./mblite.py --index

Supply the path to the PostgreSQL data dump directory as the argument to the
second command. There's also a `create.sh` script that automates this process.

After a good long while, this will create a database called `mblite.db`
containing a full copy of the MusicBrainz snapshot. When I ran this most
recently on my aging Core 2 Duo, the import took about an hour and a half
and created a 2 GB database. Indexing the DB took another 7 hours (!) and
grew the database to about 4.4 GB.

[mbdownload]: http://ftp.musicbrainz.org/pub/musicbrainz/data/fullexport/

The Future
----------

Things to do next:

  * Implement a library for querying the database.
  * Implement a clone of the MusicBrainz XML Web service that uses the SQLite
    database as a backend.
  * Explore using SQLite's full-text indexing to support Lucene-like queries.
  * Automatically fetch the latest snapshot.

Credits
-------

[Adrian Sampson][adrian] is responsible for this abomination. The code is
made available under the [GPL][gpl].

[adrian]: mailto:adrian@radbox.org
[gpl]: http://www.gnu.org/licenses/gpl.html
