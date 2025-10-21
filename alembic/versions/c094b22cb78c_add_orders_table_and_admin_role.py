# alembic/versions/c094b22cb78c_add_orders_table_and_admin_role.py
"""Add orders table and admin role"""

from alembic import op
import sqlalchemy as sa

# Revision identifiers
revision = '0002_add_orders_table_and_admin_role'
down_revision = '0001_initial_migration'
branch_labels = None
depends_on = None


def upgrade():
    # --- Orders table ---
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('buyer_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('listing_id', sa.Integer(), sa.ForeignKey('listings.id', ondelete='CASCADE')),
        sa.Column('status', sa.String(length=50), server_default='pending'),  # pending / approved / completed
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Optional: update users.role default to allow 'admin' ---
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('role', existing_type=sa.String(20), server_default='buyer')


def downgrade():
    op.drop_table('orders')
