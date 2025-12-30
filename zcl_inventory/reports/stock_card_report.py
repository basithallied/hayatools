# -- coding: utf-8 --
###################################################################################

# Author       :  Sayooj t k
# Copyright(c) :  2023-Present Zinfog Codelabs Pvt Ltd (<https://www.zinfog.com>).
# License      :  LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

# This program is free software:
# you can modify it under the terms of the GNU Lesser General Public License (LGPL) as
# published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
############################################################

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime


class StockCard(models.TransientModel):
    _name = 'stock.card.report'
    _description = 'Stock Card Report'
    _rec_name = 'name'

    name = fields.Char(string='Stock Card', default='Stock Card')
    product_ids = fields.Many2many('product.product', string='Products')
    partner_id = fields.Many2many('res.partner', string='Partner', domain="['|', ('supplier_rank', '>', 0 ), ('customer_rank', '>', 0 )]")
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    html_content = fields.Html(string=' ', readonly=True)
    location_ids = fields.Many2many('stock.location', string='Location', domain="[('usage', 'not in', ('supplier','customer', 'view'))]")

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for record in self:
            if record.date_from and record.date_to and record.date_from > record.date_to:
                raise ValidationError("The 'From Date' must be earlier than or equal to the 'To Date'.")

    def fetch_data(self):
        for rec in self:
            rec.html_content = False
            if not rec.date_from or not rec.date_to:
                raise ValidationError("Both 'From Date' and 'To Date' must be set to fetch data.")


            table_content = """
                <table border="1" style="width: 100%; border-collapse: collapse; border:1px solid black;">
                    <thead>
                        <tr  style="padding:5px;font-size:18px;border:1px solid black;">
                            <th  style="padding:5px;font-size:18px;border:1px solid black;">Date</th>
                            <th  style="padding:5px;font-size:18px;border:1px solid black;">Partner</th>
                            <th  style="padding:5px;font-size:18px;border:1px solid black;">Voucher Type</th>
                            <th  style="padding:5px;font-size:18px;border:1px solid black;">Voucher No</th>
                            <th  style="padding:5px;font-size:18px;border:1px solid black;">Inwards Quantity</th>
                            <th  style="padding:5px;font-size:18px;border:1px solid black;">Inwards Value</th>
                            <th  style="padding:5px;font-size:18px;border:1px solid black;">Outwards Quantity</th>
                            <th  style="padding:5px;font-size:18px;border:1px solid black;">Outwards Value</th>
                            <th  style="padding:5px;font-size:18px;border:1px solid black;">Location</th>
                            <th  style="padding:5px;font-size:18px;border:1px solid black;">Remaining Qty</th>
                        </tr>
                    </thead>
                    <tbody>
            """

            total_inward_qty = total_inward_value = total_outward_qty = total_outward_value = 0

            all_products = rec.product_ids or self.env['product.product'].search([])
            location_domain = []
            locations_ids_ids = None

            for product in all_products:

                domain = [
                    ('product_id', '=', product.id), ('state', '=', 'done'),
                    ('date', '>=', datetime.combine(rec.date_from, datetime.min.time())),
                    ('date', '<=', datetime.combine(rec.date_to, datetime.max.time())),
                ]

                if rec.location_ids:
                    location_domain =  [
                        '|',('location_id', 'in', rec.location_ids.ids),
                        ('location_dest_id', 'in', rec.location_ids.ids),
                    ]

                stock_moves = self.env['stock.move'].search(domain + location_domain, order='date asc')
                print('stock_moves',stock_moves)
                if rec.location_ids:
                    locations_ids = rec.location_ids.ids
                else:
                    locations_ids = self.env['stock.location'].search([]).ids


                # Add product name row only if stock moves exist
                if stock_moves:
                    table_content += f"""
                        <tr>
                            <td colspan='10' style="font-weight: bold;padding:5px;background-color: #e0e0e0;">{product.name}</td>
                        </tr>
                    """

                    for move in stock_moves:
                        outwards_qty = outwards_value = inwards_qty = inwards_value = 0
                        partner_name = ''
                        voucher_name = ''
                        name = ''
                        location = ''
                        remaining = 0
                        if move.purchase_line_id and move.origin_returned_move_id:
                            if move.location_id.id in locations_ids:
                                if move.location_id.usage not in ['supplier', 'view', 'customer', 'inventory']:
                                    outwards_qty = move.product_uom_qty
                                    outwards_value = float(move.product_uom_qty) * (move.purchase_line_id.price_unit) if move.purchase_line_id else 0 # Unit Price taken from purchase line
                                    partner_name = move.purchase_line_id.partner_id.name
                                    voucher_name = move.purchase_line_id.order_id.name
                                    location = move.location_id.name
                                    name = 'PURCHASE-RETURN'
                                    remaining = move.remaining_qty_src
                            else:
                                if move.location_dest_id.id in locations_ids:
                                    inwards_qty = move.product_uom_qty
                                    inwards_value = float(move.product_uom_qty) * (move.purchase_line_id.price_unit) if move.purchase_line_id else 0  # Unit Price taken from purchase line
                                    partner_name = move.purchase_line_id.partner_id.name
                                    voucher_name = move.purchase_line_id.order_id.name
                                    location = move.location_dest_id.name
                                    name = 'PURCHASE-RETURN'
                                    remaining = move.remaining_qty_dest
                        elif move.sale_line_id and move.origin_returned_move_id:
                            if move.location_dest_id.usage not in ['supplier', 'view', 'customer', 'inventory']:
                                if move.location_dest_id.id in locations_ids:
                                    inwards_qty = move.product_uom_qty
                                    inwards_value = float(move.product_uom_qty) * (move.sale_line_id.price_unit) if move.sale_line_id else 0 # Unit Price taken from sale order line
                                    partner_name = move.sale_line_id.order_partner_id.name
                                    voucher_name = move.sale_line_id.order_id.name
                                    location = move.location_dest_id.name
                                    name = 'SALE-RETURN'
                                    remaining = move.remaining_qty_dest
                            else:
                                if move.location_id.id in locations_ids:
                                    outwards_qty = move.product_uom_qty
                                    outwards_value = float(move.product_uom_qty) * (move.sale_line_id.price_unit) if move.sale_line_id else 0  # Unit Price taken from sale order line
                                    partner_name = move.sale_line_id.order_partner_id.name
                                    voucher_name = move.sale_line_id.order_id.name
                                    location = move.location_id.name
                                    name = 'SALE-RETURN'
                                    remaining = move.remaining_qty_src
                        elif move.purchase_line_id:
                            if move.location_dest_id.id in locations_ids and move.location_id.usage == 'supplier':
                                inwards_qty = move.product_uom_qty if move.purchase_line_id else 0
                                inwards_value = float(move.product_uom_qty) * (move.purchase_line_id.price_unit) if move.purchase_line_id else 0 # Unit Price taken from purchase line
                                partner_name = move.purchase_line_id.partner_id.name
                                voucher_name = move.purchase_line_id.order_id.name
                                location = move.location_dest_id.name
                                name = 'PURCHASE'
                                remaining = move.remaining_qty_dest
                            if move.location_id.id in locations_ids and move.location_dest_id.usage == 'supplier':
                                # some case there is no return id so take from here purchase return
                                inwards_qty = move.product_uom_qty
                                inwards_value = float(move.product_uom_qty) * (
                                    move.purchase_line_id.price_unit) if move.purchase_line_id else 0  # Unit Price taken from purchase line
                                partner_name = move.purchase_line_id.partner_id.name
                                voucher_name = move.purchase_line_id.order_id.name
                                location = move.location_dest_id.name
                                name = 'PURCHASE-RETURN'
                                remaining = move.remaining_qty_dest
                        elif move.sale_line_id:
                            if move.location_id.id in locations_ids and move.location_dest_id.usage == 'customer':
                                outwards_qty = move.product_uom_qty if move.sale_line_id else 0
                                outwards_value = float(move.product_uom_qty) * (move.sale_line_id.price_unit) if move.sale_line_id else 0 # Unit Price taken from sale order line
                                partner_name = move.sale_line_id.order_partner_id.name
                                voucher_name = move.sale_line_id.order_id.name
                                location = move.location_id.name
                                name = 'SALE'
                                remaining = move.remaining_qty_src
                            elif move.location_dest_id.id in locations_ids and move.location_id.usage == 'customer':
                                # some case there is no return id so take from here sales return
                                inwards_qty = move.product_uom_qty
                                inwards_value = float(move.product_uom_qty) * (
                                    move.sale_line_id.price_unit) if move.sale_line_id else 0  # Unit Price taken from sale order line
                                partner_name = move.sale_line_id.order_partner_id.name
                                voucher_name = move.sale_line_id.order_id.name
                                location = move.location_dest_id.name
                                name = 'SALE-RETURN'
                                remaining = move.remaining_qty_dest
                        else:
                            # Stock adjustment details
                            if not move.picking_type_id.code == 'internal':
                                # Stock adjustment inward
                                if move.location_usage not in ('internal', 'transit') and move.location_dest_usage in ('internal', 'transit'):
                                    if move.location_dest_id.id in locations_ids:

                                        inwards_qty = move.product_uom_qty
                                        valuation_layers = move.stock_valuation_layer_ids
                                        price_unit = valuation_layers[0].unit_cost if valuation_layers else 0.0 # Price taken from Valuation Layers
                                        inwards_value = float(move.product_uom_qty) * price_unit # Calculation based on Valuation Layers
                                        voucher_name = move.reference
                                        partner_name = move.partner_id.name
                                        location = move.location_dest_id.name
                                        remaining = move.remaining_qty_dest

                                # elif move.picking_type_id.code == 'outgoing':
                                # Stock adjustment outward
                                elif move.location_usage in ('internal', 'transit') and move.location_dest_usage not in ('internal', 'transit'):
                                    if move.location_id.id in locations_ids:
                                        outwards_qty = move.product_uom_qty
                                        valuation_layers = move.stock_valuation_layer_ids
                                        price_unit = valuation_layers[0].unit_cost if valuation_layers else 0.0 # Price taken from Valuation Layers
                                        outwards_value = float(move.product_uom_qty) * price_unit # Calculation based on Valuation Layers
                                        voucher_name = move.reference
                                        partner_name = move.partner_id.name
                                        location = move.location_id.name
                                        remaining = move.remaining_qty_src

                        if not move.picking_type_id.code == 'internal':

                                table_content += f"""
                                   <tr style="border:1px solid black;">
                                       <td style="border:1px solid black;padding:5px;">{move.date.strftime('%d-%b-%Y')}</td>
                                       <td style="border:1px solid black;padding:5px;">{partner_name if partner_name else ''}</td>
                                       <td style="border:1px solid black;padding:5px;">{name if name else ''}</td>
                                       <td style="border:1px solid black;padding:5px;">{voucher_name}</td>
                                       <td style="border:1px solid black;padding:5px;">{inwards_qty if inwards_qty else ''}</td>
                                       <td style="border:1px solid black;padding:5px;">{inwards_value if inwards_value else ''}</td>
                                       <td style="border:1px solid black;padding:5px;">{outwards_qty if outwards_qty else ''}</td>
                                       <td style="border:1px solid black;padding:5px;">{outwards_value if outwards_value else ''}</td>
                                       <td style="border:1px solid black;padding:5px;">{location if location else ''}</td>
                                       <td style="border:1px solid black;padding:5px;">{remaining if remaining else (move.remaining_qty if move.remaining_qty else 0)}</td>
                                   </tr>
                               """

                        else:
                            # internal transfer source location
                            if move.location_id.usage not in ['supplier', 'view', 'customer', 'inventory']:
                                outwards_qty = inwards_qty = move.product_uom_qty
                                valuation_layers = move.stock_valuation_layer_ids
                                price_unit = valuation_layers[0].unit_cost if valuation_layers else 0.0  # Price taken from Valuation Layers
                                outwards_value = inwards_value = float(move.product_uom_qty) * price_unit
                                voucher_name = move.reference
                                partner_name = move.partner_id.name if move.partner_id else ''
                                name = 'INTERNAL'

                                if move.location_id.id in locations_ids:
                                    table_content += f"""
                                            <tr style="border:1px solid black;">
                                                <td style="border:1px solid black;padding:5px;">{move.date.strftime('%d-%b-%Y')}</td>
                                                <td style="border:1px solid black;padding:5px;">{partner_name if partner_name else ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{name if name else ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{voucher_name}</td>
                                                <td style="border:1px solid black;padding:5px;">{ ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{ ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{outwards_qty if outwards_qty else ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{outwards_value if outwards_value else ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{move.location_id.name if move.location_id else ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{move.remaining_qty_src if move.remaining_qty_src else 0}</td>
                                            </tr>
                                        """


                            # internal transfer destination location
                            if move.location_dest_id.usage not in ['supplier', 'view', 'customer', 'inventory']:
                                if move.location_dest_id.id in locations_ids:
                                    table_content += f"""
                                            <tr style="border:1px solid black;">
                                                <td style="border:1px solid black;padding:5px;">{move.date.strftime('%d-%b-%Y')}</td>
                                                <td style="border:1px solid black;padding:5px;">{partner_name if partner_name else ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{name if name else ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{voucher_name}</td>
                                                <td style="border:1px solid black;padding:5px;">{inwards_qty if inwards_qty else ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{inwards_value if inwards_value else ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{''}</td>
                                                <td style="border:1px solid black;padding:5px;">{''}</td>
                                                <td style="border:1px solid black;padding:5px;">{move.location_dest_id.name if move.location_dest_id else ''}</td>
                                                <td style="border:1px solid black;padding:5px;">{move.remaining_qty_dest if move.remaining_qty_dest else 0}</td>
                                            </tr>
                                        """

                        # Update totals
                        total_inward_qty += inwards_qty
                        total_inward_value += inwards_value
                        total_outward_qty += outwards_qty
                        total_outward_value += outwards_value

            # Add footer with totals after processing all products
            table_content += f"""
                </tbody>
                <tfoot>
                    <tr>
                        <th colspan="4" style="text-align: right;padding:5px;">Totals</th>
                        <th style="padding:5px;">{total_inward_qty}</th>
                        <th style="padding:5px;">{total_inward_value:.2f}</th>
                        <th style="padding:5px;">{total_outward_qty}</th>
                        <th style="padding:5px;">{total_outward_value:.2f}</th>
                    </tr>
                </tfoot>
                </table>
            """

            # Set the final HTML content
            rec.html_content = table_content



