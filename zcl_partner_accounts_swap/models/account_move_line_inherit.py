# -- coding: utf-8 --
###################################################################################

# Author       :  Sayooj t k
# Copyright(c) :  2023-Present Zinfog Codelabs Pvt Ltd (<https://www.zinfog.com>).
# License      :  LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

# This program is free software:
# you can modify it under the terms of the GNU Lesser General Public License (LGPL) as
# published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
############################################################

from odoo import models, fields,api, _
from odoo.exceptions import UserError


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'


    @api.constrains('account_id', 'display_type')
    def _check_payable_receivable(self):
        """ Inherit base function and skip constrains checking"""
        pass
        # for line in self:
        #     account_type = line.account_id.account_type
        #     if line.move_id.is_sale_document(include_receipts=True):
        #         if (line.display_type == 'payment_term') ^ (account_type == 'asset_receivable'):
        #             raise UserError(_("Any journal item on a receivable account must have a due date and vice versa."))
            # if line.move_id.is_purchase_document(include_receipts=True):
            #     if (line.display_type == 'payment_term') ^ (account_type == 'liability_payable'):
            #         raise UserError(_("Any journal item on a payable account must have a due date and vice versa."))

