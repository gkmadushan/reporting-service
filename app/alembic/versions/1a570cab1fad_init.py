"""init

Revision ID: 1a570cab1fad
Revises: 
Create Date: 2021-09-08 00:34:05.615398

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql




# revision identifiers, used by Alembic.
revision = '1a570cab1fad'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('email', sa.String, nullable=False)
    )    


def downgrade():
    op.drop_table('user')
