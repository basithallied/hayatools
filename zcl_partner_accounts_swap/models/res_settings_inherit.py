# -*- coding: utf-8 -*-
###################################################################################

# Author       :  Sayooj t k
# Copyright(c) :  2023-Present Zinfog Codelabs Pvt Ltd (<https://www.zinfog.com>).
# License      :  LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

# This program is free software:
# you can modify it under the terms of the GNU Lesser General Public License (LGPL) as
# published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

###################################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    customer_receive_account = fields.Many2one(
        'account.account',
        string="Account Receivable",
        config_parameter='zcl_partner_accounts_swap.customer_receive_account'
    )
    customer_payable_account = fields.Many2one(
        'account.account',
        string="Account Payable",
        config_parameter='zcl_partner_accounts_swap.customer_payable_account')

    vendor_receive_account = fields.Many2one(
        'account.account',
        string="Account Receivable",
        config_parameter='zcl_partner_accounts_swap.vendor_receive_account'
    )
    vendor_payable_account = fields.Many2one(
        'account.account',
        string="Account Payable",
        config_parameter='zcl_partner_accounts_swap.vendor_payable_account')

    other_receive_account = fields.Many2one(
        'account.account',
        string="Account Receivable",
        config_parameter='zcl_partner_accounts_swap.other_receive_account'
    )
    other_payable_account = fields.Many2one(
        'account.account',
        string="Account Payable",
        config_parameter='zcl_partner_accounts_swap.other_payable_account')
    #
    # @api.model
    # def get_values(self):
    #     res = super(ResConfigSettings, self).get_values()
    #
    #     # Fetch default receivable and payable accounts for the current company
    #     company = self.env.company
    #     partner = self.env['res.partner'].search([('company_id', '=', company.id)], limit=1, order="id asc")
    #
    #     # Fallback to global partner if no company-specific partner exists
    #     if not partner:
    #         partner = self.env['res.partner'].search([], limit=1, order="id asc")
    #
    #     receivable_account = partner.property_account_receivable_id or company.chart_template_id.property_account_receivable_id
    #     payable_account = partner.property_account_payable_id or company.chart_template_id.property_account_payable_id
    #
    #     res.update({
    #         'customer_receive_account': receivable_account.id if receivable_account else False,
    #         'vendor_receive_account': receivable_account.id if receivable_account else False,
    #         'customer_payable_account': payable_account.id if payable_account else False,
    #         'vendor_payable_account': payable_account.id if payable_account else False,
    #     })
    #
    #     return res
    #
    # def set_values(self):
    #     super(ResConfigSettings, self).set_values()