#!/bin/bash
set -e

# Ensure vault directory is writable
if [ ! -w /vault ]; then
    echo "WARNING: /vault is not writable by user obsidian"
fi

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
