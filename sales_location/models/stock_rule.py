from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'
    
    def _get_stock_move_values(self, product_id, product_qty, product_uom,
                               location_id, name, origin, company_id, values):
        if values.get('sale_line_id', False):
            sale_line_id = self.env['sale.order.line'].sudo().browse(
                values['sale_line_id'])
            self.location_src_id = sale_line_id.order_id.source_location_id if sale_line_id.order_id.source_location_id else self.picking_type_id.default_location_src_id
        return super()._get_stock_move_values(product_id,
                                              product_qty,
                                              product_uom,
                                              location_id,
                                              name, origin,
                                              company_id,
                                              values)
