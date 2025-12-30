from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    source_location_id = fields.Many2one('stock.location', string='Source Location')
