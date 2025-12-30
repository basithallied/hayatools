# -- coding: utf-8 --

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    auto_create_lot = fields.Boolean()
