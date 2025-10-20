from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

# --- Ensure project root is on sys.path ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(BASE_DIR)

# --- Import Base and models ---
from app.database import Base
from app import models

# --- Alembic Config object ---
config = context.config

# --- Logging setup ---
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Metadata for autogeneration ---
target_metadata = Base.metadata

# --- Helper: Database URL fallback ---
def get_url():
    return os.getenv("DATABASE_URL", "sqlite:///./real_estate.db")


# --- Ensure required runtime directories exist ---
def ensure_runtime_dirs():
    os.makedirs(os.path.join(BASE_DIR, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)


# --- Offline migration mode ---
def run_migrations_offline():
    ensure_runtime_dirs()
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# --- Online migration mode ---
def run_migrations_online():
    ensure_runtime_dirs()
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Override URL if DATABASE_URL env var exists
    if os.getenv("DATABASE_URL"):
        connectable = engine_from_config(
            {**config.get_section(config.config_ini_section), "sqlalchemy.url": get_url()},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
