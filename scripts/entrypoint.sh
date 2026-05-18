#!/bin/sh
# Vyper entrypoint — creates data directories with proper permissions.
set -e

# Create all known data directories with world-writable permissions.
# This is necessary because Docker volumes are mounted with host UID/GID
# and the app runs as a non-root user (appuser).
for dir in \
    /data/config \
    /data/scanner/solc \
    /data/scanner/results \
    /data/source \
    /data/reporter/reports \
    /data/notifier \
    /data/upkeep/update \
    /data/upkeep/backup \
    /data/upkeep/metrics \
    /data/exploit/pocs \
    /data/ai \
    /data/classifier \
    /data/dashboard \
    /data/orchestrator \
    /data/webhook \
    /data/immunefi \
    /data/learning \
; do
    mkdir -p "$dir" 2>/dev/null || true
    chmod 777 "$dir" 2>/dev/null || true
done

# Execute the original command (CMD from Dockerfile).
exec "$@"
