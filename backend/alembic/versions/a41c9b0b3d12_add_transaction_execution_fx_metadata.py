"""add transaction execution and currency conversion metadata"""

import sqlalchemy as sa

from alembic import op

revision = "a41c9b0b3d12"
down_revision = "52ff5305a742"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("input_currency", sa.String(length=3), nullable=True))
        batch_op.add_column(sa.Column("input_price", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("input_fees", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("input_taxes", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("input_to_asset_rate", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("conversion_provider", sa.String(length=64), nullable=True))
        batch_op.add_column(
            sa.Column("conversion_effective_at", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(sa.Column("conversion_precision", sa.String(length=16), nullable=True))
    op.execute(
        "UPDATE transactions SET input_currency = currency, input_price = price, "
        "input_fees = fees, input_taxes = taxes, input_to_asset_rate = '1', "
        "conversion_provider = 'identity', conversion_precision = 'exact'"
    )


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_column("conversion_precision")
        batch_op.drop_column("conversion_effective_at")
        batch_op.drop_column("conversion_provider")
        batch_op.drop_column("input_to_asset_rate")
        batch_op.drop_column("input_taxes")
        batch_op.drop_column("input_fees")
        batch_op.drop_column("input_price")
        batch_op.drop_column("input_currency")
        batch_op.drop_column("executed_at")
