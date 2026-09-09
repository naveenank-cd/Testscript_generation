"""Add project application_url, auth_config, latest_crawl_id, and crawl_knowledge.

Revision ID: 0003
Revises: 0002
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("application_url", sa.String(2048), nullable=True))
    op.add_column("projects", sa.Column("auth_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("projects", sa.Column("latest_crawl_id", sa.String(255), nullable=True))
    op.add_column("projects", sa.Column("crawl_knowledge", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade():
    op.drop_column("projects", "crawl_knowledge")
    op.drop_column("projects", "latest_crawl_id")
    op.drop_column("projects", "auth_config")
    op.drop_column("projects", "application_url")
