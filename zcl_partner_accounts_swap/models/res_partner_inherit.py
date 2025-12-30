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



class ResPartner(models.Model):
    _inherit = 'res.partner'


    partner_type = fields.Selection(selection=[
            ('customer', 'Customer'),
            ('vendor', 'Vendor'),
            ('other', 'Other'),
        ], string="Type")

    @api.onchange('partner_type')
    def _onchange_of_partner_type(self):
        if self.partner_type == 'other':
            other_receive_account_id = self.env['ir.config_parameter'].sudo().get_param(
                'zcl_partner_accounts_swap.other_receive_account')
            other_payable_account_id = self.env['ir.config_parameter'].sudo().get_param(
                'zcl_partner_accounts_swap.other_payable_account')

            if other_receive_account_id:
                account_receivable = self.env['account.account'].browse(int(other_receive_account_id))
                print('account_receivable',account_receivable.name)
                self.property_account_receivable_id = account_receivable

            if other_payable_account_id:
                account_payable = self.env['account.account'].browse(int(other_payable_account_id))
                self.property_account_payable_id = account_payable

        elif self.partner_type == 'customer':
            other_receive_account_id = self.env['ir.config_parameter'].sudo().get_param(
                'zcl_partner_accounts_swap.customer_receive_account')
            other_payable_account_id = self.env['ir.config_parameter'].sudo().get_param(
                'zcl_partner_accounts_swap.customer_payable_account')

            if other_receive_account_id:
                account_receivable = self.env['account.account'].browse(int(other_receive_account_id))
                print('account_receivable', account_receivable.name)
                self.property_account_receivable_id = account_receivable

            if other_payable_account_id:
                account_payable = self.env['account.account'].browse(int(other_payable_account_id))
                self.property_account_payable_id = account_payable
        elif self.partner_type == 'vendor':
            other_receive_account_id = self.env['ir.config_parameter'].sudo().get_param(
                'zcl_partner_accounts_swap.vendor_receive_account')
            other_payable_account_id = self.env['ir.config_parameter'].sudo().get_param(
                'zcl_partner_accounts_swap.vendor_payable_account')

            if other_receive_account_id:
                account_receivable = self.env['account.account'].browse(int(other_receive_account_id))
                print('account_receivable', account_receivable.name)
                self.property_account_receivable_id = account_receivable

            if other_payable_account_id:
                account_payable = self.env['account.account'].browse(int(other_payable_account_id))
                self.property_account_payable_id = account_payable