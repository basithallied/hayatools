from odoo import models, fields,api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    standard_price = fields.Float(string='Cost')
    available_qty = fields.Float( string='Available Quantity', compute='_compute_available_qty', store=True)


    # @api.depends('product_id', 'order_id.state')
    # def _compute_available_qty(self):
    #     """Compute available quantity, ensuring all records are assigned a value."""
    #     for rec in self:
    #         if rec.order_id.state not in ['purchase', 'cancel']:
    #             if rec.product_id:
    #                 rec.available_qty = rec.product_id.qty_available
    #             else:
    #                 rec.available_qty = 0.0
    #         else:
    #             rec.available_qty = rec.available_qty or 0.0


    @api.depends('product_id', 'order_id.state')
    def _compute_available_qty(self):
        StockQuant = self.env['stock.quant']
        for rec in self:
            if rec.order_id.state in ['purchase', 'cancel']:
                rec.available_qty = 0.0
                continue

            warehouse = self.env.user.property_warehouse_id
            if rec.product_id and warehouse:
                # Get the Stock Location of the Warehouse
                warehouse_location = warehouse.lot_stock_id
                qty = StockQuant._get_available_quantity(
                    rec.product_id, warehouse_location
                )
                rec.available_qty = qty
            else:
                rec.available_qty = rec.product_id.qty_available if rec.product_id else 0.0



class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    vendor_balance = fields.Monetary(
        string="Vendor Balance",
        compute="_compute_vendor_balance",
        store=False,
        currency_field='currency_id'
    )



    @api.depends('partner_id')
    def _compute_vendor_balance(self):
        for order in self:
            if order.partner_id:
                order.vendor_balance = (order.partner_id.credit - order.partner_id.debit)
            else:
                order.vendor_balance = 0.0




