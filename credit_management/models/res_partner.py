from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    days_limit = fields.Integer(string="Days")
