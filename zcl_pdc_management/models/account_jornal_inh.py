# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.osv.expression import AND
from odoo.fields import Command


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.depends('outbound_payment_method_line_ids', 'inbound_payment_method_line_ids')
    def _compute_available_payment_method_ids(self):
        # Call the super to preserve default behavior
        super()._compute_available_payment_method_ids()

        # 💡 Your custom logic goes here
        for journal in self.filtered(lambda j: j.type in ('bank', 'cash')):
            # For example: force-add a method with code `pdc_in` if not already included
            pdc_method = self.env['account.payment.method'].search([('code', '=', 'pdc_in')], limit=1)
            if pdc_method and pdc_method not in journal.available_payment_method_ids:
                journal.available_payment_method_ids = [Command.link(
                    pdc_method.id)] + journal.available_payment_method_ids.ids
            pdc_method_out = self.env['account.payment.method'].search([('code', '=', 'pdc_out')], limit=1)
            if pdc_method_out and pdc_method_out not in journal.available_payment_method_ids:
                journal.available_payment_method_ids = [Command.link(
                    pdc_method_out.id)] + journal.available_payment_method_ids.ids



