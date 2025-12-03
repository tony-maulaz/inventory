"""add users table and normalize user_roles

Revision ID: 0003_users_table
Revises: 0002_security_levels_and_roles
Create Date: 2025-12-03
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

# revision identifiers, used by Alembic.
revision = "0003_users_table"
down_revision = "0002_security_levels_and_roles"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # Existing user_roles structure: id, username, display_name, roles (comma-separated)
    old_rows = list(
        bind.execute(sa.text("SELECT username, display_name, roles FROM user_roles")).fetchall()
    )

    # Drop old table and recreate normalized schema
    op.drop_table("user_roles")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id"),
    )

    users_table = table(
        "users",
        column("id", sa.Integer),
        column("username", sa.String),
        column("display_name", sa.String),
    )
    user_roles_table = table(
        "user_roles",
        column("user_id", sa.Integer),
        column("role_id", sa.Integer),
    )

    # Reinsert data from old table
    for row in old_rows:
        username = row[0]
        display_name = row[1]
        roles_csv = row[2] or ""
        roles = [r.strip() for r in roles_csv.split(",") if r.strip()]

        result = bind.execute(
            users_table.insert().values(username=username, display_name=display_name).returning(sa.text("id"))
        )
        user_id = result.scalar()

        if roles:
            for role_name in roles:
                role_id = bind.execute(
                    sa.text("SELECT id FROM roles WHERE name = :name"), {"name": role_name}
                ).scalar()
                if role_id:
                    bind.execute(user_roles_table.insert().values(user_id=user_id, role_id=role_id))


def downgrade():
    bind = op.get_bind()

    # Fetch current data
    data = bind.execute(
        sa.text(
            """
            SELECT u.username, u.display_name, string_agg(r.name, ',') as roles
            FROM users u
            LEFT JOIN user_roles ur ON ur.user_id = u.id
            LEFT JOIN roles r ON r.id = ur.role_id
            GROUP BY u.id, u.username, u.display_name
            """
        )
    ).fetchall()

    op.drop_table("user_roles")
    op.drop_table("users")

    # Recreate old user_roles table
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("roles", sa.String(length=200), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
    )

    user_roles_old = table(
        "user_roles",
        column("username", sa.String),
        column("display_name", sa.String),
        column("roles", sa.String),
    )

    for row in data:
        bind.execute(
            user_roles_old.insert().values(
                username=row.username,
                display_name=row.display_name,
                roles=row.roles or "",
            )
        )
