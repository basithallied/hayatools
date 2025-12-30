from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    sale_return_id = fields.Many2one("sale.return", string="Sale Return")


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    sale_return_line_id = fields.Many2one("sale.return.line", string="Sale Return Line")
