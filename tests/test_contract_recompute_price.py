# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest

from trytond.tests.test_tryton import suite as test_suite
from trytond.tests.test_tryton import ModuleTestCase


class TestContractRecomputePriceCase(ModuleTestCase):
    'Test Contract Recompute Price module'
    module = 'contract_recompute_price'


def suite():
    suite = test_suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
            TestContractRecomputePriceCase))
    return suite
