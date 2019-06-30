#!/usr/bin/env bash

# taken from /home/mica/git/blackserver/ensure_blackserver_running.bash

# exit if it's already running
ps aux | grep [g]rocery | grep -v ensure >/dev/null && exit 0

echo starting server
bash /home/mica/git/mica/grocery-tracker/backend/start_server.bash
