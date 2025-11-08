#!/bin/bash
# Install dependencies required for 2FA enforcement scripts

echo "Installing 2FA enforcement script dependencies..."

# Install psycopg2 if not already present
pip3 install psycopg2-binary --quiet

# Install postgresql-client for database checks
apk add --no-cache postgresql-client 2>/dev/null || \
apt-get update && apt-get install -y postgresql-client 2>/dev/null || \
yum install -y postgresql 2>/dev/null || true

echo "Dependencies installed successfully"
