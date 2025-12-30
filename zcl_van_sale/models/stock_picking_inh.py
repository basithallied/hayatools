# -*- coding: utf-8 -*-

from odoo import models,fields,api,_

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    van_transfer = fields.Boolean('Van Transfer', default=False)
    sales_person = fields.Many2one('res.users','Sales Person')


    @api.onchange('sales_person')
    def _onchange_of_sales_person(self):
        if self.sales_person:
            self.partner_id = self.sales_person.partner_id.id or False
            if self.sales_person.allowed_location:
                self.location_dest_id = self.sales_person.allowed_location.id
            else:
                self.location_dest_id = False  # Clear if not configured
                return {
                    'warning': {
                        'title': _('Configuration Missing'),
                        'message': _('Please configure an inventory location for the salesperson to proceed.'),
                    }
                }


    @api.depends('picking_type_id', 'partner_id', 'sales_person')
    def _compute_location_id(self):
        """Inherit base code and add condition for van sale """
        for picking in self:
            if picking.state in ('cancel', 'done') or picking.return_id:
                continue
            picking = picking.with_company(picking.company_id)
            if picking.picking_type_id:
                location_src = picking.picking_type_id.default_location_src_id
                if location_src.usage == 'supplier' and picking.partner_id:
                    location_src = picking.partner_id.property_stock_supplier
                location_dest = picking.picking_type_id.default_location_dest_id
                if location_dest.usage == 'customer' and picking.partner_id:
                    location_dest = picking.partner_id.property_stock_customer
                if picking.sales_person and picking.sales_person.allowed_location:
                    location_dest = picking.sales_person.allowed_location
                picking.location_id = location_src.id
                picking.location_dest_id = location_dest.id

