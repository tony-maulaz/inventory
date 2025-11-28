"""Initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2025-11-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "device_statuses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=50), nullable=False, unique=True),
    )
    op.create_table(
        "device_types",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("inventory_number", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("type_id", sa.Integer(), sa.ForeignKey("device_types.id"), nullable=False),
        sa.Column("status_id", sa.Integer(), sa.ForeignKey("device_statuses.id"), nullable=False),
        sa.UniqueConstraint("inventory_number", name="uq_inventory_number"),
    )
    op.create_table(
        "test_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("roles", sa.String(length=200), nullable=False, server_default=""),
    )
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False, index=True),
        sa.Column("borrower", sa.String(length=100), nullable=False),
        sa.Column("borrower_display_name", sa.String(length=200), nullable=True),
        sa.Column("usage_location", sa.String(length=200), nullable=True),
        sa.Column("loaned_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("returned_at", sa.DateTime(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table("loans")
    op.drop_table("test_users")
    op.drop_table("devices")
    op.drop_table("device_types")
    op.drop_table("device_statuses")
