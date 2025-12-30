from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'

    arabic_name = fields.Char(string="Arabic Name")
