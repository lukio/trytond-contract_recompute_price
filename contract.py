# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal

from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.wizard import Button, StateTransition, StateView, Wizard
from trytond.modules.product.product import price_digits

__all__ = ['ContractLine', 'RecomputePriceStart', 'RecomputePrice']


class ContractLine:
    __name__ = 'contract.line'
    __metaclass__ = PoolMeta

    def _recompute_price_by_service(self):
        digits = self.__class__.unit_price.digits[1]
        new_unit_price = (self.service.product.list_price).quantize(
            Decimal(str(10 ** -digits)))
        values = {
            'unit_price': new_unit_price,
            }
        # Compatibility with contract_discount module
        if hasattr(self, 'gross_unit_price'):
            digits = self.__class__.gross_unit_price.digits[1]
            new_gross_unit_price = (self.service.product.list_price).quantize(
                Decimal(str(10 ** -digits)))
            values['gross_unit_price'] = new_gross_unit_price
        return values

    @classmethod
    def recompute_price_by_product_price(cls, lines):
        to_write = []
        for line in lines:
            new_values = line._recompute_price_by_service()
            if new_values:
                to_write.extend(([line], new_values))
        if to_write:
            cls.write(*to_write)


class RecomputePriceStart(ModelView):
    'Recompute Price - Start'
    __name__ = 'contract.recompute_price.start'

    method = fields.Selection([
            ('product_price', 'By Product price'),
            ('fixed_amount', 'Fixed Amount'),
            ], 'Recompute Method', required=True)
    list_price = fields.Numeric('List Price', digits=price_digits,
        states={
            'invisible': Eval('method') != 'fixed_amount',
            'required': Eval('method') == 'fixed_amount',
            },
        depends=['method'])


class RecomputePrice(Wizard):
    'Recompute Product List Price'
    __name__ = 'contract.recompute_price'

    start = StateView('contract.recompute_price.start',
        'contract_recompute_price.recompute_price_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Recompute', 'compute', 'tryton-ok', default=True),
            ])
    compute = StateTransition()

    def get_additional_args(self):
        method_name = 'get_additional_args_%s' % self.start.method
        if not hasattr(self, method_name):
            return {}
        return getattr(self, method_name)()

    def get_additional_args_fixed_amount(self):
        return {
            'list_price': self.start.list_price,
            }

    def transition_compute(self):
        pool = Pool()
        ContractLine = pool.get('contract.line')

        method_name = 'recompute_price_by_%s' % self.start.method
        method = getattr(ContractLine, method_name)
        if method:
            method(ContractLine.search([('contract_state', '=', 'confirmed')]),
                **self.get_additional_args())
        return 'end'
