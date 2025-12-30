# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from odoo.exceptions import ValidationError, UserError
from collections import defaultdict


class AccountMove(models.Model):
    _inherit = 'account.move'

    sale_order_id = fields.Many2one('sale.order', string="Sale Order", domain="[('partner_id', '=', partner_id), ('state', '=', 'sale')]")
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order", domain="[('partner_id', '=', partner_id), ('state', '=', 'purchase')]")
    product_ids = fields.Many2many('product.product', string='Products', compute="_compute_product_ids")
    return_ids = fields.Many2many('stock.picking', string='Returns')

    @api.depends('sale_order_id','purchase_order_id')
    def _compute_product_ids(self):
        for rec in self:
            if rec.sale_order_id:
                rec.product_ids = [(6, 0, rec.sale_order_id.order_line.mapped("product_id").ids)]
            elif rec.purchase_order_id:
                rec.product_ids = [(6, 0, rec.purchase_order_id.order_line.mapped("product_id").ids)]
            else:
                rec.product_ids = [(5, 0, 0)]


    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.sale_order_id:
            self.sale_order_id = None
        if self.purchase_order_id:
            self.purchase_order_id = None

    #
    # @api.onchange('sale_order_id')
    # def _onchange_sale_order_id_with(self):
    #     self.ref = self.sale_order_id.name
    #     if self.sale_order_id:
    #         delivery_orders = self.sale_order_id.picking_ids.filtered(lambda p: p.state == 'done' and p.picking_type_id.code == 'outgoing')
    #
    #         if not delivery_orders:
    #             raise ValidationError("No completed delivery order found for this Sale Order.")
    #
    #         credit_note_lines = []
    #         for picking in delivery_orders:
    #             print("picking", picking.id)
    #             for move in picking.move_line_ids:
    #                 if move.quantity > 0:
    #                     credit_note_lines.append((0, 0, {
    #                         'product_id': move.product_id.id,
    #                         'quantity': move.quantity,
    #                         'lot_id': move.lot_id.id if move.lot_id else None,  # Set lot_id to None if no lot
    #                         'picking_id': picking.id,
    #                         'stock_move_id': move.move_id.id,
    #                         'price_unit': move.product_id.lst_price,
    #                         'display_type': 'product',
    #                         'sequence': 100
    #                     }))
    #
    #         if credit_note_lines:
    #             self.invoice_line_ids = [Command.clear()]
    #             self.invoice_line_ids =  credit_note_lines


    def action_post(self):
        """Override to create and validate the return picking when confirming the credit note"""
        if self.move_type == 'out_refund' and self.partner_id:
            self._create_and_validate_return_picking_of_sale()
        elif self.move_type == 'in_refund' and self.partner_id:
            self._create_and_validate_return_picking_of_purchase()
        res = super().action_post()
        return res



    def _create_and_validate_return_picking_of_sale(self):
        self.ensure_one()
        if self.sale_order_id:
            product_qty_map = defaultdict(float)
            for rec in self.invoice_line_ids:
                product_qty_map[rec.product_id] += rec.quantity


            for product, return_qty in product_qty_map.items():
                sale_line = self.sale_order_id.order_line.filtered(lambda l: l.product_id == product)

                if not sale_line:
                    raise UserError(f"Product {product.display_name} is not in the sale order.")

                delivered_qty = sum(sale_line.mapped("qty_delivered"))

                if return_qty > delivered_qty:
                    raise UserError(f"Return quantity {return_qty} for {product.display_name} exceeds delivered quantity {delivered_qty}.")


            delivery_orders = self.sale_order_id.picking_ids.filtered(lambda p: p.state == 'done' and p.picking_type_id.code == 'outgoing')
            return_picking_id = []
            for line in self.invoice_line_ids:
                returned_qty = line.quantity
                if returned_qty > 0:
                    for picking in delivery_orders:
                        for move in picking.move_line_ids:
                            if line.product_id == move.product_id:
                                if returned_qty > 0:
                                    if move.quantity > 0:
                                        qty = 0
                                        if returned_qty == move.quantity:
                                            qty = move.quantity
                                        elif move.quantity > returned_qty:
                                            qty = returned_qty
                                        elif move.quantity < returned_qty:
                                            qty = move.quantity
                                        return_wizard = self.env['stock.return.picking'].create(
                                            {'picking_id': picking.id, 'company_id': self.company_id.id, 'product_return_moves': [(0, 0, {
                                                'product_id': line.product_id.id, 'quantity':qty, 'move_id': move.move_id.id, 'uom_id': line.product_uom_id.id})]})

                                        returned_qty -= qty

                                        abc = return_wizard.action_create_returns()
                                        return_picking_id.append(abc.get("res_id"))

            if return_picking_id:
                return_ids_list = self.return_ids.ids
                for pick in return_picking_id:
                    returns = self.env['stock.picking'].browse(int(pick))
                    returns._action_done()
                    returns.button_validate()
                    return_ids_list.extend(returns.ids)
                self.return_ids = [(6, 0, list(set(return_ids_list)))]


    def _create_and_validate_return_picking_of_purchase(self):
        self.ensure_one()
        if self.purchase_order_id:
            product_qty_map = defaultdict(float)
            for rec in self.invoice_line_ids:
                product_qty_map[rec.product_id] += rec.quantity

            for product, return_qty in product_qty_map.items():
                purchase_line = self.purchase_order_id.order_line.filtered(lambda l: l.product_id == product)

                if not purchase_line:
                    raise UserError(f"Product {product.display_name} is not in the purchase order.")

                delivered_qty = sum(purchase_line.mapped("qty_received"))

                if return_qty > delivered_qty:
                    raise UserError(f"Return quantity {return_qty} for {product.display_name} exceeds delivered quantity {delivered_qty}.")

            delivery_orders = self.purchase_order_id.picking_ids.filtered(lambda p: p.state == 'done' and p.picking_type_id.code == 'incoming')
            return_picking_id = []
            for line in self.invoice_line_ids:
                returned_qty = line.quantity
                if returned_qty > 0:
                    for picking in delivery_orders:
                        for move in picking.move_line_ids:
                            if line.product_id == move.product_id:
                                if returned_qty > 0:
                                    if move.quantity > 0:
                                        qty = 0
                                        if returned_qty == move.quantity:
                                            qty = move.quantity
                                        elif move.quantity > returned_qty:
                                            qty = returned_qty
                                        elif move.quantity < returned_qty:
                                            qty = move.quantity
                                        return_wizard = self.env['stock.return.picking'].create(
                                            {'picking_id': picking.id, 'company_id': self.company_id.id, 'product_return_moves': [(0, 0, {
                                                'product_id': line.product_id.id, 'quantity': qty, 'move_id': move.move_id.id, 'uom_id': line.product_uom_id.id})]})

                                        returned_qty -= qty
                                        abc = return_wizard.action_create_returns()
                                        return_picking_id.append(abc.get("res_id"))

            if return_picking_id:
                return_ids_list = self.return_ids.ids
                for pick in return_picking_id:
                    returns = self.env['stock.picking'].browse(int(pick))
                    returns._action_done()
                    returns.button_validate()
                    return_ids_list.extend(returns.ids)
                self.return_ids = [(6, 0, list(set(return_ids_list)))]


    def write(self, vals):
        """Override write to print context while updating a record"""
        record = super().write(vals)
        for rec in self.invoice_line_ids:
            if self.sale_order_id:
                if not rec.product_id:
                    rec.sudo().unlink()
        return record

    def action_view_returns(self):
        self.ensure_one()
        return {
            'name': 'Return Pickings',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'stock.picking',
            'domain': [('id', 'in', self.return_ids.ids)],
            'target': 'current',
        }



class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    lot_id = fields.Many2one('stock.lot', string="Lot/Serial Number")
    picking_id = fields.Many2one('stock.picking', string="Stock Picking")
    stock_move_id = fields.Many2one('stock.move', string="Stock Move")


