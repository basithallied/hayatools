import base64
import xlrd
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import datetime

class JournalImportWizard(models.TransientModel):
    _name = 'journal.import.wizard'
    _description = 'Import Journal Entry from Excel'

    file = fields.Binary(string='File', required=True)
    file_name = fields.Char(string='File Name')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True)
    contra_account_id = fields.Many2one('account.account', string='Contra Account', required=True)
    contra_partner_id = fields.Many2one('res.partner', string='Contra Partner (e.g. Wife)')
    
    def import_journal_entry(self):
        try:
            decoded_file = base64.b64decode(self.file)
            book = xlrd.open_workbook(file_contents=decoded_file)
            sheet = book.sheet_by_index(0)
        except Exception as e:
            raise UserError(_("Please provide a valid Excel file. Error: %s") % e)

        # Columns (0-based indices)
        # A: Date (0)
        # B: Ref. No. (1)
        # C: Account (2)
        # D: Party's Name (3)
        # E: Debit (4)
        # F: Credit (5)

        for row_idx in range(1, sheet.nrows): # Skip header
            row = sheet.row_values(row_idx)
            
            date_val = row[0]
            ref = str(row[1]).split('.')[0] # Handle float '123.0' -> '123'
            account_code_or_name = str(row[2]).split('.')[0]
            party_name = row[3]
            debit = float(row[4]) if row[4] else 0.0
            credit = float(row[5]) if row[5] else 0.0

            # Date parsing
            if isinstance(date_val, float):
                date_tuple = xlrd.xldate_as_tuple(date_val, book.datemode)
                date = datetime.date(*date_tuple[:3])
            else:
                # Try string parse if needed, usually xlrd gives float
                date = fields.Date.today()

            # Find Account
            account = self.env['account.account'].search([
                ('code', '=', account_code_or_name),
            ], limit=1)
            if not account:
                # Try by name
                account = self.env['account.account'].search([
                    ('name', 'ilike', account_code_or_name),
                ], limit=1)
            
            if not account:
                raise UserError(_("Account not found for code/name: %s at row %s") % (account_code_or_name, row_idx + 1))

            # Find Partner
            partner = self.env['res.partner'].search([('name', '=', party_name)], limit=1)
            if not partner and party_name:
                partner = self.env['res.partner'].create({'name': party_name})
            
            # Create Move
            move_vals = {
                'date': date,
                'ref': ref,
                'journal_id': self.journal_id.id,
                'move_type': 'entry',
            }
            move = self.env['account.move'].create(move_vals)

            # 1. Main Line
            line_vals = {
                'move_id': move.id,
                'account_id': account.id,
                'partner_id': partner.id if partner else False,
                'name': ref,
                'debit': debit,
                'credit': credit,
            }
            self.env['account.move.line'].create(line_vals)

            # 2. Contra Line (Balancing)
            # Reverse Debit/Credit
            contra_debit = credit
            contra_credit = debit
            
            contra_line_vals = {
                'move_id': move.id,
                'account_id': self.contra_account_id.id,
                'partner_id': self.contra_partner_id.id if self.contra_partner_id else False,
                'name': ref + ' (Contra)',
                'debit': contra_debit,
                'credit': contra_credit,
            }
            self.env['account.move.line'].create(contra_line_vals)

        return {'type': 'ir.actions.act_window_close'}
