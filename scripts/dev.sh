#!/usr/bin/env bash

# Open browser in a completely detached background process
(
    sleep 5
    if command -v xdg-open &> /dev/null; then
        xdg-open "http://localhost:8000" > /dev/null 2>&1
    elif command -v open &> /dev/null; then
        open "http://localhost:8000" > /dev/null 2>&1
    fi
) &

# Run process-compose in the foreground
exec process-compose up
