import time
from odoo import api, models, _
from odoo.exceptions import UserError
from collections import defaultdict



class ReportCashBook(models.AbstractModel):
    _name = 'report.zcl_cash_bank_report.report_cashbook_template'
    _description = 'Cash Book Report'

    def _get_lines(self, date_from, date_to, journal_ids, account_ids):
        domain = [
            ('date', '>=', date_from),
            ('date', '<=', date_to),
            ('state', 'in', ['paid', 'expense_done', 'in_process', 'internal_transfer']),
            '|', ('journal_id.type', '=', 'cash'), ('destination_journal_id.type', '=', 'cash'),
            ('is_pdc', '=', False),
        ]

        payments = self.env['account.payment'].search(domain, order='id asc')
        # print('payments',payments)
        grouped_data = defaultdict(lambda: {
            'account_name': '',
            'account_code': '',
            'debit': 0.0,
            'credit': 0.0,
            'balance': 0.0,
            'lines': []
        })

        AccountMoveLine = self.env['account.move.line']

        for rec in account_ids:
            account = self.env['account.account'].search([('id', '=', rec)], limit=1)
            if account:
                initial_domain = [
                    ('account_id', '=', account.id),
                    ('date', '<', date_from),
                    ('move_id.state', '=', 'posted'),
                ]
                initial_balance = sum(AccountMoveLine.search(initial_domain).mapped(lambda l: l.debit - l.credit))
                initial_debit = sum(AccountMoveLine.search(initial_domain).mapped(lambda l: l.debit))
                initial_credit = sum(AccountMoveLine.search(initial_domain).mapped(lambda l: l.credit))

                grouped_data[account.id]['account_name'] = account.name
                grouped_data[account.id]['account_code'] = account.code
                grouped_data[account.id]['initial_balance'] = initial_balance
                grouped_data[account.id]['initial_debit'] = initial_debit
                grouped_data[account.id]['initial_credit'] = initial_credit

        running_balance = 0.0

        list_id = []
        for rec in payments:
            journal = rec.journal_id
            if rec.move_id:
                if rec.move_id.state != 'posted':
                    continue
                for line in rec.move_id.line_ids:
                    if line.account_id.id not in account_ids:
                        continue
                    list_id.append(line.id)

                    debit = line.debit
                    credit = line.credit
                    running_balance += debit - credit

                    account_key = line.account_id.id
                    grouped_data[account_key]['account_name'] = line.account_id.name
                    grouped_data[account_key]['account_code'] = line.account_id.code
                    grouped_data[account_key]['debit'] += debit
                    grouped_data[account_key]['credit'] += credit
                    grouped_data[account_key]['balance'] += debit - credit

                    grouped_data[account_key]['lines'].append({
                        'date': line.date,
                        'journal': journal.name,
                        'partner': line.partner_id.name if line.partner_id else '',
                        'account': rec.expense_account_id.name if rec.payment_expense else line.account_id.name,
                        'move_name': line.move_id.name,
                        'debit': debit,
                        'credit': credit,
                        'line_balance':  debit - credit,
                        'balance': running_balance,
                    })
        return list(grouped_data.values())


    @api.model
    def _get_report_values(self, docids, data=None):
        grouped_lines = self._get_lines(
            data['date_from'],
            data['date_to'],
            data['journal_ids'],
            data['account_ids']
        )
        journal_records = self.env['account.journal'].browse(data['journal_ids'])

        return {
            'doc_ids': docids,
            'doc_model': 'cash.book.wizard',
            'data': data,
            'grouped_lines': grouped_lines,
            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'journal_records': journal_records,
        }

