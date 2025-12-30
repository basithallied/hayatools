from odoo import models, fields

class SalePurchaseRegisterWizard(models.TransientModel):
    _name = "sale.purchase.register.wizard"

    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="To Date", required=True)
    register_type = fields.Selection([('sale', 'Sale Register'), ('purchase', 'Purchase Register')], string="Register Type", required=True)
    journal_id = fields.Many2one('account.journal', string="Journal")

    def action_print_sale_purchase_register(self):
        data = {
            'from_date': self.from_date,
            'to_date': self.to_date,
            'register_type': self.register_type,
            'journal_id': self.journal_id.id if self.journal_id else False,
        }
        return self.env.ref('zcl_invoice.action_sale_purchase_register_report_new').report_action(self, data=data)
