from odoo import models, fields, _ 

class StockLocation(models.Model):
    _inherit = 'stock.location'

    supervisor_id = fields.Many2one('res.users', string="Supervisor")
    picker_ids = fields.Many2many('res.users', string="Pickers")