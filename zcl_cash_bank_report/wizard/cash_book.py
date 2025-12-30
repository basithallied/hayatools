# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from datetime import date


class AccountCashBookReport(models.TransientModel):
    _name = "account.cashbook.report.wizard"
    _description = "Cash Book Report Wizard"

    date_from = fields.Date(string='Start Date', default=date.today(), required=True)
    date_to = fields.Date(string='End Date', default=date.today(), required=True)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, domain="[('type', '=', 'cash')]",
                                   default=lambda self: self.env['account.journal'].search([('type', '=', 'cash')]))
    account_ids = fields.Many2many('account.account', string='Accounts', required=True,
                                   domain="[('account_type', '=', 'asset_cash')]")

    display_account = fields.Selection(
        [('all', 'All'), ('movement', 'With movements'),
         ('not_zero', 'With balance is not equal to 0')],
        string='Display Accounts', required=True, default='movement')

    def _build_comparison_context(self, data):
        result = {}
        result['journal_ids'] = 'journal_ids' in data['form'] and data['form'][
            'journal_ids'] or False
        result['state'] = 'target_move' in data['form'] and data['form'][
            'target_move'] or ''
        result['date_from'] = data['form']['date_from'] or False
        result['date_to'] = data['form']['date_to'] or False
        result['strict_range'] = True if result['date_from'] else False
        result['account_ids'] = 'account_ids' in data['form'] and data['form'][
            'account_ids'] or False
        return result

    def check_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'journal_ids': self.journal_ids.ids,
            'account_ids': self.account_ids.ids,
        }
        return self.env.ref('zcl_cash_bank_report.action_report_cash_book_action').report_action(self, data=data)



