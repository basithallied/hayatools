from odoo import fields, models, api, _


class AccountPartnerLedger(models.TransientModel):
    _name = "account.report.partner.ledger"
    _inherit = "account.common.partner.report"
    _description = "Account Partner Ledger"

    amount_currency = fields.Boolean("With Currency",
                                     help="It adds the currency column on "
                                          "report if the currency differs from "
                                          "the company currency.")
    reconciled = fields.Boolean('Reconciled Entries', default=True)
    company_ids = fields.Many2many(
        'res.company', string='Companies',
        default=lambda self: self.env.companies
    )

    @api.onchange('company_ids')
    def _onchange_company_ids(self):
        if self.company_ids:
            self.journal_ids = self.env['account.journal'].sudo().search(
                [('company_id', 'in', self.company_ids.ids)])
        else:
            self.journal_ids = self.env['account.journal'].sudo().search([])

    def _get_report_data(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled,
                             'amount_currency': self.amount_currency,
                             'company_ids': self.company_ids.ids})
        if data['form'].get('company_ids'):
            data['form']['used_context']['allowed_company_ids'] = data['form']['company_ids']
            data['form']['used_context']['company_id'] = False
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_partnerledger').with_context(landscape=True).\
            report_action(self, data=data)
