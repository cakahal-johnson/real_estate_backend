## This directory contains Alembic migration environment.

To create and apply migrations:
  1. alembic revision --autogenerate -m "init db"
  2. alembic upgrade head


## Future Use

Each time you change a model (e.g., add a column):

alembic revision --autogenerate -m "add new field"
alembic upgrade head

# Initialize Alembic migrations
alembic revision --autogenerate -m "init users and listings tables"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
