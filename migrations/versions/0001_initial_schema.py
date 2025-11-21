\"\"\"Initial schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2025-11-20 23:04:00.000000
\"\"\"

from alembic import op

from bugbridge.database.schema import SCHEMA_SQL

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    \"\"\"Apply initial schema.\"\"\"
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    \"\"\"Drop all tables created by initial schema.\"\"\"
    op.execute(
        \"\"\"\n        DROP TABLE IF EXISTS reports CASCADE;\n        DROP TABLE IF EXISTS notifications CASCADE;\n        DROP TABLE IF EXISTS workflow_states CASCADE;\n        DROP TABLE IF EXISTS jira_tickets CASCADE;\n        DROP TABLE IF EXISTS analysis_results CASCADE;\n        DROP TABLE IF EXISTS feedback_posts CASCADE;\n        \"\"\"\n    )

