# -*- coding: utf-8 -*-
#############################################################################
#
#############################################################################
from datetime import date
from odoo import fields, models,api
import calendar
from odoo.tools.misc import get_lang



class AccountPartnerLedger(models.TransientModel):
    _name = "account.repor.partner.ledger"
    _inherit = "account.common.partner.report"
    _description = "Account Partner Ledger"

    section_main_report_ids = fields.Many2many(string="Section Of",
                                               comodel_name='account.report',
                                               relation="account_report_partner_section_rel",
                                               column1="sub_report_id",
                                               column2="main_report_id")
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, default=lambda self: self.env.company)

    section_report_ids = fields.Many2many(string="Sections",
                                          comodel_name='account.report',
                                          relation="account_report_partner_section_rel",
                                          column1="main_report_id",
                                          column2="sub_report_id")
    name = fields.Char(string="Partner Ledger Report",
                       default="Partner Ledger Report", required=True,
                       translate=True)
    amount_currency = fields.Boolean("With Currency",
                                     help="It adds the currency column on"
                                          " report if the "
                                          "currency differs from the "
                                          "company currency.")
    reconciled = fields.Boolean(string='Reconciled Entries')

    partner_ids = fields.Many2many('res.partner', string="Partner")
    partner_id = fields.Many2one('res.partner', string="Partner")
    journal_ids = fields.Many2many(
        comodel_name='account.journal',
        string='Journals',
        required=True,
        default=lambda self: self.env['account.journal'].search(
            [('company_id', '=', self.company_id.id)]),
        domain="[('company_id', '=', company_id)]")



    # filter_residual = fields.Boolean(
    #     string="Due Entries",
    #     help="Check this box to filter out records where the residual amount is zero.")
    this_month = fields.Boolean(string="This Month")
    previous_month = fields.Boolean(string="Previous Month")
    this_year = fields.Boolean(string="This Year")
    previous_year = fields.Boolean(string="Previous Year")

    @api.onchange('this_month', 'previous_month', 'this_year','previous_year')
    def _onchange_date_fields(self):
        """ Update the date range based on the selected field. """
        today = date.today()

        if self.this_month:
            first_day, last_day = calendar.monthrange(today.year, today.month)
            self.date_from = date(today.year, today.month, 1)
            self.date_to = date(today.year, today.month, last_day)
            self.previous_month = False
            self.this_year = False
            self.previous_year = False

        elif self.previous_month:
            prev_month = today.month - 1 if today.month > 1 else 12
            prev_year = today.year if today.month > 1 else today.year - 1
            first_day, last_day = calendar.monthrange(prev_year, prev_month)
            self.date_from = date(prev_year, prev_month, 1)
            self.date_to = date(prev_year, prev_month, last_day)
            self.this_month = False
            self.this_year = False
            self.previous_year = False


        elif self.this_year:
            self.date_from = date(today.year, 1, 1)
            self.date_to = date(today.year, 12, 31)
            self.this_month = False
            self.previous_month = False
            self.previous_year = False


        elif self.previous_year:
            prev_year = today.year - 1
            self.date_from = date(prev_year, 1, 1)
            self.date_to = date(prev_year, 12, 31)
            self.this_month = False
            self.previous_month = False
            self.this_year = False

        else:
            self.date_from = False
            self.date_to = False


    # def _print_report(self, data):
    #     data = self.pre_print_report(data)
    #     data['form'].update({'reconciled': self.reconciled,
    #                          'amount_currency': self.amount_currency,
    #                          'partner_ids': self.partner_ids.ids,
    #                          'partner': self.partner_id.id,
    #                          'filter_residual':self.filter_residual,})
    #     print("data", data)
    #     return self.env.ref(
    #         'zcl_reports.action_report_partnerledger').report_action(
    #         self, data=data)

    def check_report_background(self):
        self.ensure_one()
        data = {}
        data['ids'] = self.env.context.get('active_ids', [])
        data['model'] = self.env.context.get('active_model', 'ir.ui.menu')
        data['form'] = self.read(
            ['date_from', 'date_to', 'journal_ids', 'target_move',
             'company_id'])[0]
        used_context = self._build_contexts(data)
        data['form']['used_context'] = dict(used_context,
                                            lang=get_lang(self.env).code)
        return self.with_context(discard_logo_check=True)._print_report_background(data)


    def _print_report_background(self, data):
        data = self.pre_print_report(data)
        data['form'].update({'reconciled': self.reconciled,
                             'amount_currency': self.amount_currency,
                             'partner_ids': self.partner_ids.ids,
                             'partner': self.partner_id.id,
                             })
        print("data", data)
        return self.env.ref(
            'zcl_reports.action_report_partnerledger_background').report_action(
            self, data=data)




