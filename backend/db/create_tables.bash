#!/usr/bin/env bash

# create groceries schema
psql -c 'CREATE SCHEMA IF NOT EXISTS groceries;'

# # get search_path
# search_path=$(printf '\\pset pager off\nshow search_path\n' | psql | grep '\----' -C 1 | tail -1)
#
# # if groceries schema not on path, put it there
# echo search_path | grep groceries \
#     || psql -c "alter user $USER set search_path = $search_path , groceries"

psql <<EOF
CREATE TABLE IF NOT EXISTS groceries.foods (
    fid serial primary key
    , food text
    , dt timestamp without time zone default now()
    , location text
    , price numeric(7, 2)
    , count decimal
    , unit varchar(10)
);
EOF
