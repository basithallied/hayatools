# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

class SalePersonIncentive(models.Model):
    _name = 'salesperson.incentive'
    _description = 'Salesperson Incentive'
    _order = 'date_from desc'

    name = fields.Char(string='Incentive Reference', required=True, copy=False, readonly=True, default='New')
    salesperson_id = fields.Many2one('res.users', string='Salesperson', required=True)
    date_from = fields.Date(string='From Date', required=True)
    date_to = fields.Date(string='To Date', required=True)
    percentage = fields.Float(string='Incentive %', required=True)
    target_amount = fields.Monetary(string='Target Amount')
    sale_amount = fields.Monetary(string='Sale Amount', compute='_compute_sale_amount')
    amount = fields.Monetary(string='Total Incentive', compute='_compute_amount', inverse='_inverse_amount', )
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    line_ids = fields.One2many('salesperson.incentive.line', 'incentive_id', string='Product Lines')
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'),('posted', 'Posted')], default='draft', string='Status')


    # Accounting
    journal_id = fields.Many2one('account.journal', string='Journal')
    debit_account_id = fields.Many2one('account.account', string='Debit Account')
    credit_account_id = fields.Many2one('account.account', string='Credit Account')
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True)

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('salesperson.incentive') or 'New'
        return super().create(vals)

    @api.constrains('salesperson_id', 'date_from', 'date_to')
    def _check_unique_period(self):
        for rec in self:
            domain = [
                ('salesperson_id', '=', rec.salesperson_id.id),
                ('id', '!=', rec.id),
                ('date_from', '<=', rec.date_to),
                ('date_to', '>=', rec.date_from),
            ]
            if self.search_count(domain):
                raise ValidationError(_('An incentive already exists for this salesperson in this period.'))

    def _inverse_amount(self):
        pass


    @api.depends('line_ids.total')
    def _compute_amount(self):
        for rec in self:
            rec.amount = sum(rec.line_ids.mapped('total'))



    @api.depends('line_ids.price_subtotal')
    def _compute_sale_amount(self):
        for rec in self:
            rec.sale_amount = sum(rec.line_ids.mapped('price_subtotal'))

    def action_calculate_lines(self):
        for rec in self:
            if rec.state != 'draft':
                raise ValidationError(_("Cannot recalculate on approved incentives."))
            rec.line_ids.unlink()
            lines = self.env['sale.order.line'].search([
                ('order_id.user_id', '=', rec.salesperson_id.id),
                ('product_id.product_tmpl_id.is_import', '=', rec.salesperson_id.id),
                ('order_id.date_order', '>=', rec.date_from),
                ('order_id.date_order', '<=', rec.date_to),
                ('order_id.state', 'in', ['sale', 'done']),
            ])
            line_vals = []
            for line in lines:
                line_vals.append((0, 0, {
                    'product_id': line.product_id.id,
                    'order_id': line.order_id.id,
                    'date_order': line.order_id.date_order,
                    'price_subtotal': line.price_subtotal,
                    'incentive_percent': rec.percentage,
                    'total': (line.price_subtotal * rec.percentage) / 100,
                }))
            rec.line_ids = line_vals

    def action_post_to_accounting(self):
        for rec in self:
            if rec.state != 'approved':
                raise UserError("Only approved incentives can be posted.")
            if not rec.journal_id or not rec.debit_account_id or not rec.credit_account_id:
                raise UserError("Journal and accounts must be set before posting.")

            move_vals = {
                'ref': rec.name,
                'journal_id': rec.journal_id.id,
                'date': fields.Date.context_today(self),
                'partner_id': self.salesperson_id.partner_id.id,
                'line_ids': [
                    (0, 0, {
                        'account_id': rec.debit_account_id.id,
                        'name': rec.name,
                        'debit': rec.amount,
                        'credit': 0.0,
                        'partner_id':self.salesperson_id.partner_id.id
                    }),
                    (0, 0, {
                        'account_id': rec.credit_account_id.id,
                        'name': rec.name,
                        'debit': 0.0,
                        'credit': rec.amount,
                        'partner_id':self.salesperson_id.partner_id.id
                    }),
                ],
            }
            move = self.env['account.move'].create(move_vals)
            move.action_post()
            rec.move_id = move.id
            rec.state = 'posted'

    def action_approve(self):
        for rec in self:
            rec.state = 'approved'

    def write(self, vals):
        if 'state' not in vals and any(rec.state == 'posted' for rec in self):
            raise ValidationError(_("Approved incentives cannot be edited."))
        return super().write(vals)

    def button_open_journal_entry(self):
        ''' Redirect the user to this incentive journal.
        :return:    An action on account.move.
        '''
        self.ensure_one()
        return {
            'name': _("Journal Entry"),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }


    def unlink(self):
        for rec in self:
            if rec.state == 'posted':
                raise UserError("You cannot delete an incentive that has been posted to accounting.")
        return super(SalePersonIncentive, self).unlink()



class SalespersonIncentiveLine(models.Model):
    _name = 'salesperson.incentive.line'
    _description = 'Salesperson Incentive Line'

    incentive_id = fields.Many2one('salesperson.incentive', string='Incentive')
    product_id = fields.Many2one('product.product', string='Product')
    order_id = fields.Many2one('sale.order', string='Sale Order')
    date_order = fields.Datetime( string='Order Date')
    price_subtotal = fields.Float(string='Sale Amount')
    incentive_percent = fields.Float(string='Incentive %')
    total = fields.Float(string='Incentive Amount')
    currency_id = fields.Many2one('res.currency', related='incentive_id.currency_id')