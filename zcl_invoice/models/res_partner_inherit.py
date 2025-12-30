# -- coding: utf-8 --
###################################################################################

# Author       :  Sayooj t k
# Copyright(c) :  2023-Present Zinfog Codelabs Pvt Ltd (<https://www.zinfog.com>).
# License      :  LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

# This program is free software:
# you can modify it under the terms of the GNU Lesser General Public License (LGPL) as
# published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
############################################################

from odoo import models, fields,api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_and_vendor_true = fields.Boolean(string='Customer & Vendor', default=False)

    pay_receive_account = fields.Many2one('account.account', company_dependent=True,
                                                  string="Payable & Receivable Account")
    @api.onchange('customer_and_vendor_true')
    def _onchange_customer_and_vendor_true(self):
        if self.customer_and_vendor_true:
            if self.supplier_rank:
                self.customer_rank =1
            elif self.customer_rank:
                self.supplier_rank =1


    supplier_code = fields.Char('Supplier Code')
    customer_code = fields.Char('Customer Code')
    cr_number = fields.Char('CR Number')

    def action_test_button(self):
        return self.env.ref('zcl_invoice.action_customer_overdue_custom_report').report_action(self.id, data=None)



    user_id = fields.Many2one(
        'res.users', string='Salesperson',
        compute='_compute_user_id',
        precompute=True,  # avoid queries post-create
        readonly=False, store=True,
        default=lambda self: self.env.uid,
        help='The internal user in charge of this contact.')