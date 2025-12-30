from odoo import models, fields

class BaseDocumentLayout(models.TransientModel):
    _inherit = 'base.document.layout'

    street = fields.Char(related='company_id.street', readonly=True)
    street2 = fields.Char(related='company_id.street2', readonly=True)
    city = fields.Char(related='company_id.city', readonly=True)
    zip = fields.Char(related='company_id.zip', readonly=True)
    state_id = fields.Many2one(related='company_id.state_id', readonly=True)
    country_id = fields.Many2one(related='company_id.country_id', readonly=True)
    phone = fields.Char(related='company_id.phone', readonly=True)
    email = fields.Char(related='company_id.email', readonly=True)
    vat = fields.Char(related='company_id.vat', readonly=True)