class StockMove(models.Model):
    _inherit = 'stock.move'

    remaining_qty = fields.Float(string='Total Remaining Quantity', help="The total remaining quantity of the product in stock.", copy=False, default=0.0)
    remaining_qty_src = fields.Float(string='Total Remaining Quantity Source location', help="The total remaining quantity of the product in source location",copy=False, default=0.0)
    remaining_qty_dest = fields.Float(string='Total Remaining Quantity Destination location', help="The total remaining quantity of the product in stock destination location",copy=False, default=0.0)

    def _action_done(self, cancel_backorder=False):
        # res = super(StockMove, self)._action_done()
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        for move in self:

            # move.remaining_qty = move.product_id.qty_available

            if move.location_id.usage not in ['supplier', 'view', 'customer', 'inventory']:
                stocks = self.env['stock.quant'].sudo().search([('product_id', '=', move.product_id.id),('location_id', '=',move.location_id.id)])
                total_qty = sum(stocks.mapped('quantity')) if stocks else 0
                move.remaining_qty_src = total_qty if total_qty else 0.0
            if move.location_dest_id.usage not in ['supplier', 'view', 'customer', 'inventory']:
                stocks = self.env['stock.quant'].sudo().search([('product_id', '=', move.product_id.id),('location_id', '=',move.location_dest_id.id)])
                total_qty = sum(stocks.mapped('quantity')) if stocks else 0
                move.remaining_qty_dest = total_qty if total_qty else 0.0
        return res


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for move in self.move_ids_without_package:
            # Fetch the total quantity available for the product

            # total_qty_available = move.product_id.qty_available
            # move.remaining_qty = total_qty_available


            if move.location_id.usage not in ['supplier', 'view', 'customer', 'inventory']:
                stocks = self.env['stock.quant'].sudo().search([('product_id', '=', move.product_id.id),('location_id', '=',move.location_id.id)])
                total_qty = sum(stocks.mapped('quantity')) if stocks else 0
                move.remaining_qty_src = total_qty if total_qty else 0.0
            if move.location_dest_id.usage not in ['supplier', 'view', 'customer', 'inventory']:
                stocks = self.env['stock.quant'].sudo().search([('product_id', '=', move.product_id.id),('location_id', '=',move.location_dest_id.id)])
                total_qty = sum(stocks.mapped('quantity')) if stocks else 0
                move.remaining_qty_dest = total_qty if total_qty else 0.0

        return res


