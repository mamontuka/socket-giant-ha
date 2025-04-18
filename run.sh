#!/usr/bin/with-contenv bashio
set -e
echo "Socket-Giant Service started"

## start ritar-bms main part
python3 -u /socket-giant.py
