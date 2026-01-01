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
        # ...
        # G: Debit (6)
        # H: Credit (7)

        for row_idx in range(1, sheet.nrows): # Skip header
            row = sheet.row_values(row_idx)
            
            date_val = row[0]
            ref = str(row[1]).split('.')[0] # Handle float '123.0' -> '123'
            account_code_or_name = str(row[2]).split('.')[0]
            party_name = row[3]
            debit_raw = row[6] # Column G
            credit_raw = row[7] # Column H

            def safe_float(val):
                if not val:
                    return 0.0
                if isinstance(val, str):
                    val = val.replace(',', '').strip()
                try:
                    return float(val)
                except ValueError:
                    return 0.0

            debit = safe_float(debit_raw)
            credit = safe_float(credit_raw)
            
            if debit == 0.0 and credit == 0.0:
                 raise UserError(_("Row %s has 0 Debit and 0 Credit.\nRaw Data: %s") % (row_idx + 1, row))


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
            
            # Prepare Lines
            line_ids = []
            
            # 1. Main Line
            line_ids.append((0, 0, {
                'account_id': account.id,
                'partner_id': partner.id if partner else False,
                'name': ref,
                'debit': debit,
                'credit': credit,
            }))

            # 2. Contra Line (Balancing)
            # Reverse Debit/Credit
            contra_debit = credit
            contra_credit = debit
            
            line_ids.append((0, 0, {
                'account_id': self.contra_account_id.id,
                'partner_id': self.contra_partner_id.id if self.contra_partner_id else False,
                'name': ref + ' (Contra)',
                'debit': contra_debit,
                'credit': contra_credit,
            }))
            
            # Create Move with Lines
            move_vals = {
                'date': date,
                'ref': ref,
                'journal_id': self.journal_id.id,
                'move_type': 'entry',
                'line_ids': line_ids,
            }
            self.env['account.move'].create(move_vals)

        return {'type': 'ir.actions.act_window_close'}
