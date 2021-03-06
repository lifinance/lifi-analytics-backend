"""empty message

Revision ID: f61ef505c121
Revises: 
Create Date: 2021-10-08 16:21:19.842116

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f61ef505c121'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('txns',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('amount', sa.String(), nullable=True),
    sa.Column('expiry', sa.String(), nullable=True),
    sa.Column('fulfillTimestamp', sa.String(), nullable=True),
    sa.Column('subgraphId', sa.String(), nullable=True),
    sa.Column('preparedBlockNumber', sa.String(), nullable=True),
    sa.Column('preparedTimestamp', sa.String(), nullable=True),
    sa.Column('receivingAssetId', sa.String(), nullable=True),
    sa.Column('sendingAssetId', sa.String(), nullable=True),
    sa.Column('status', sa.String(), nullable=True),
    sa.Column('user', sa.String(), nullable=True),
    sa.Column('chain', sa.String(), nullable=True),
    sa.Column('txn_type', sa.String(), nullable=True),
    sa.Column('asset_movement', sa.String(), nullable=True),
    sa.Column('asset_token', sa.String(), nullable=True),
    sa.Column('decimals', sa.Integer(), nullable=True),
    sa.Column('dollar_amount', sa.Float(), nullable=True),
    sa.Column('time_prepared', sa.DateTime(), nullable=True),
    sa.Column('time_fulfilled', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.alter_column('asset_movement', 'id',
               existing_type=sa.BIGINT(),
               nullable=False,
               autoincrement=True)
    op.drop_index('ix_asset_movement_id', table_name='asset_movement')
    op.alter_column('bridges_tvl', 'id',
               existing_type=sa.BIGINT(),
               nullable=False,
               autoincrement=True)
    op.drop_index('ix_bridges_tvl_id', table_name='bridges_tvl')
    op.alter_column('date_volume', 'id',
               existing_type=sa.BIGINT(),
               nullable=False,
               autoincrement=True)
    op.drop_index('ix_date_volume_id', table_name='date_volume')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('ix_date_volume_id', 'date_volume', ['id'], unique=False)
    op.alter_column('date_volume', 'id',
               existing_type=sa.BIGINT(),
               nullable=True,
               autoincrement=True)
    op.create_index('ix_bridges_tvl_id', 'bridges_tvl', ['id'], unique=False)
    op.alter_column('bridges_tvl', 'id',
               existing_type=sa.BIGINT(),
               nullable=True,
               autoincrement=True)
    op.create_index('ix_asset_movement_id', 'asset_movement', ['id'], unique=False)
    op.alter_column('asset_movement', 'id',
               existing_type=sa.BIGINT(),
               nullable=True,
               autoincrement=True)
    op.drop_table('txns')
    # ### end Alembic commands ###
