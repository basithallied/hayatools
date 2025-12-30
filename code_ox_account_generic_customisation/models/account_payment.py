from odoo import models, fields, _
from odoo.exceptions import UserError

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    ref_date = fields.Date(string='Reference Date', tracking=True)
    remarks = fields.Char(string='Remarks', tracking=True)


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        res = super(AccountPaymentRegister, self).action_create_payments()
        for wizard in self:
            if wizard.amount > wizard.source_amount_currency and wizard.source_amount_currency > 0:
                raise UserError(_("The payment amount cannot be greater than invoice amount."))
        return res