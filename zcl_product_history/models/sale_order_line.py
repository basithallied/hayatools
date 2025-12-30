# -*- coding: utf-8 -*-
from odoo import models


class SaleOrderLine(models.Model):
    """ Model is inherited to add a new function to order line """
    _inherit = 'sale.order.line'

    def get_product_history_data(self):
        """Returns the product history data from stock moves ordered by date"""
        values_sale = []
        values_purchase = []

        # Fetch stock moves for the current product ordered by date
        domain = [
            '|',
            ('purchase_line_id', '!=', None), ('sale_line_id', '!=', None),
            ('product_id', '=', self.product_id.id),('origin_returned_move_id', '=', None),
            ('state', '=', 'done'),
        ]

        stock_moves = self.env['stock.move'].search(domain, order='date asc')

        for move in stock_moves:

            if move.sale_line_id and move.sale_line_id.order_id.partner_id.id == self.order_id.partner_id.id:
                history_sale = {
                    'move_id': move.id,
                    'reference': str(move.sale_line_id.order_id.name),
                    'history_date': move.date,
                    'history_qty': -(move.product_uom_qty),
                    'remaining_qty': move.remaining_qty,
                    'history_total': (move.product_uom_qty * (move.sale_line_id.price_unit)),
                    'sale_order_id': move.sale_line_id.order_id.id,
                    'history_price': move.sale_line_id.price_unit
                }
                values_sale.append((0, 0, history_sale))
            elif  move.purchase_line_id and  move.purchase_line_id.partner_id.id == self.order_id.partner_id.id:
                history_purchase = {
                    'move_id': move.id,
                    'reference': str(move.purchase_line_id.order_id.name),
                    'history_date': move.date,
                    'history_qty': move.product_uom_qty,
                    'remaining_qty': move.remaining_qty,
                    'history_total': move.product_uom_qty * (move.purchase_line_id.price_unit),
                    'purchase_order_id': move.purchase_line_id.order_id.id,
                    'history_price': move.purchase_line_id.price_unit
                }
                values_purchase.append((0, 0, history_purchase))


        # Create history record
        history_id = self.env['product.sale.order.history'].create({
            'product_id': self.product_id.id,
            'partner_id': self.order_id.partner_id.id,
            'product_sale_history_ids': values_sale,
            'product_purchase_history_ids': values_purchase,
        })

        return {
            'name': 'Product Stock Movement History',
            'view_mode': 'form',
            'res_model': 'product.sale.order.history',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': history_id.id
        }



