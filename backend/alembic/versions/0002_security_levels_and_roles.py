"""add security level and roles tables

Revision ID: 0002_security_levels_and_roles
Revises: 0001_initial
Create Date: 2024-04-09
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = "0002_security_levels_and_roles"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


ROLE_NAMES = ["employee", "gestionnaire", "expert", "admin"]


def upgrade():
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("roles", sa.String(length=200), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.add_column(
        "devices",
        sa.Column(
            "security_level",
            sa.String(length=20),
            nullable=False,
            server_default="standard",
        ),
    )

    roles_table = table("roles", column("name", sa.String))
    op.bulk_insert(roles_table, [{"name": r} for r in ROLE_NAMES])

    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    if "test_users" in existing_tables:
        bind.execute(
            sa.text(
                """
                INSERT INTO user_roles (username, display_name, roles)
                SELECT username, display_name, roles FROM test_users
                ON CONFLICT (username) DO NOTHING
                """
            )
        )

    op.alter_column("devices", "security_level", server_default=None)


def downgrade():
    op.drop_column("devices", "security_level")
    op.drop_table("user_roles")
    op.drop_table("roles")
