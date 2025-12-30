# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class ResPartner(models.Model):
    _inherit = 'res.partner'

    days_limit = fields.Integer(string="Days")

    def _check_day_limit_restriction(self):
        for partner in self:
            if partner.days_limit > 0:
                # Calculate the max overdue days
                overdue_invoices = self.env['account.move'].search([
                    ('partner_id', '=', partner.id),
                    ('move_type', '=', 'out_invoice'),
                    ('payment_state', 'in', ['not_paid', 'partial']),
                    ('invoice_date_due', '<', fields.Date.today()),
                    ('state', '=', 'posted')
                ])

                if overdue_invoices:
                    max_due_days = max((fields.Date.today() - inv.invoice_date_due).days for inv in overdue_invoices)
                    if max_due_days > partner.days_limit:
                        raise ValidationError(_(
                            "Cannot create Sale Order. The customer has overdue invoices older than the allowed day limit (%s days)." % partner.days_limit
                        ))