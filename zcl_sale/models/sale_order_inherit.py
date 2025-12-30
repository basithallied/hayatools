from odoo import models, fields, api
from odoo.exceptions import UserError

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    standard_price = fields.Float( string='Cost', compute='_compute_last_purchase_cost', default=0)
    available_qty = fields.Float( string='Available Quantity', compute='_compute_available_qty', store=True)

    @api.depends('product_id')
    def _compute_last_purchase_cost(self):
        """ this function for find last purchase cost of the product"""
        for rec in self:
            if rec.product_id.id:
                last_purchase_line = self.env['purchase.order.line'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('order_id.state', 'in', ['purchase'])
                ],limit=1, order ='id desc')
                if last_purchase_line:
                    rec.standard_price = last_purchase_line.price_unit
                else:
                    rec.standard_price = rec.product_id.standard_price

    # @api.depends('product_id', 'order_id.state')
    # def _compute_available_qty(self):
    #     """Compute available quantity, ensuring all records are assigned a value."""
    #     for rec in self:
    #         if rec.order_id.state not in ['sale', 'cancel']:
    #             if rec.product_id and not rec.order_id.van_sale:
    #                 rec.available_qty = rec.product_id.qty_available
    #             elif rec.product_id and rec.order_id.van_sale:
    #                 if rec.order_id.user_id.allowed_location:
    #                     stocks = self.env['stock.quant'].sudo().search( [('product_id', '=', rec.product_id.id),
    #                          ('location_id', '=',  rec.order_id.user_id.allowed_location.id)])
    #                     total_qty = sum(stocks.mapped('quantity')) if stocks else 0
    #                     rec.available_qty = total_qty if total_qty else 0.0
    #                 else:
    #                     rec.available_qty = 0.0
    #             else:
    #                 rec.available_qty = 0.0
    #         else:
    #             rec.available_qty = rec.available_qty or 0.0

    @api.depends('product_id', 'order_id.state')
    def _compute_available_qty(self):
        """Compute available quantity, ensuring all records are assigned a value."""
        for rec in self:
            StockQuant = self.env['stock.quant']
            if rec.order_id.state not in ['sale', 'cancel']:
                if rec.product_id and not rec.order_id.van_sale:
                    # ADD WAREHOUSE CONDITION
                    warehouse = self.env.user.property_warehouse_id
                    if warehouse:
                        # Get the Stock Location of the Warehouse
                        warehouse_location = warehouse.lot_stock_id
                        qty = StockQuant._get_available_quantity(
                            rec.product_id, warehouse_location
                        )
                        rec.available_qty = qty
                    else:
                        rec.available_qty = rec.product_id.qty_available if rec.product_id else 0.0

                elif rec.product_id and rec.order_id.van_sale:
                    if rec.order_id.user_id.allowed_location:
                        stocks = self.env['stock.quant'].sudo().search( [('product_id', '=', rec.product_id.id),
                             ('location_id', '=',  rec.order_id.user_id.allowed_location.id)])
                        total_qty = sum(stocks.mapped('quantity')) if stocks else 0
                        rec.available_qty = total_qty if total_qty else 0.0
                    else:
                        rec.available_qty = 0.0
                else:
                    rec.available_qty = 0.0
            else:
                rec.available_qty = rec.available_qty or 0.0



class SaleOrder(models.Model):
    _inherit = 'sale.order'


    customer_balance = fields.Monetary(
        string="Customer Balance",
        compute="_compute_customer_balance",
        store=False,
        currency_field='currency_id'
    )

    van_sale = fields.Boolean('Van sale', default=False)

    def action_confirm(self):

        # Block Negative sale blocking
        for order in self:
            StockQuant = self.env['stock.quant']
            for line in order.order_line:
                product = line.product_id
                warehouse = self.env.user.property_warehouse_id
                if not order.van_sale:
                    if not warehouse:
                        if product.qty_available < line.product_uom_qty :
                            raise UserError(f"Not enough stock for {product.display_name}. Available: {product.qty_available}, "
                                            f"Required: {line.product_uom_qty}")
                    else:
                        warehouse_location = warehouse.lot_stock_id
                        qty = StockQuant._get_available_quantity(line.product_id, warehouse_location)
                        if qty < line.product_uom_qty:
                            raise UserError(
                                f"Not enough stock for {product.display_name}. Available: {product.qty_available},"
                                f"Required: {line.product_uom_qty}, In warehouse {warehouse.name}")


        res = super(SaleOrder, self).action_confirm()
        for order in self:
            for line in order.order_line:
                product = line.product_id
                product.list_price = line.price_unit # last price update in product master

            # Auto Confirm Delivery
            for picking in order.picking_ids:
                if order.van_sale:
                    picking.location_id = order.user_id.allowed_location.id
                if self.env.company.auto_validate_delivery and picking.state not in ['done', 'cancel']:
                    picking.action_confirm()
                    if picking.state == 'confirmed':
                        picking.action_assign()
                    if picking.state in ['assigned', 'partially_available']:
                        picking.button_validate()

        return res


    @api.depends('partner_id')
    def _compute_customer_balance(self):
        for order in self:
            if order.partner_id:
                order.customer_balance = (order.partner_id.credit - order.partner_id.debit)
            else:
                order.customer_balance = 0.0
