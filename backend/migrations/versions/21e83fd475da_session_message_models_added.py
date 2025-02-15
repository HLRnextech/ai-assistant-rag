"""session, message models added

Revision ID: 21e83fd475da
Revises: d7b1cfcc04f2
Create Date: 2024-05-26 13:45:33.719421

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '21e83fd475da'
down_revision = 'd7b1cfcc04f2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('session',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('guid', sa.String(length=32), nullable=False),
    sa.Column('user_guid', sa.String(length=32), nullable=False),
    sa.Column('status', sa.Enum('ACTIVE', 'INACTIVE', name='sessionstatus'), nullable=False),
    sa.Column('feedback', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('last_active_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('ended_at', sa.DateTime(), nullable=True),
    sa.Column('bot_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['bot_id'], ['bot.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_session_guid'), ['guid'], unique=True)

    op.create_table('message',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('guid', sa.String(length=32), nullable=False),
    sa.Column('role', sa.Enum('HUMAN', 'BOT', name='messagerole'), nullable=False),
    sa.Column('type', sa.String(length=50), nullable=True),
    sa.Column('content', sa.String(), nullable=False),
    sa.Column('feedback', sa.Enum('POSITIVE', 'NEGATIVE', 'NEUTRAL', name='messagefeedback'), nullable=True),
    sa.Column('error', sa.String(length=500), nullable=True),
    sa.Column('cost', sa.Float(), nullable=True),
    sa.Column('num_tokens', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.Column('session_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['session_id'], ['session.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_message_guid'), ['guid'], unique=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('message', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_message_guid'))

    op.drop_table('message')
    with op.batch_alter_table('session', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_session_guid'))

    op.drop_table('session')
    # ### end Alembic commands ###
