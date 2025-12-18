#!/bin/bash
set -e

# Check if secret exists before reading
if [ -f /run/secrets/mmino_app_password ]; then
    app_password=$(cat /run/secrets/mmino_app_password)
else
    echo "Error: Secret mmino_app_password not found in /run/secrets/"
    exit 1
fi

healthcheck_password=$(cat /run/secrets/healthcheck_password)

psql -v ON_ERROR_STOP=1 --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" <<-EOSQL
    -- Create roles only if they don't exist
    DO \$$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'healthcheck_user') THEN
            CREATE ROLE healthcheck_user LOGIN PASSWORD '$healthcheck_password';
        END IF;
        
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mmino_app') THEN
            CREATE ROLE mmino_app LOGIN CREATEDB PASSWORD '$app_password';
        END IF;
    END
    \$$;

    -- Set permissions on the database automatically created by Docker
    GRANT CONNECT ON DATABASE "$POSTGRES_DB" TO healthcheck_user;
    ALTER DATABASE "$POSTGRES_DB" OWNER TO mmino_app;
    
    -- Connect to the DB to create the schema
    \c "$POSTGRES_DB"
    CREATE SCHEMA IF NOT EXISTS app_schema AUTHORIZATION mmino_app;
EOSQL