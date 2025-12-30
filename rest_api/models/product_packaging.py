# -*- coding: utf-8 -*-
###################################################################################

# Author       :  Sayooj t k
# Copyright(c) :  2023-Present Zinfog Codelabs Pvt Ltd (<https://www.zinfog.com>).
# License      :  LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

# This program is free software:
# you can modify it under the terms of the GNU Lesser General Public License (LGPL) as
# published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

###################################################################################
from odoo import fields, models


class ProductPacking(models.Model):
    _inherit = "product.packaging"

    sale_qty = fields.Integer(string='Sale Quantity', default=0, store=True)
    sale_package = fields.Boolean(string="Sale package", default=False)

    def auto_package_unlink(self):
        for rec in self.search([('sale_qty','=', 0)]):
            rec.unlink()
