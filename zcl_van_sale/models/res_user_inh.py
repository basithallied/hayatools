# -*- coding: utf-8 -*-

from odoo import models,fields,api

class ResUser(models.Model):
    _inherit = 'res.users'

    allowed_location = fields.Many2one('stock.location', 'Allowed Location')
    is_van_user = fields.Boolean('Van user', default=False)