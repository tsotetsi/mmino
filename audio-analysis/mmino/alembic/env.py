import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Import your models/Base
from mmino.db.base import Base
from mmino.db import models 

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_database_url():
    """Construct the database URL from environment variables."""
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    db = os.getenv("POSTGRES_DB")
    if not all([user, password, host, db]):
        raise ValueError("One or more PostgreSQL environment variables are not set.")
    return f"postgresql://{user}:{password}@{host}/{db}"

config.set_main_option("sqlalchemy.url", get_database_url())

def include_object(obj, name, type_, reflected, compare_to):
    """
    Logic to include/exclude database objects. 
    Returns True to include, False to ignore.
    """
    # Example: Ignore internal Postgres or PostGIS tables if they appear
    ignored_tables = ["spatial_ref_sys", "health_check"]
    
    if type_ == "table" and name in ignored_tables:
        return False
    return True

def process_revision_directives(context, revision, directives):
    """Prevents empty migrations from being generated."""
    if getattr(config.cmd_opts, 'autogenerate', False):
        script = directives[0]
        if script.upgrade_ops.is_empty():
            directives[:] = []
            print('No changes in schema detected.')

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()