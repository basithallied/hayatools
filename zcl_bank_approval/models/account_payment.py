from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    state = fields.Selection(selection_add=[
        ('to_approve', 'To Approve')
    ], ondelete={'to_approve': 'cascade'})

    is_bank_journal = fields.Boolean(compute='_compute_is_bank_journal', store=True)

    @api.depends('journal_id')
    def _compute_is_bank_journal(self):
        for payment in self:
            payment.is_bank_journal = payment.journal_id.type == 'bank'

    def action_bank_approve(self):
        if not self.env.user.has_group('zcl_bank_approval.group_bank_approver'):
            raise UserError(_("You do not have the permissions to approve bank transactions."))
        return self.action_post()

    def action_post(self):
        to_post = self.env['account.payment']
        for payment in self:
            if payment.is_bank_journal and payment.state == 'draft':
                if self.env.user.has_group('zcl_bank_approval.group_bank_approver'):
                    to_post |= payment
                else:
                    payment.state = 'to_approve'
            elif payment.state == 'to_approve':
                if self.env.user.has_group('zcl_bank_approval.group_bank_approver'):
                    payment.state = 'draft' # Move back to draft for standard posting
                    to_post |= payment
                else:
                    raise UserError(_("This bank transaction is waiting for approval by an authorized person."))
            else:
                to_post |= payment
        
        if not to_post:
            return True
            
        return super(AccountPayment, to_post).action_post()
