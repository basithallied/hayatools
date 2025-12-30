
from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class SalePurchaseRegisterReport(models.AbstractModel):
    _name = 'report.zcl_invoice.report_zcl_sale_purchase_register'
    _description = 'Sale and Purchase Register Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data:
            _logger.error("❌ No data received!")
            return {}

        from_date_str = data.get('from_date')
        to_date_str = data.get('to_date')
        register_type = data.get('register_type')
        journal_id = data.get('journal_id')

        from_date = fields.Date.from_string(from_date_str) if from_date_str else None
        to_date = fields.Date.from_string(to_date_str) if to_date_str else None

        register_type_label = dict(
            self.env['sale.purchase.register.wizard'].fields_get(['register_type'])['register_type']['selection']
        ).get(register_type, '')

        journal_name = ""
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            journal_name = journal.name if journal.exists() else ""

        company_name = self.env.company.name if self.env.company else ""

        domain = [('date', '>=', from_date), ('date', '<=', to_date), ('state', '=', 'posted')]
        if journal_id:
            domain.append(('journal_id', '=', journal_id))

        if register_type == 'sale':
            domain.append(('move_type', 'in', ['out_invoice', 'out_refund']))
        elif register_type == 'purchase':
            domain.append(('move_type', 'in', ['in_invoice', 'in_refund']))

        entries = self.env['account.move'].search(domain)

        return {
            'doc_ids': docids,
            'doc_model': 'sale.purchase.register.wizard',
            'docs': self.env['sale.purchase.register.wizard'].browse(docids),
            'entries': entries,
            'from_date': from_date.strftime('%d/%m/%y') if from_date else '',
            'to_date': to_date.strftime('%d/%m/%y') if to_date else '',
            'register_type': register_type_label,
            'journal_name': journal_name,
            'company_name': company_name,
            'is_sale': register_type == 'sale',
            'is_purchase': register_type == 'purchase',
        }