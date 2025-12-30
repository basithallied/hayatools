# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError,ValidationError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_pdc = fields.Boolean('PDC Payment')
    cheque_no = fields.Char('Cheque No')
    cheque_date = fields.Date('Cheque Date')
    pdc_journal = fields.Many2one('account.move')

    def button_open_pdc_entry(self):
        '''  Redirect the user to this pdc journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.pdc_journal.id,
        }

    @api.constrains('payment_method_line_id')
    def constrains_of_payment_method_line_id(self):
        for rec in self:
            if rec.is_pdc and rec.payment_method_line_id:
                if  rec.payment_method_line_id.payment_method_id.code not in ['pdc_out','pdc_in']:
                    raise ValidationError(_("Please add valid pdc payment method"))
                if not rec.payment_method_line_id.payment_account_id:
                    raise ValidationError(_("Please configure payment method accounts"))


    def action_pdc_clear(self):
        for payment in self:
            if not payment.move_id:
                raise UserError("No journal entry found for this payment.")

            if payment.pdc_journal:
                raise UserError("Cheque already cleared. Reversal journal exists.")

            if not payment.journal_id.default_account_id:
                raise UserError("No default account set for journal: %s" % payment.journal_id.name)

            # Get main accounts
            original_bank_account = payment.journal_id.default_account_id  # Actual bank account
            pdc_account = payment.payment_method_line_id.payment_account_id  # Assuming this is your PDC account



            if not pdc_account:
                raise UserError("No destination account (PDC) found for payment.")

            if payment.payment_type == 'inbound':
                # From PDC to Actual Bank
                debit_line = {
                    'name': 'PDC Clearance',
                    'account_id': original_bank_account.id,
                    'debit': payment.amount,
                    'credit': 0.0,
                    'partner_id': payment.partner_id.id,
                }
                credit_line = {
                    'name': 'PDC Clearance',
                    'account_id': pdc_account.id,
                    'debit': 0.0,
                    'credit': payment.amount,
                    'partner_id': payment.partner_id.id,
                }

            elif payment.payment_type == 'outbound':
                # From Actual Bank to PDC
                debit_line = {
                    'name': f'PDC Clearance of - {payment.cheque_no}',
                    'account_id': pdc_account.id,
                    'debit': payment.amount,
                    'credit': 0.0,
                    'partner_id': payment.partner_id.id,
                }
                credit_line = {
                    'name': f'PDC Clearance of - {payment.cheque_no}',
                    'account_id': original_bank_account.id,
                    'debit': 0.0,
                    'credit': payment.amount,
                    'partner_id': payment.partner_id.id,
                }

            else:
                raise UserError("Unsupported payment type for cheque clearing.")

            reversal_move = self.env['account.move'].create({
                'ref': f'PDC Clearance: {payment.name}',
                'journal_id': payment.journal_id.id,
                'date': fields.Date.today(),
                'line_ids': [(0, 0, debit_line), (0, 0, credit_line)],
            })

            reversal_move.action_post()

            payment.pdc_journal = reversal_move.id


