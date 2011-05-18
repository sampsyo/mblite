#!/bin/sh

if [ -z "$1" ]
then
    echo $0: usage: $0 /path/to/mbdump
    exit 1
fi

dbfile=mblite.db
script=./mblite.py
mbdump=$1

echo `date` Fetching SQL files from git.
$script --fetch-sql
ls -l *.sql

echo `date` Removing any previous database.
rm -f $dbfile

echo `date` Initializing schema.
$script --init
ls -l $dbfile

echo `date` Importing data.
$script --import $mbdump
ls -l $dbfile

echo `date` Indexing.
$script --index
ls -l $dbfile

echo `date` Done.
