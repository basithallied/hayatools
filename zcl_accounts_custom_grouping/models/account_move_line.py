# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    parent_id = fields.Many2one('account.account',string='Parent', related='account_id.parent_id')
    account_group_id = fields.Many2one('account.sub.group', string='Parent Group', related='account_id.account_group_id')
    account_sub_group_id = fields.Many2one('account.sub.group', string='Sub Group', related='account_id.account_sub_group_id')