from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = 'account.move'

    state = fields.Selection(selection_add=[
        ('to_approve', 'To Approve')
    ], ondelete={'to_approve': 'cascade'})

    is_bank_journal = fields.Boolean(compute='_compute_is_bank_journal', store=True)

    @api.depends('journal_id')
    def _compute_is_bank_journal(self):
        for move in self:
            move.is_bank_journal = move.journal_id.type == 'bank'

    def action_submit_for_approval(self):
        for move in self:
            if move.state != 'draft':
                continue
            if not move.is_bank_journal:
                continue
            move.state = 'to_approve'

    def action_bank_approve(self):
        if not self.env.user.has_group('zcl_bank_approval.group_bank_approver'):
            raise UserError(_("You do not have the permissions to approve bank transactions."))
        return self.action_post()

    def action_post(self):
        to_post = self.env['account.move']
        for move in self:
            if move.is_bank_journal and move.state == 'draft':
                if self.env.user.has_group('zcl_bank_approval.group_bank_approver'):
                    to_post |= move
                else:
                    move.action_submit_for_approval()
            elif move.state == 'to_approve':
                if self.env.user.has_group('zcl_bank_approval.group_bank_approver'):
                    move.state = 'draft' # Move back to draft for standard posting
                    to_post |= move
                else:
                    raise UserError(_("This bank transaction is waiting for approval by an authorized person."))
            else:
                to_post |= move
        
        if not to_post:
            return True
            
        return super(AccountMove, to_post).action_post()
