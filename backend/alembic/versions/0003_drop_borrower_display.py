"""Drop loans.borrower_display_name

Revision ID: 0003_drop_borrower_display
Revises: 0002_loans_borrower_id
Create Date: 2025-11-27
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_drop_borrower_display"
down_revision = "0002_loans_borrower_id"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_column("loans", "borrower_display_name")


def downgrade():
    op.add_column(
        "loans",
        sa.Column("borrower_display_name", sa.String(length=200), nullable=True),
    )
