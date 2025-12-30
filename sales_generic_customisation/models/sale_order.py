from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.fields import Command
from odoo.tools import format_date, frozendict

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_type = fields.Selection([
        ('wholesale', 'Wholesale'),
        ('b2b', 'B2B'),
        ('vansale', 'Van Sale')
    ], string="Sales Type")

    has_price_alert = fields.Boolean(
        string="Has Price Alert",
        compute='_compute_has_price_alert',
        store=True
    )
    total_discount = fields.Monetary(string='Discount Amount', compute='_compute_discount_amount', store=True, readonly=True)

    @api.depends('order_line.discount_amount')
    def _compute_discount_amount(self):
        for order in self:
            order.total_discount = sum(order.order_line.mapped('discount_amount'))

    @api.depends('order_line.price_unit', 'order_line.purchase_price', 'order_line.product_id.is_storable')
    def _compute_has_price_alert(self):
        for order in self:
            order.has_price_alert = any(
                line.purchase_price > line.price_unit and line.product_id.is_storable
                for line in order.order_line
            )
    
    def _compute_tax_totals(self):
        res = super(SaleOrder, self)._compute_tax_totals()
        AccountTax = self.env['account.tax']
        for order in self:
            order_lines = order.order_line.filtered(lambda x: not x.display_type and not x.is_discount)
            base_lines = [line._prepare_base_line_for_taxes_computation() for line in order_lines]
            AccountTax._add_tax_details_in_base_lines(base_lines, order.company_id)
            AccountTax._round_base_lines_tax_details(base_lines, order.company_id)
            order.tax_totals = AccountTax._get_tax_totals_summary(
                base_lines=base_lines,
                currency=order.currency_id or order.company_id.currency_id,
                company=order.company_id,
            )
            if order.total_discount > 0:
                order.tax_totals['discount'] = order.total_discount
            global_discount = sum(order.order_line.filtered(lambda x: x.is_discount == True).mapped('price_subtotal'))
            order.tax_totals['total_amount_currency'] = order.tax_totals['total_amount_currency'] + global_discount
            # Change untaxed amount to taxable
            if 'subtotals' in order.tax_totals:
                for subtotal in order.tax_totals['subtotals']:
                    if subtotal.get('name') == 'Untaxed Amount':
                        subtotal['name'] = 'Taxable'
        return res
    
    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super()._create_invoices(grouped=grouped, final=final, date=date)
        for order in self:
            for line in order.order_line:
                if line.is_discount:
                    moves.invoice_line_ids.filtered(lambda x: x.sale_line_ids == line).write({'is_discount': True})
        return moves

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    expiration_date = fields.Datetime(related='lot_id.expiration_date', string="Lot Expiry", store=True)
    internal_reference = fields.Char(
        string='Internal Reference',
        related='product_id.default_code',
        store=True,
        readonly=True,
    )
    is_discount = fields.Boolean(string='Is Discount', default=False)
    discount_amount = fields.Float(string='Discount Amount', compute='_compute_discount_amount', store=True)

    @api.depends('product_uom_qty', 'price_unit', 'price_subtotal')
    def _compute_discount_amount(self):
        for line in self:
            line.discount_amount = (line.product_uom_qty * line.price_unit) - line.price_subtotal
            if line.is_discount:
                line.discount_amount = -1 * line.price_subtotal