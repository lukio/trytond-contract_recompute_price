# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import contract


def register():
    Pool.register(
        contract.ContractLine,
        contract.RecomputePriceStart,
        module='contract_recompute_price', type_='model')
    Pool.register(
        contract.RecomputePrice,
        module='contract_recompute_price', type_='wizard')
