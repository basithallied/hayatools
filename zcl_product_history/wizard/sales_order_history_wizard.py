# -*- coding: utf-8 -*-
from odoo import fields, models, api

class ProductSaleOrderHistory(models.TransientModel):
    _name = 'product.sale.order.history'
    _description = 'Product Sale Order History'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    partner_id = fields.Many2one('res.partner', string="Partner", required=True)
    product_sale_history_ids = fields.One2many('product.sale.history.line', 'order_line_id', string='Product Sale Price History')
    product_purchase_history_ids = fields.One2many('product.sale.history.line', 'purchase_order_line_id', string='Product Purchase Price History')
