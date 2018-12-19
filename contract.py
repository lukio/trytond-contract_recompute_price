# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import Decimal, ROUND_HALF_UP

from trytond.model import ModelView, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.wizard import Button, StateTransition, StateView, Wizard
from trytond.modules.product.product import price_digits

__all__ = ['ContractLine', 'RecomputePriceStart', 'RecomputePrice']


class ContractLine:
    __name__ = 'contract.line'
    __metaclass__ = PoolMeta

    @classmethod
    def _recompute_price_by_fixed_amount(cls, line, new_unit_price):
        values = {
            'unit_price': new_unit_price,
            }
        # Compatibility with contract_discount module
        if hasattr(line, 'gross_unit_price'):
            values['gross_unit_price'] = new_unit_price
        return values

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
    def _recompute_price_by_factor(cls, line, factor):
        new_list_price = (line.unit_price * factor).quantize(
            Decimal('1.'), rounding=ROUND_HALF_UP)
        values = {
            'unit_price': new_list_price,
            }
        # Compatibility with contract_discount module
        if hasattr(line, 'gross_unit_price'):
            new_gross_unit_price = (line.unit_price * factor).quantize(
                Decimal('1.'), rounding=ROUND_HALF_UP)
            values['gross_unit_price'] = new_gross_unit_price
        return values

    @classmethod
    def recompute_price_by_percentage(cls, lines, percentage):
        to_write = []
        factor = Decimal(1) + Decimal(percentage)
        for line in lines:
            new_values = cls._recompute_price_by_factor(line, factor)
            if new_values:
                to_write.extend(([line], new_values))
        if to_write:
            cls.write(*to_write)

    @classmethod
    def recompute_price_by_product_price(cls, lines):
        to_write = []
        for line in lines:
            new_values = line._recompute_price_by_service()
            if new_values:
                to_write.extend(([line], new_values))
        if to_write:
            cls.write(*to_write)

        # Compatibility with contract_discount module
        to_write = []
        for line in lines:
            if hasattr(line, 'gross_unit_price'):
                old_unit_price = line.unit_price
                line.update_prices()
                if old_unit_price != line.unit_price:
                    to_write.append(line)
        if to_write:
            cls.save(to_write)

    @classmethod
    def recompute_price_by_fixed_amount(cls, lines, unit_price):
        to_write = []
        for line in lines:
            new_values = line._recompute_price_by_fixed_amount(line, unit_price)
            if new_values:
                to_write.extend(([line], new_values))
        if to_write:
            cls.write(*to_write)

        # Compatibility with contract_discount module
        to_write = []
        for line in lines:
            if hasattr(line, 'gross_unit_price'):
                old_unit_price = line.unit_price
                line.update_prices()
                if old_unit_price != line.unit_price:
                    to_write.append(line)
        if to_write:
            cls.save(to_write)


class RecomputePriceStart(ModelView):
    'Recompute Price - Start'
    __name__ = 'contract.recompute_price.start'

    method = fields.Selection([
            ('percentage', 'By Percentage'),
            ('product_price', 'By Product price'),
            ('fixed_amount', 'Fixed Amount'),
            ], 'Recompute Method', required=True)
    unit_price = fields.Numeric('Unit Price', digits=price_digits,
        states={
            'invisible': Eval('method') != 'fixed_amount',
            'required': Eval('method') == 'fixed_amount',
            },
        depends=['method'])
    percentage = fields.Float('Percentage', digits=(16, 4),
        states={
            'invisible': Eval('method') != 'percentage',
            'required': Eval('method') == 'percentage',
            },
        depends=['method'])
    categories = fields.Many2Many('product.category', None, None, 'Categories',
        states={
            'invisible': Eval('method') != 'percentage',
            'required': Eval('method') == 'percentage',
            }, depends=['method'])
    services = fields.Many2Many('contract.service', None, None, 'Services',
        states={
            'invisible': Eval('method') != 'fixed_amount',
            'required': Eval('method') == 'fixed_amount',
            }, depends=['method'])

    @staticmethod
    def default_method():
        return 'percentage'


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
            'unit_price': self.start.unit_price,
            }

    def get_additional_args_percentage(self):
        return {
            'percentage': self.start.percentage,
            }

    def transition_compute(self):
        pool = Pool()
        ContractLine = pool.get('contract.line')

        method_name = 'recompute_price_by_%s' % self.start.method
        method = getattr(ContractLine, method_name)
        if method:
            domain = [('contract_state', '=', 'confirmed')]
            if self.start.method == 'percentage' and self.start.categories:
                categories = [cat.id for cat in list(self.start.categories)]
                domain.append(('service.product.category', 'in', categories))
            if self.start.method == 'fixed_amount' and self.start.services:
                services = [s.id for s in list(self.start.services)]
                domain.append(('service', 'in', services))
            method(ContractLine.search(domain),
                **self.get_additional_args())
        return 'end'
