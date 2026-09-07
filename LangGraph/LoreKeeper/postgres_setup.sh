#!/usr/bin/env bash
# Execute using this command: export PATH="/usr/lib/postgresql/16/bin:$PATH" && bash postgres_setup.sh
set -e

# Automatically locate binaries on Ubuntu/Debian
if ! command -v initdb &> /dev/null; then
    PG_BIN=$(ls -d /usr/lib/postgresql/*/bin 2>/dev/null | tail -n 1)
    if [ -n "$PG_BIN" ]; then
        export PATH="$PG_BIN:$PATH"
    fi
fi

PG_DATA_DIR="$(pwd)/minimal_pgdata"
PG_PORT=5433
PG_DB="langgraph_db"
PG_LOG="$(pwd)/pg_minimal.log"

# Fix 1: Handle execution as root by creating/using an unprivileged user
if [ "$(id -u)" -eq 0 ]; then
    echo "Running as root. Creating 'pguser' to manage minimal PostgreSQL..."
    id -u pguser &>/dev/null || useradd -m -s /bin/bash pguser
    chown -R pguser:pguser "$(pwd)"
    
    # Re-exec this script as 'pguser'
    exec su pguser -c "export PATH=$PATH; bash $0"
    exit 0
fi

echo "=== 1. Cleaning Old Data ==="
pg_ctl -D "$PG_DATA_DIR" stop &>/dev/null || true
rm -rf "$PG_DATA_DIR" "$PG_LOG"

echo "=== 2. Initializing Data Directory ==="
initdb -D "$PG_DATA_DIR" --auth-host=trust --auth-local=trust

echo "=== 3. Injecting Configuration ==="
cat <<EOT >> "$PG_DATA_DIR/postgresql.conf"
unix_socket_directories = '$PG_DATA_DIR'
port = $PG_PORT
max_connections = 10
shared_buffers = 16MB
work_mem = 2MB
maintenance_work_mem = 16MB
autovacuum = off
wal_level = minimal
max_wal_senders = 0
fsync = off
EOT

echo "=== 4. Starting Local PostgreSQL Instance ==="
pg_ctl -D "$PG_DATA_DIR" -l "$PG_LOG" start

sleep 2

echo "=== 5. Creating LangGraph Database ==="
createdb -h localhost -p $PG_PORT "$PG_DB"

echo ""
echo "=========================================================="
echo "Minimal Postgres is running!"
echo "RAM Usage: ~30 MB"
echo "Connection String: postgresql://localhost:$PG_PORT/$PG_DB"
# postgresql://localhost:5433/langgraph_db
echo "To stop server:   pg_ctl -D $PG_DATA_DIR stop"
# pg_ctl -D /workspaces/aravindan22.github.io/LangGraph/LoreKeeper/minimal_pgdata stop
echo "=========================================================="