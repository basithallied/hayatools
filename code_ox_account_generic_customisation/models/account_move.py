from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    total_discount = fields.Float(string='Total Discount', compute='_compute_total_discount', store=True)

    @api.depends('invoice_line_ids.discount_amount')
    def _compute_total_discount(self):
        for inv in self:
            inv.total_discount = sum(inv.invoice_line_ids.mapped('discount_amount'))

    def _compute_tax_totals(self):
        res = super(AccountMove, self)._compute_tax_totals()
        for inv in self:
            if inv.tax_totals:
                if inv.total_discount > 0:
                    inv.tax_totals['discount'] = inv.total_discount
                global_discount = sum(inv.invoice_line_ids.filtered(lambda x: x.is_discount == True).mapped('price_subtotal'))
                inv.tax_totals['total_amount_currency'] = inv.tax_totals['total_amount_currency'] + global_discount
                if 'subtotals' in inv.tax_totals:
                    for subtotal in inv.tax_totals['subtotals']:
                        if subtotal.get('name') == 'Untaxed Amount':
                            subtotal['name'] = 'Taxable'
        return res