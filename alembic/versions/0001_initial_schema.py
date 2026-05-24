"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-24
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "urls",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("original_url", sa.String(), nullable=False),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_urls_id", "urls", ["id"])
    op.create_index("ix_urls_code", "urls", ["code"], unique=True)


def downgrade():
    op.drop_index("ix_urls_code", table_name="urls")
    op.drop_index("ix_urls_id", table_name="urls")
    op.drop_table("urls")
