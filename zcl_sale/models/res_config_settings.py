from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    auto_validate_delivery = fields.Boolean(related='company_id.auto_validate_delivery', readonly=False)
