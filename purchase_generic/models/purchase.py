from odoo import models, fields,api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    import_purchase = fields.Boolean(default=False)
    ministry_approval_ids = fields.Many2many('ir.attachment', 'ministry_approval', 'purchase_id', 'attachment_id')
    health_approval_ids = fields.Many2many('ir.attachment', 'health_approval', 'purchase_id', 'attachment_id')
    labeling_approval_ids = fields.Many2many('ir.attachment', 'labeling_approval', 'purchase_id', 'attachment_id')
    total_discount = fields.Monetary(string='Discount Amount', compute='_compute_discount_amount', store=True, readonly=True)


    @api.onchange('import_purchase')
    def _onchange_import_purchase(self):
        if self.import_purchase:
            return {'domain': {'partner_id': [('vendor_type', '=', 'import_vendor')]}}
        else:
            return {'domain': {'partner_id': [('vendor_type', '=', 'local_vendor')]}}
        
    @api.depends('order_line.discount_amount')
    def _compute_discount_amount(self):
        for order in self:
            order.total_discount = sum(order.order_line.mapped('discount_amount'))

    @api.depends('order_line.price_subtotal', 'currency_id', 'company_id', 'total_discount')
    def _compute_tax_totals(self):
        res = super(PurchaseOrder, self)._compute_tax_totals()
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
            if 'subtotals' in order.tax_totals:
                for subtotal in order.tax_totals['subtotals']:
                    if subtotal.get('name') == 'Untaxed Amount':
                        subtotal['name'] = 'Taxable'
        return res
    
    def send_to_multiple_vendors(self):
        try:
            if self.env.context.get('send_rfq', False):
                template_id = self.env.ref('purchase.email_template_edi_purchase')
            else:
                template_id = self.env.ref('purchase.email_template_edi_purchase_done')
        except ValueError:
            template_id = False
        for record in self.alternative_po_ids:
            template_id.send_mail(record.id)
            if record.state == 'draft':
                record.write({'state': 'sent'})
        return True
    
    def action_create_invoice(self):
        res = super(PurchaseOrder, self).action_create_invoice()
        for order in self:
            bill = self.env['account.move'].browse(res['res_id'])
            for line in order.order_line:
                if line.is_discount:
                    bill.invoice_line_ids.filtered(lambda x: x.purchase_line_id == line).write({'is_discount': True})
        return res

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    expiration_date = fields.Datetime(compute='get_expiration_date')
    internal_reference = fields.Char(
        string='Internal Reference',
        related='product_id.default_code',
        store=True,
        readonly=True,
    )
    discount_amount = fields.Float(string='Discount Amount', compute='_compute_discount_amount', store=True)
    is_discount = fields.Boolean(string='Is Discount', default=False)

    def get_expiration_date(self):
        for line in self:
            if line.product_id.tracking == 'lot':
                moves = line.move_ids
                lots = moves.mapped('lot_ids')
                if lots:
                    line.expiration_date = lots[0].expiration_date
                else:
                    line.expiration_date = False
            else:
                line.expiration_date = False

    @api.depends('product_qty', 'price_unit', 'price_unit_discounted')
    def _compute_discount_amount(self):
        for line in self:
            line.discount_amount = line.product_qty * (line.price_unit - line.price_unit_discounted)
            if line.is_discount:
                line.discount_amount = -1 * line.price_subtotal