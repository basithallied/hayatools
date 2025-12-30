from odoo import models, fields,api
from odoo.exceptions import UserError
import logging
from datetime import date
import base64

_logger = logging.getLogger(__name__)



class AccountMove(models.Model):
    _inherit = 'account.move'


    manuel_entry = fields.Boolean()
    account_payment_reconcile_id = fields.Many2one('account.payment')
    report_file = fields.Binary("Invoice PDF", readonly=True)
    report_filename = fields.Char("Filename")
    partner_tags = fields.Many2many('res.partner.category', related='partner_id.category_id', string='Tags')

    def action_customer_invoice_report(self):
        return self.env.ref('zcl_invoice.action_customer_invoice_report').report_action(self.id, data=None)


    # @api.model
    # def create(self, vals):
    #     move_type = vals.get('move_type')
    #     if move_type in ['out_invoice', 'out_refund'] and not vals.get('name'):
    #         sequence_code = 'account.custom.invoice' if move_type == 'out_invoice' else 'account.custom.refund'
    #         vals['name'] = self.env['ir.sequence'].next_by_code(sequence_code) or '/'
    #     return super(AccountMove, self).create(vals)





    @api.depends('company_id', 'invoice_filter_type_domain')
    def _compute_suitable_journal_ids(self):
        for m in self:
            credit_domain = []
            if m.move_type == 'out_refund':
                credit_domain = [('is_credit_note_journal', '=', True)]
            journal_type = m.invoice_filter_type_domain or 'general'
            company = m.company_id or self.env.company
            if not m.move_type == 'out_refund':
                m.suitable_journal_ids = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('type', '=', journal_type),
                ]+ credit_domain)
            else:
                m.suitable_journal_ids = self.env['account.journal'].search([
                    *self.env['account.journal']._check_company_domain(company),
                    ('is_credit_note_journal', '=', True),
                ])


    def _search_default_journal(self):
        if self.statement_line_ids.statement_id.journal_id:
            return self.statement_line_ids.statement_id.journal_id[:1]

        journal_types = self._get_valid_journal_types()
        company = self.company_id or self.env.company
        domain = [
            *self.env['account.journal']._check_company_domain(company),
            ('type', 'in', journal_types),
        ]

        journal = None
        # the currency is not a hard dependence, it triggers via manual add_to_compute
        # avoid computing the currency before all it's dependences are set (like the journal...)
        if self.env.cache.contains(self, self._fields['currency_id']):
            currency_id = self.currency_id.id or self._context.get('default_currency_id')
            if currency_id and currency_id != company.currency_id.id:
                currency_domain = domain + [('currency_id', '=', currency_id)]
                journal = self.env['account.journal'].search(currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)

        if not journal:
            error_msg = self.env['account.journal']._build_no_journal_error_msg(company.display_name, journal_types)
            raise UserError(error_msg)

        if self.move_type in ['out_refund', 'entry']:
            journal= None

        return journal

    # automates the reconciliation of payments with selected invoices
    def action_payment_reconcile(self):
        for rec in self:
            # Check if invoices are selected
            selected_invoices = self.env.context.get('active_ids', [])
            if not selected_invoices:
                raise UserError('Please select invoices to reconcile.')

            # Loop through each selected invoice
            for invoice_id in selected_invoices:
                print('rec.account_payment_reconcile_id',rec.account_payment_reconcile_id)
                invoice = self.env['account.move'].browse(invoice_id)
                credit_line = (rec.account_payment_reconcile_id.move_id.line_ids + invoice.line_ids).filtered(
                    lambda line: line.account_id.reconcile and not line.reconciled
                )
                # Perform reconciliation
                if credit_line:
                    credit_line.reconcile()



    def action_post(self):
        result = super(AccountMove, self).action_post()
        self.auto_reconcile_customer_supplier()
        if self.move_type in ['in_invoice' ,'in_refund']:
            self.l10n_sa_confirmation_datetime = fields.Datetime.now()
        return result



    def auto_reconcile_customer_supplier(self):
        partners = self.env['res.partner'].search([('id', '=', self.partner_id.id)])

        for partner in partners:
            account_lines = self.env['account.move.line'].search([
                ('partner_id', '=', partner.id),
                ('reconciled', '=', False),
                ('account_id.reconcile', '=', True),
                ('move_type', 'in', ['in_invoice','out_invoice'])
            ])

            if account_lines:
                account_ids = account_lines.mapped('account_id.id')
                for account_id in account_ids:
                    lines_to_reconcile = account_lines.filtered(lambda l: l.account_id.id == account_id)
                    if lines_to_reconcile and len(lines_to_reconcile) > 1:
                        try:
                            lines_to_reconcile.reconcile()
                        except Exception as e:
                            _logger.warning(f"Reconciliation failed for partner {partner.name}: {e}")


    def print_custom_invoice_report(self):
        return self.env.ref('zcl_invoice.action_customer_invoice_with_header').report_action(self.id, data=None)

    def action_print_invoice_api(self):
        self.ensure_one()
        report_print = self.env.ref('zcl_invoice.action_customer_invoice_with_header').report_action(self.id, data=None)
        pdf_data, _ = self.env['ir.actions.report']._render_qweb_pdf('zcl_invoice.action_customer_invoice_with_header', res_ids=self.id)
        encoded_pdf = base64.b64encode(pdf_data)
        filename = f"Invoice_{self.name or self.id}.pdf"
        self.report_file = encoded_pdf
        self.report_filename = filename
        return report_print

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    overdue_by_days = fields.Integer(string="Overdue by (Days)",compute="_compute_overdue_by_days",)

    @api.depends('date_maturity')
    def _compute_overdue_by_days(self):
        today = date.today()
        for record in self:
            if not record.reconciled:
                if record.date_maturity:
                    record.overdue_by_days = (today - record.date_maturity).days
                else:
                    record.overdue_by_days = 0
            else:
                record.overdue_by_days = 0
