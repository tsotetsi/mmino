#!/bin/sh
set -e

ACL_FILE="/tmp/redis-acl.conf"
CONF_FILE="/usr/local/etc/redis/redis.conf"

# Read the Redis password from the secret
if [ -f /run/secrets/redis_password ]; then
    REDIS_PASSWORD=$(cat /run/secrets/redis_password)
    export REDIS_PASSWORD
    echo "Redis password loaded from secrets"
else
    echo "ERROR: Redis password secret not found at /run/secrets/redis_password"
    exit 1
fi

echo "Creating Redis ACL file: $ACL_FILE"

# Generate ACL file using the password
cat > "$ACL_FILE" <<EOF
user default on >${REDIS_PASSWORD} ~* &* +@all -@dangerous
EOF

echo "ACL file created successfully"

# Set proper permissions
chmod 644 "$ACL_FILE"
chown redis:redis "$ACL_FILE" 2>/dev/null || true

echo "Starting Redis server..."
exec gosu redis redis-server "$CONF_FILE" --aclfile "$ACL_FILE"