#!/usr/bin/env bash

cd $(dirname $0)

/home/mica/anaconda3/envs/blackserver/bin/gunicorn \
    server:api \
    --timeout 0 \
    --reload \
    --pid pid.txt \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --keyfile /home/mica/.ssh/black.key \
    --certfile /home/mica/.ssh/black.crt \
    --bind 0.0.0.0:$(cat port.txt)
