# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ProductSaleHistoryLine(models.TransientModel):
    _name = 'product.sale.history.line'
    _rec_name = 'reference'

    reference = fields.Char('Reference')
    order_line_id = fields.Many2one('product.sale.order.history', string='Order Line')
    purchase_order_line_id = fields.Many2one('product.sale.order.history', string='Purchase Order Line')
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")
    move_id = fields.Many2one('stock.move', string="Stock Move")
    history_date = fields.Date(string="Date")
    history_price = fields.Char(string='Unit Price')
    history_total = fields.Float(string='Total Price')
    history_qty = fields.Float(string='Quantity')
    remaining_qty = fields.Float(string='Remaining Qty')
    type = fields.Selection([('sale', 'Sale'), ('purchase', 'Purchase')], string="Type")

