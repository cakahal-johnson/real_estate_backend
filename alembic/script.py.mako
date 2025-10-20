"""Add owner_id to listings"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = 'abcd1234'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('listings', sa.Column('owner_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'listings', 'users', ['owner_id'], ['id'])


def downgrade():
    op.drop_constraint(None, 'listings', type_='foreignkey')
    op.drop_column('listings', 'owner_id')
