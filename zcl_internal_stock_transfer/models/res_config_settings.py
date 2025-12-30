from odoo import models, fields, api

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ist_source_location_id = fields.Many2one(
        'stock.location',
        string="Default Source Location",
        config_parameter='zcl_internal_stock_transfer.source_location_id'
    )
    ist_dest_location_id = fields.Many2one(
        'stock.location',
        string="Default Destination Location",
        config_parameter='zcl_internal_stock_transfer.dest_location_id'
    )
    ist_transit_location_id = fields.Many2one(
        'stock.location',
        string="Default Transit Location",
        config_parameter='zcl_internal_stock_transfer.transit_location_id'
    )
