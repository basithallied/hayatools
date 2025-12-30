from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    has_financial_report_access = fields.Boolean(
        string='Financial Report Access',
        compute='_compute_financial_report_access',
        inverse='_inverse_financial_report_access',
        help='If checked, the user will be added to the Financial Report Access group.'
    )

    def _compute_financial_report_access(self):
        group_id = self.env.ref('zcl_financial_report_access.group_financial_report_access')
        for user in self:
            user.has_financial_report_access = group_id in user.groups_id

    def _inverse_financial_report_access(self):
        group_id = self.env.ref('zcl_financial_report_access.group_financial_report_access')
        for user in self:
            if user.has_financial_report_access:
                user.groups_id = [(4, group_id.id)]
            else:
                user.groups_id = [(3, group_id.id)]
