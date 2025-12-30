from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    is_bank_approver = fields.Boolean(
        string='Bank Transaction Approver',
        compute='_compute_is_bank_approver',
        inverse='_inverse_is_bank_approver',
        help='If checked, the user will be added to the Bank Transaction Approver group.'
    )

    def _compute_is_bank_approver(self):
        group_id = self.env.ref('zcl_bank_approval.group_bank_approver')
        for user in self:
            user.is_bank_approver = group_id in user.groups_id

    def _inverse_is_bank_approver(self):
        group_id = self.env.ref('zcl_bank_approval.group_bank_approver')
        for user in self:
            if user.is_bank_approver:
                user.groups_id = [(4, group_id.id)]
            else:
                user.groups_id = [(3, group_id.id)]
