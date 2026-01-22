"""Link loans to users

Revision ID: 0002_loans_borrower_id
Revises: 0001_initial
Create Date: 2025-11-27
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_loans_borrower_id"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("loans", sa.Column("borrower_id", sa.Integer(), nullable=True))
    op.create_index("ix_loans_borrower_id", "loans", ["borrower_id"])
    op.create_foreign_key(
        "fk_loans_borrower_id_users",
        "loans",
        "users",
        ["borrower_id"],
        ["id"],
    )

    conn = op.get_bind()
    loans = sa.table(
        "loans",
        sa.column("borrower", sa.String),
        sa.column("borrower_id", sa.Integer),
    )
    users = sa.table("users", sa.column("id", sa.Integer), sa.column("username", sa.String))

    borrowers = conn.execute(sa.select(sa.distinct(loans.c.borrower))).fetchall()
    for (borrower,) in borrowers:
        if borrower is None:
            continue
        user_id = conn.execute(
            sa.select(users.c.id).where(users.c.username == borrower)
        ).scalar()
        if not user_id:
            result = conn.execute(sa.insert(users).values(username=borrower))
            if result.inserted_primary_key:
                user_id = result.inserted_primary_key[0]
            else:
                user_id = conn.execute(
                    sa.select(users.c.id).where(users.c.username == borrower)
                ).scalar()
        conn.execute(
            sa.update(loans)
            .where(loans.c.borrower == borrower)
            .values(borrower_id=user_id)
        )

    op.alter_column("loans", "borrower_id", nullable=False)
    op.drop_column("loans", "borrower")


def downgrade():
    op.add_column("loans", sa.Column("borrower", sa.String(length=100), nullable=True))

    conn = op.get_bind()
    loans = sa.table(
        "loans",
        sa.column("borrower", sa.String),
        sa.column("borrower_id", sa.Integer),
    )
    users = sa.table("users", sa.column("id", sa.Integer), sa.column("username", sa.String))

    pairs = conn.execute(sa.select(users.c.id, users.c.username)).fetchall()
    for user_id, username in pairs:
        conn.execute(
            sa.update(loans)
            .where(loans.c.borrower_id == user_id)
            .values(borrower=username)
        )

    op.alter_column("loans", "borrower", nullable=False)
    op.drop_constraint("fk_loans_borrower_id_users", "loans", type_="foreignkey")
    op.drop_index("ix_loans_borrower_id", table_name="loans")
    op.drop_column("loans", "borrower_id")
