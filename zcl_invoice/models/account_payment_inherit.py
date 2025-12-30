# -- coding: utf-8 --
###################################################################################

# Author       :  Sayooj t k
# Copyright(c) :  2023-Present Zinfog Codelabs Pvt Ltd (<https://www.zinfog.com>).
# License      :  LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

# This program is free software:
# you can modify it under the terms of the GNU Lesser General Public License (LGPL) as
# published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
############################################################

from odoo import models, fields,api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError



class AccountPayment(models.Model):
    _inherit = 'account.payment'

    state = fields.Selection(selection_add=[('internal_transfer', 'Internal Transfer'),('expense_done', 'Done')], ondelete={'internal_transfer': 'set default','expense_done': 'set default'})

    journal_id = fields.Many2one(
        comodel_name='account.journal',
        compute='_compute_journal_id', store=True, readonly=False, precompute=True,
        check_company=True,
        index=False,
        required=True, default=False
    )  # inherit default field and remove the default loading

    partner_total_payable = fields.Monetary(compute='_compute_payable_receivable', store=True,
                                            string='Total Receivable', readonly=True,
                                            help="Total amount this customer owes you."
                                            )
    partner_total_receivable = fields.Monetary(compute='_compute_payable_receivable', store=True,
                                               string='Total Payable', readonly=True,
                                               help="Total amount you have to pay to this "
                                                    "vendor.")
    internal_transfers = fields.Boolean(string='Internal Transfer ', default=False)
    branch_transfers = fields.Boolean(string='Branch Transfer ', default=False)


    currency_id = fields.Many2one(
        'res.currency',
        string="Currency",
        default=lambda self: self.env.company.currency_id,
        required=True,
        readonly=True
    )

    destination_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Destination Journal",
        domain="[('type', 'in', ['bank', 'cash']), "
               "('company_id', '=', company_id), ('id', '!=', journal_id)]",
    )

    payment_expense = fields.Boolean(string='Expense', default=False)



    unpaid_invoice_bill_ids = fields.One2many(
        'account.move',
        string='Unpaid Invoices',
        store=False

    )

    expense_account_id = fields.Many2one(
        'account.account',
        string='Account',

    )


    @api.depends('partner_id')
    def _compute_unpaid_moves(self):
        for record in self:
            if record.partner_id:
                # Fetch unpaid invoices and bills in one search
                moves = self.env['account.move'].search([
                    ('partner_id', '=', record.partner_id.id),
                    ('move_type', 'in', ['out_invoice', 'in_invoice']),  # Both Invoices and Bills
                    ('payment_state', '!=', 'paid'),
                    ('state', '=', 'posted')
                ])
                record.unpaid_invoice_bill_ids = moves

                if record.unpaid_invoice_bill_ids:
                    for rec in record.unpaid_invoice_bill_ids:
                        rec.account_payment_reconcile_id = record.id

            else:
                record.unpaid_invoice_bill_ids = False

    def action_view_unpaid_invoices(self):
        self._compute_unpaid_moves()
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Unpaid Invoices',
            'view_mode': 'list',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.unpaid_invoice_bill_ids.ids),
                       ('move_type', '=', 'out_invoice')
                       ],
            'target': 'new',  # Opens in a popup
            'context': {
                'create': False,
                'edit': False,
                'default_move_type': 'out_invoice'
            },
            'view_id': self.env.ref('zcl_invoice.view_account_move_tree_custom').id,  # Reference to custom view
        }

    def action_view_unpaid_bills(self):
        self._compute_unpaid_moves()
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Unpaid Bills',
            'view_mode': 'list',
            'res_model': 'account.move',
            'domain': [('id', 'in', self.unpaid_invoice_bill_ids.ids),
                       ('move_type', '=', 'in_invoice')],
            'target': 'new',
            'context': {
                'create': False,
                'edit': False,
                'default_move_type': 'in_invoice'
            },
            'view_id': self.env.ref('zcl_invoice.view_account_move_tree_custom').id,

        }





    @api.depends('partner_id')
    def _compute_payable_receivable(self):
        for record in self:
            if record.partner_id:
                record.partner_total_payable = record.partner_id.credit
                record.partner_total_receivable = record.partner_id.debit
            else:
                record.partner_total_payable = 0.0
                record.partner_total_receivable = 0.0



    # # Method to reconcile payments with corresponding invoices or bills
    # def payment_reconcile(self):
    #     for rec in self:
    #         # Define the domain based on payment type
    #         if rec.payment_type == 'inbound':
    #             domain = [
    #                 ('partner_id', '=', rec.partner_id.id),
    #                 ('state', '=', 'posted'),
    #                 ('payment_state', 'in', ['not_paid', 'partial']),
    #                 ('move_type', '=', 'out_invoice')  # Customer Invoices
    #             ]
    #         elif rec.payment_type == 'outbound':  # Vendor payment
    #             domain = [
    #                 ('partner_id', '=', rec.partner_id.id),
    #                 ('state', '=', 'posted'),
    #                 ('payment_state', 'in', ['not_paid', 'partial']),
    #                 ('move_type', '=', 'in_invoice')   # Vendor Bills
    #             ]
    #         # Search for matching invoices or bills
    #         moves = self.env['account.move'].search(domain, order= 'id asc')
    #         if moves:
    #             for inv in moves:
    #
    #                 credit_line = (rec.move_id.line_ids + inv.line_ids).filtered(
    #                     lambda line: line.account_id.reconcile and not line.reconciled
    #                     )
    #                 # Perform reconciliation
    #                 credit_line.reconcile()

    def action_post(self):
        if self.internal_transfers:
            self._create_internal_transfer_journal_entry()
            # expense
        elif self.payment_expense:
            self._create_expense_journal_entry()
        else:
            result = super(AccountPayment, self).action_post()
            return result

    @api.constrains('state', 'move_id')
    def _check_move_id(self):
        for payment in self:
            if not payment.internal_transfers and not payment.payment_expense:
                if (
                    payment.state not in ('draft', 'canceled', 'to_approve')
                    and not payment.move_id
                    and payment.outstanding_account_id
                ):
                    raise ValidationError(_("A payment with an outstanding account cannot be confirmed without having a journal entry."))
                if payment.state == 'draft' and payment.move_id:
                    raise ValidationError(_("A payment cannot have a journal entry if it is not confirmed."))


    def _create_internal_transfer_journal_entry(self):
        if not self.destination_journal_id:
            raise UserError(_("Please select a destination journal for the internal transfer."))

        if self.journal_id == self.destination_journal_id:
            raise UserError(_("The source and destination journals must be different."))

        # Create journal entry
        move_vals = {
            'ref': f'Internal Transfer from {self.journal_id.name} From {self.destination_journal_id.name}' ,
            'journal_id': self.journal_id.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.journal_id.default_account_id.id,
                    'name': _('Transfer to %s') % self.destination_journal_id.name,
                    'credit': self.amount,
                    'debit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.destination_journal_id.default_account_id.id,
                    'name': _('Transfer from %s') % self.journal_id.name,
                    'debit': self.amount,
                    'credit': 0.0,
                }),
            ]
        }
        move = self.env['account.move'].create(move_vals)
        self.move_id = move
        move.action_post()
        self.state = 'internal_transfer'

    def _create_expense_journal_entry(self):
        if not self.journal_id:
            raise UserError(_("Please select a journal."))

        if self.partner_id.property_account_payable_id.id == self.journal_id.default_account_id:
            raise UserError(_("The source and destination accounts must be different."))

        # Create journal entry
        move_vals = {
            'ref': f'Expense of {self.partner_id.name}' ,
            'journal_id': self.journal_id.id,
            'line_ids': [
                (0, 0, {
                    'account_id': self.expense_account_id.id,
                    'name': _('Transfer from %s') % self.journal_id.default_account_id.name,
                    'partner_id': self.partner_id.id,
                    'debit': self.amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.journal_id.default_account_id.id,
                    'name': _('Transfer to %s') % self.expense_account_id.name,
                    'credit': self.amount,
                    'partner_id': self.partner_id.id,
                    'debit': 0.0,
                }),
            ]
        }
        move = self.env['account.move'].create(move_vals)
        self.move_id = move
        move.action_post()
        self.state = 'expense_done'






