# This file is a part of the AnyBlok / Sale project
#
#    Copyright (C) 2018 Franck Bret <franckbret@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file,You can
# obtain one at http://mozilla.org/MPL/2.0/.
# -*- coding: utf-8 -*-

from anyblok.tests.testcase import BlokTestCase
from anyblok_mixins.workflow.exceptions import WorkFlowException

from decimal import Decimal as D

from marshmallow.exceptions import ValidationError


class TestSaleOrderModel(BlokTestCase):
    """Test Sale.Order model"""

    def test_create_sale_order(self):
        so = self.registry.Sale.Order.create(
                                channel="WEBSITE",
                                code="SO-TEST-000001"
                            )
        self.assertEqual(so.state, 'draft')

    def test_create_empty_sale_order_fail_validation(self):
        with self.assertRaises(ValidationError) as ctx:
            self.registry.Sale.Order.create()

        self.assertTrue('code' in ctx.exception.messages.keys())
        self.assertEqual(
            ctx.exception.messages.get('code'),
            ['Missing data for required field.']
        )
        self.assertTrue('channel' in ctx.exception.messages.keys())
        self.assertEqual(
            ctx.exception.messages.get('channel'),
            ['Missing data for required field.']
        )

    def test_create_sale_order_fail_validation(self):
        with self.assertRaises(ValidationError) as ctx:
            self.registry.Sale.Order.create(
                                code="SO-TEST-000001"
                            )

        self.assertTrue('channel' in ctx.exception.messages.keys())
        self.assertEqual(
            ctx.exception.messages.get('channel'),
            ['Missing data for required field.']
        )

    def test_sale_order_state_transition_to_done(self):
        so = self.registry.Sale.Order.create(
                                channel="WEBSITE",
                                code="SO-TEST-000001"
                            )

        self.assertEqual(so.state, 'draft')
        so.state = 'quotation'
        self.registry.flush()  # flush to update state on db
        self.assertEqual(so.state, 'quotation')
        so.state = 'order'
        self.registry.flush()
        self.assertEqual(so.state, 'order')
        self.registry.flush()

    def test_sale_order_state_transition_to_cancelled(self):
        so = self.registry.Sale.Order.create(
                                channel="WEBSITE",
                                code="SO-TEST-000001"
                            )
        self.assertEqual(so.state, 'draft')
        so.state = 'quotation'
        self.registry.flush()
        self.assertEqual(so.state, 'quotation')
        so.state = 'cancelled'
        self.registry.flush()
        self.assertEqual(so.state, 'cancelled')

    def test_sale_order_transition_quotation_order_failed(self):
        so = self.registry.Sale.Order.create(
                                channel="WEBSITE",
                                code="SO-TEST-000001"
                            )
        so.state = 'quotation'
        self.registry.flush()
        so.state = 'order'
        self.registry.flush()

        with self.assertRaises(WorkFlowException) as ctx:
            so.state = 'draft'
            self.registry.flush()

        self.assertEqual(
            ctx.exception.args[0],
            "No rules found to change state from 'order' to 'draft'")


class TestSaleOrderLineModel(BlokTestCase):
    """ Test Sale.Order.Line model"""

    def test_compute_sale_order_line_unit(self):
        so = self.registry.Sale.Order.create(
                     channel="WEBSITE",
                     code="SO-TEST-000001"
                     )

        self.assertEqual(so.state, 'draft')
        product = self.registry.Product.Item.insert(code="plop", name="plop")

        line1 = self.registry.Sale.Order.Line.create(
                    order=so,
                    item=product,
                    quantity=1,
                    unit_price=100,
                    unit_tax=20,
                    properties=dict()
                    )

        line2 = self.registry.Sale.Order.Line.create(
                    order=so,
                    item=product,
                    quantity=1,
                    unit_price_untaxed=83.33,
                    unit_tax=20,
                    properties=dict()
                    )

        self.assertEqual(line1.unit_price_untaxed, line2.unit_price_untaxed)
        self.assertEqual(line1.unit_price, line2.unit_price)

        self.assertEqual(line1.unit_price_untaxed, line1.amount_untaxed)
        self.assertEqual(line1.unit_price, line1.amount_total)

        self.assertEqual(line2.unit_price_untaxed, line2.amount_untaxed)
        self.assertEqual(line2.unit_price, line2.amount_total)

        line3 = self.registry.Sale.Order.Line.create(
                    order=so,
                    item=product,
                    quantity=1,
                    unit_price=23.14,
                    unit_tax=2.1,
                    properties=dict()
                    )

        line4 = self.registry.Sale.Order.Line.create(
                    order=so,
                    item=product,
                    quantity=1,
                    unit_price_untaxed=22.66,
                    unit_tax=2.1,
                    properties=dict()
                    )

        self.assertEqual(line3.unit_price_untaxed, line4.unit_price_untaxed)
        self.assertEqual(line3.unit_price, line4.unit_price)

        self.assertEqual(line3.unit_price_untaxed, line3.amount_untaxed)
        self.assertEqual(line3.unit_price, line3.amount_total)

        self.assertEqual(line4.unit_price_untaxed, line4.amount_untaxed)
        self.assertEqual(line4.unit_price, line4.amount_total)

        line5 = self.registry.Sale.Order.Line.create(
                    order=so,
                    item=product,
                    quantity=1,
                    unit_price=100,
                    unit_price_untaxed=83.33,
                    unit_tax=20,
                    properties=dict()
                    )

        self.assertEqual(line5.unit_price_untaxed, D('83.33'))

        self.assertEqual(line5.unit_price_untaxed, line5.amount_untaxed)
        self.assertEqual(line5.unit_price, line5.amount_total)

        self.assertEqual(so.amount_untaxed, D('0'))
        self.assertEqual(so.amount_tax, D('0'))
        self.assertEqual(so.amount_total, D('0'))
        so.compute()
        self.assertEqual(so.amount_untaxed, D('295.31'))
        self.assertEqual(so.amount_tax, D('50.97'))
        self.assertEqual(so.amount_total, D('346.28'))
