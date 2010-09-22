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

    $ ./mblite.py --init
    $ ./mblite.py --import /path/to/mbdump

Supply the path to the PostgreSQL data dump directory as the argument to the
second command.

After a good long while, this will create a database called `mblite.db`
containing a full copy of the MusicBrainz snapshot. When I ran this most
recently, it took a few hours and the database file ended up about 2 GB in
size.

[mbdownload]: http://wiki.musicbrainz.org/Database_Download

The Future
----------

Things to do next:

  * Use `executemany` and shorter transactions to make the import process go
    faster.
  * Database indices.
  * Implement a library for querying the database.
  * Implement a clone of the MusicBrainz XML Web service that uses the SQLite
    database as a backend.
  * Explore using SQLite's full-text indexing to support Lucene-like queries.
  * Script for automatically fetching and importing the latest snapshot.
  * Import boolean columns correctly.

Credits
-------

[Adrian Sampson][adrian] is responsible for this abomination. The code is
made available under the [GPL][gpl].

[adrian]: mailto:adrian@radbox.org
[gpl]: http://www.gnu.org/licenses/gpl.html
