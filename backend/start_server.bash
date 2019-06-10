#!/usr/bin/env bash

gunicorn \
    server:api \
    --timeout 0 \
    --reload \
    --pid pid.txt \
    --access-logfile - \
    --error-logfile - \
    --log-level debug \
    --keyfile /Users/mica/.ssh/mica_CA/localhost/localhost.key \
    --certfile /Users/mica/.ssh/mica_CA/localhost/localhost.crt
