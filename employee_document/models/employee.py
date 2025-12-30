from odoo import api, fields, models

class Employee(models.Model):
    _inherit = 'hr.employee'

    document_tracking_ids = fields.One2many(
        'document.tracking',
        'employee_id',
        string='Employee Documents'
    )