# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ProductProduct(models.Model):
    _inherit = 'product.template'

    is_import = fields.Boolean(string="Import", Default=False)