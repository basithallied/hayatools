# from odoo import models, api
#
#
# class StockTraceabilityConfig(models.Model):
#     _inherit = 'stock.configuration'
#
#     @api.model
#     def _set_expiration_dates_default(self):
#         # Set default value for expiration dates setting under traceability
#         traceability_settings = self.env.ref('stock.stock_traceability_settings')
#
#         # Check if the setting exists and enable expiration date
#         if traceability_settings:
#             traceability_settings.write({
#                 'trace_lot_expiration': True
#             })
#
#         # Alternatively, set the ir.config_parameter directly (if traceability settings aren't found)
#         self.env['ir.config_parameter'].sudo().set_param('stock.trace_lot_expiration', True)
#
