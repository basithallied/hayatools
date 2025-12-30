import time
from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero
from datetime import datetime
from dateutil.relativedelta import relativedelta


class ReportAgedPartnerBalance(models.AbstractModel):
    _name = 'report.accounting_pdf_reports.report_agedpartnerbalance'
    _description = 'Aged Partner Balance Report'

    def _get_partner_move_lines(self, account_type, partner_ids,
                                date_from, target_move, period_length,slab_1,slab_2,slab_3,slab_4,slab_5,slab_6,tags):
        # This method can receive the context key 'include_nullified_amount' {Boolean}
        # Do an invoice and a payment and unreconcile. The amount will be nullified
        # By default, the partner wouldn't appear in this report.
        # The context key allow it to appear
        # In case of a period_length of 30 days as of 2019-02-08, we want the following periods:
        # Name       Stop         Start
        # 1 - 30   : 2019-02-07 - 2019-01-09
        # 31 - 60  : 2019-01-08 - 2018-12-10
        # 61 - 90  : 2018-12-09 - 2018-11-10
        # 91 - 120 : 2018-11-09 - 2018-10-11
        # +120     : 2018-10-10
        periods = {}
        start = datetime.strptime(str(date_from), "%Y-%m-%d")
        date_from = datetime.strptime(str(date_from), "%Y-%m-%d").date()
        for i in range(7)[::-1]:
            if i ==6:
                stop = start - relativedelta(days=slab_1)
                period_name = str(0) + '-' + str(slab_1)
                period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
                periods[str(i)] = {
                    'name': period_name,
                    'stop': period_stop,
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop

            elif i==5:
                stop = start - relativedelta(days=slab_2 - slab_1)
                period_name = str(slab_1) + '-' + str(slab_2)
                period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
                periods[str(i)] = {
                    'name': period_name,
                    'stop': period_stop,
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop
            elif i==4:
                stop = start - relativedelta(days=slab_3 - slab_2)
                period_name = str(slab_2) + '-' + str(slab_3)
                period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
                periods[str(i)] = {
                    'name': period_name,
                    'stop': period_stop,
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop
            elif i==3:
                stop = start - relativedelta(days=slab_4 - slab_3)
                period_name = str(slab_3) + '-' + str(slab_4)
                period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
                periods[str(i)] = {
                    'name': period_name,
                    'stop': period_stop,
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop

            elif i==2:
                stop = start - relativedelta(days=slab_5 - slab_4)
                period_name = str(slab_4) + '-' + str(slab_5)
                period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
                periods[str(i)] = {
                    'name': period_name,
                    'stop': period_stop,
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop

            elif i==1:
                stop = start - relativedelta(days=slab_6 - slab_5)
                period_name = str(slab_5) + '-' + str(slab_6)
                period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
                periods[str(i)] = {
                    'name': period_name,
                    'stop': period_stop,
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop


            if i == 0:
                stop = start - relativedelta(days=slab_6)
                period_name = 'above' + str(slab_6)
                period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
                periods[str(i)] = {
                    'name': period_name,
                    'stop': period_stop,
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop

        res = []
        total = []
        cr = self.env.cr
        user_company = self.env.user.company_id
        user_currency = user_company.currency_id
        company_ids = self._context.get('company_ids') or [user_company.id]
        move_state = ['draft', 'posted']
        date = self._context.get('date') or fields.Date.today()
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company

        if target_move == 'posted':
            move_state = ['posted']
        arg_list = (tuple(move_state), tuple(account_type))

        reconciliation_clause = '(l.reconciled IS FALSE)'
        cr.execute('SELECT debit_move_id, credit_move_id FROM account_partial_reconcile where max_date > %s', (date_from,))
        reconciled_after_date = []
        for row in cr.fetchall():
            reconciled_after_date += [row[0], row[1]]
        if reconciled_after_date:
            reconciliation_clause = '(l.reconciled IS FALSE OR l.id IN %s)'
            arg_list += (tuple(reconciled_after_date),)
        arg_list += (date_from, tuple(company_ids))
        query = '''
            SELECT DISTINCT l.partner_id, UPPER(res_partner.name)
            FROM account_move_line AS l left join res_partner on l.partner_id = res_partner.id, account_account, account_move am
            WHERE (l.account_id = account_account.id)
                AND (l.move_id = am.id)
                AND (am.state IN %s)
                AND (account_account.account_type IN %s)
                AND ''' + reconciliation_clause + '''
                AND (l.date <= %s)
                AND l.company_id IN %s
            ORDER BY UPPER(res_partner.name)'''
        cr.execute(query, arg_list)
        partners = cr.dictfetchall()
        # put a total of 0
        for i in range(9):
            total.append(0)

        # Build a string like (1,2,3) for easy use in SQL query
        if not partner_ids:
            if not tags:
                partner_ids = [partner['partner_id'] for partner in partners if partner['partner_id']]
            else:
                partner_ids = [partner['partner_id'] for partner in partners if partner.get('partner_id') and any( items in tags for items in self.env['res.partner'].browse(partner['partner_id']).category_id.ids)]

        lines = dict((partner['partner_id'] or False, []) for partner in partners)
        if not partner_ids:
            return [], [], {}

        if partner_ids and tags:
            for check in partner_ids:
                partner = self.env['res.partner'].browse(int(check))
                if not any( item in tags for item in partner.category_id.ids):
                    partner_ids.remove(check)
        if not partner_ids:
            return [], [], {}


        # This dictionary will store the not due amount of all partners
        undue_amounts = {}
        query = '''SELECT l.id
                FROM account_move_line AS l, account_account, account_move am
                WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                    AND (am.state IN %s)
                    AND (account_account.account_type IN %s)
                    AND (COALESCE(l.date_maturity,l.date) >= %s)\
                    AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                AND (l.date <= %s)
                AND l.company_id IN %s'''
        cr.execute(query, (tuple(move_state), tuple(account_type), date_from,
                           tuple(partner_ids), date_from, tuple(company_ids)))
        aml_ids = cr.fetchall()
        aml_ids = aml_ids and [x[0] for x in aml_ids] or []
        for line in self.env['account.move.line'].browse(aml_ids):
            partner_id = line.partner_id.id or False
            if partner_id not in undue_amounts:
                undue_amounts[partner_id] = 0.0
            line_amount = line.company_id.currency_id._convert(line.balance,
                                                               user_currency,
                                                               company, date)
            if user_currency.is_zero(line_amount):
                continue
            for partial_line in line.matched_debit_ids:
                if partial_line.max_date <= date_from:
                    line_currency = partial_line.company_id.currency_id
                    line_amount += line_currency._convert(partial_line.amount,
                                                          user_currency,
                                                          company, date)
            for partial_line in line.matched_credit_ids:
                if partial_line.max_date <= date_from:
                    line_currency = partial_line.company_id.currency_id
                    line_amount -= line_currency._convert(partial_line.amount,
                                                          user_currency,
                                                          company, date)
            if not self.env.user.company_id.currency_id.is_zero(line_amount):
                undue_amounts[partner_id] += line_amount
                lines[partner_id].append({
                    'line': line,
                    'amount': line_amount,
                    'period': 6,
                })

        # Use one query per period and store results in history (a list variable)
        # Each history will contain: history[1] = {'<partner_id>': <partner_debit-credit>}
        history = []
        for i in range(7):
            args_list = (tuple(move_state), tuple(account_type), tuple(partner_ids),)
            dates_query = '(COALESCE(l.date_maturity,l.date)'

            if periods[str(i)]['start'] and periods[str(i)]['stop']:
                dates_query += ' BETWEEN %s AND %s)'
                args_list += (periods[str(i)]['start'], periods[str(i)]['stop'])
            elif periods[str(i)]['start']:
                dates_query += ' >= %s)'
                args_list += (periods[str(i)]['start'],)
            else:
                dates_query += ' <= %s)'
                args_list += (periods[str(i)]['stop'],)
            args_list += (date_from, tuple(company_ids))

            query = '''SELECT l.id
                    FROM account_move_line AS l, account_account, account_move am
                    WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
                        AND (am.state IN %s)
                        AND (account_account.account_type IN %s)
                        AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
                        AND ''' + dates_query + '''
                    AND (l.date <= %s)
                    AND l.company_id IN %s'''
            cr.execute(query, args_list)
            partners_amount = {}
            aml_ids = cr.fetchall()
            aml_ids = aml_ids and [x[0] for x in aml_ids] or []
            for line in self.env['account.move.line'].browse(aml_ids):
                partner_id = line.partner_id.id or False
                if partner_id not in partners_amount:
                    partners_amount[partner_id] = 0.0
                line_currency_id = line.company_id.currency_id
                line_amount = line_currency_id._convert(line.balance, user_currency, company, date)
                if user_currency.is_zero(line_amount):
                    continue
                for partial_line in line.matched_debit_ids:
                    if partial_line.max_date <= date_from:
                        line_currency_id = partial_line.company_id.currency_id
                        line_amount += line_currency_id._convert(
                            partial_line.amount, user_currency, company, date)
                for partial_line in line.matched_credit_ids:
                    if partial_line.max_date <= date_from:
                        line_currency_id = partial_line.company_id.currency_id
                        line_amount -= line_currency_id._convert(
                            partial_line.amount, user_currency, company, date)
                if not self.env.user.company_id.currency_id.is_zero(line_amount):
                    partners_amount[partner_id] += line_amount
                    lines[partner_id].append({
                        'line': line,
                        'amount': line_amount,
                        'period': i + 1,
                        })
            history.append(partners_amount)

        for partner in partners:
            if partner['partner_id'] is None:
                partner['partner_id'] = False
            at_least_one_amount = False
            values = {}
            undue_amt = 0.0
            if partner['partner_id'] in undue_amounts:  # Making sure this partner actually was found by the query
                undue_amt = undue_amounts[partner['partner_id']]

            total[8] = total[8] + undue_amt
            values['direction'] = undue_amt
            if not float_is_zero(values['direction'], precision_rounding=self.env.user.company_id.currency_id.rounding):
                at_least_one_amount = True

            for i in range(7):
                during = False
                if partner['partner_id'] in history[i]:
                    during = [history[i][partner['partner_id']]]
                # Adding counter
                total[(i)] = total[(i)] + (during and during[0] or 0)
                values[str(i)] = during and during[0] or 0.0
                if not float_is_zero(values[str(i)],
                                     precision_rounding=self.env.user.company_id.currency_id.rounding):
                    at_least_one_amount = True
            values['total'] = sum([values['direction']] + [values[str(i)] for i in range(7)])
            ## Add for total
            total[(i + 1)] += values['total']
            values['partner_id'] = partner['partner_id']
            if partner['partner_id']:
                browsed_partner = self.env['res.partner'].browse(partner['partner_id'])

                #Remove partner name last ... coming for haya

                # values['name'] = browsed_partner.name and len(
                #     browsed_partner.name) >= 45 and browsed_partner.name[
                #                                     0:40] + '...' or browsed_partner.name
                values['name'] =  browsed_partner.name
                values['trust'] = browsed_partner.trust
            else:
                values['name'] = _('Unknown Partner')
                values['trust'] = False

            if at_least_one_amount or (self._context.get('include_nullified_amount') and lines[partner['partner_id']]):
                res.append(values)

        if res:
            for rec in res:
                partner = self.env['res.partner'].browse(int(rec['partner_id']))
                if partner.unreconciled_aml_ids:
                    aml_list = []
                    for aml in partner.unreconciled_aml_ids:
                        dic = {}
                        dic = {'date': str(aml.date.strftime("%d/%m/%Y")),'move_name':aml.move_id.name, 'date_maturity':str(aml.date_maturity.strftime("%d/%m/%Y")),'result':aml.result,'amount_residual':aml.amount_residual,'journal':aml.move_id.journal_id.name, 'od_days':aml.overdue_by_days}
                        aml_list.append(dic)
                    rec['payment_followp'] = aml_list
                else:
                    rec['payment_followp'] = []

        return res, total, lines


    # def _get_partner_move_lines(self, account_type, partner_ids,
    #                             date_from, target_move, period_length,slab_1,slab_2,slab_3,slab_4,slab_5,slab_6):
    #     # This method can receive the context key 'include_nullified_amount' {Boolean}
    #     # Do an invoice and a payment and unreconcile. The amount will be nullified
    #     # By default, the partner wouldn't appear in this report.
    #     # The context key allow it to appear
    #     # In case of a period_length of 30 days as of 2019-02-08, we want the following periods:
    #     # Name       Stop         Start
    #     # 1 - 30   : 2019-02-07 - 2019-01-09
    #     # 31 - 60  : 2019-01-08 - 2018-12-10
    #     # 61 - 90  : 2018-12-09 - 2018-11-10
    #     # 91 - 120 : 2018-11-09 - 2018-10-11
    #     # +120     : 2018-10-10
    #     periods = {}
    #     start = datetime.strptime(str(date_from), "%Y-%m-%d")
    #     date_from = datetime.strptime(str(date_from), "%Y-%m-%d").date()
    #     for i in range(5)[::-1]:
    #         stop = start - relativedelta(days=period_length)
    #         period_name = str((5 - (i + 1)) * period_length + 1) + '-' + str((5 - i) * period_length)
    #         period_stop = (start - relativedelta(days=1)).strftime('%Y-%m-%d')
    #         if i == 0:
    #             period_name = '+' + str(4 * period_length)
    #         periods[str(i)] = {
    #             'name': period_name,
    #             'stop': period_stop,
    #             'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
    #         }
    #         start = stop
    #
    #     print('periods',periods)
    #
    #     res = []
    #     total = []
    #     cr = self.env.cr
    #     user_company = self.env.user.company_id
    #     user_currency = user_company.currency_id
    #     company_ids = self._context.get('company_ids') or [user_company.id]
    #     move_state = ['draft', 'posted']
    #     date = self._context.get('date') or fields.Date.today()
    #     company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
    #
    #     if target_move == 'posted':
    #         move_state = ['posted']
    #     arg_list = (tuple(move_state), tuple(account_type))
    #
    #     reconciliation_clause = '(l.reconciled IS FALSE)'
    #     cr.execute('SELECT debit_move_id, credit_move_id FROM account_partial_reconcile where max_date > %s', (date_from,))
    #     reconciled_after_date = []
    #     for row in cr.fetchall():
    #         reconciled_after_date += [row[0], row[1]]
    #     print('reconciled_after_date', reconciled_after_date)
    #     if reconciled_after_date:
    #         reconciliation_clause = '(l.reconciled IS FALSE OR l.id IN %s)'
    #         arg_list += (tuple(reconciled_after_date),)
    #     arg_list += (date_from, tuple(company_ids))
    #     query = '''
    #         SELECT DISTINCT l.partner_id, UPPER(res_partner.name)
    #         FROM account_move_line AS l left join res_partner on l.partner_id = res_partner.id, account_account, account_move am
    #         WHERE (l.account_id = account_account.id)
    #             AND (l.move_id = am.id)
    #             AND (am.state IN %s)
    #             AND (account_account.account_type IN %s)
    #             AND ''' + reconciliation_clause + '''
    #             AND (l.date <= %s)
    #             AND l.company_id IN %s
    #         ORDER BY UPPER(res_partner.name)'''
    #     cr.execute(query, arg_list)
    #     partners = cr.dictfetchall()
    #
    #     print('partners334',partners)
    #     # put a total of 0
    #     for i in range(7):
    #         total.append(0)
    #     print('total334', total)
    #     # Build a string like (1,2,3) for easy use in SQL query
    #     if not partner_ids:
    #         partner_ids = [partner['partner_id'] for partner in partners if partner['partner_id']]
    #     lines = dict((partner['partner_id'] or False, []) for partner in partners)
    #     if not partner_ids:
    #         return [], [], {}
    #
    #     # This dictionary will store the not due amount of all partners
    #     undue_amounts = {}
    #     query = '''SELECT l.id
    #             FROM account_move_line AS l, account_account, account_move am
    #             WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
    #                 AND (am.state IN %s)
    #                 AND (account_account.account_type IN %s)
    #                 AND (COALESCE(l.date_maturity,l.date) >= %s)\
    #                 AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
    #             AND (l.date <= %s)
    #             AND l.company_id IN %s'''
    #     cr.execute(query, (tuple(move_state), tuple(account_type), date_from,
    #                        tuple(partner_ids), date_from, tuple(company_ids)))
    #     aml_ids = cr.fetchall()
    #     aml_ids = aml_ids and [x[0] for x in aml_ids] or []
    #     for line in self.env['account.move.line'].browse(aml_ids):
    #         partner_id = line.partner_id.id or False
    #         if partner_id not in undue_amounts:
    #             undue_amounts[partner_id] = 0.0
    #         line_amount = line.company_id.currency_id._convert(line.balance,
    #                                                            user_currency,
    #                                                            company, date)
    #         if user_currency.is_zero(line_amount):
    #             continue
    #         for partial_line in line.matched_debit_ids:
    #             if partial_line.max_date <= date_from:
    #                 line_currency = partial_line.company_id.currency_id
    #                 line_amount += line_currency._convert(partial_line.amount,
    #                                                       user_currency,
    #                                                       company, date)
    #         for partial_line in line.matched_credit_ids:
    #             if partial_line.max_date <= date_from:
    #                 line_currency = partial_line.company_id.currency_id
    #                 line_amount -= line_currency._convert(partial_line.amount,
    #                                                       user_currency,
    #                                                       company, date)
    #         if not self.env.user.company_id.currency_id.is_zero(line_amount):
    #             undue_amounts[partner_id] += line_amount
    #             lines[partner_id].append({
    #                 'line': line,
    #                 'amount': line_amount,
    #                 'period': 6,
    #             })
    #
    #
    #     print('undue_amounts@2',undue_amounts)
    #
    #     # Use one query per period and store results in history (a list variable)
    #     # Each history will contain: history[1] = {'<partner_id>': <partner_debit-credit>}
    #     history = []
    #     for i in range(5):
    #         args_list = (tuple(move_state), tuple(account_type), tuple(partner_ids),)
    #         dates_query = '(COALESCE(l.date_maturity,l.date)'
    #
    #         if periods[str(i)]['start'] and periods[str(i)]['stop']:
    #             dates_query += ' BETWEEN %s AND %s)'
    #             args_list += (periods[str(i)]['start'], periods[str(i)]['stop'])
    #         elif periods[str(i)]['start']:
    #             dates_query += ' >= %s)'
    #             args_list += (periods[str(i)]['start'],)
    #         else:
    #             dates_query += ' <= %s)'
    #             args_list += (periods[str(i)]['stop'],)
    #         args_list += (date_from, tuple(company_ids))
    #
    #         query = '''SELECT l.id
    #                 FROM account_move_line AS l, account_account, account_move am
    #                 WHERE (l.account_id = account_account.id) AND (l.move_id = am.id)
    #                     AND (am.state IN %s)
    #                     AND (account_account.account_type IN %s)
    #                     AND ((l.partner_id IN %s) OR (l.partner_id IS NULL))
    #                     AND ''' + dates_query + '''
    #                 AND (l.date <= %s)
    #                 AND l.company_id IN %s'''
    #         cr.execute(query, args_list)
    #         partners_amount = {}
    #         aml_ids = cr.fetchall()
    #         aml_ids = aml_ids and [x[0] for x in aml_ids] or []
    #         for line in self.env['account.move.line'].browse(aml_ids):
    #             partner_id = line.partner_id.id or False
    #             if partner_id not in partners_amount:
    #                 partners_amount[partner_id] = 0.0
    #             line_currency_id = line.company_id.currency_id
    #             line_amount = line_currency_id._convert(line.balance, user_currency, company, date)
    #             if user_currency.is_zero(line_amount):
    #                 continue
    #             for partial_line in line.matched_debit_ids:
    #                 if partial_line.max_date <= date_from:
    #                     line_currency_id = partial_line.company_id.currency_id
    #                     line_amount += line_currency_id._convert(
    #                         partial_line.amount, user_currency, company, date)
    #             for partial_line in line.matched_credit_ids:
    #                 if partial_line.max_date <= date_from:
    #                     line_currency_id = partial_line.company_id.currency_id
    #                     line_amount -= line_currency_id._convert(
    #                         partial_line.amount, user_currency, company, date)
    #             if not self.env.user.company_id.currency_id.is_zero(line_amount):
    #                 partners_amount[partner_id] += line_amount
    #                 lines[partner_id].append({
    #                     'line': line,
    #                     'amount': line_amount,
    #                     'period': i + 1,
    #                 })
    #         history.append(partners_amount)
    #
    #     print("history@12",history)
    #
    #     for partner in partners:
    #         if partner['partner_id'] is None:
    #             partner['partner_id'] = False
    #         at_least_one_amount = False
    #         values = {}
    #         undue_amt = 0.0
    #         if partner['partner_id'] in undue_amounts:  # Making sure this partner actually was found by the query
    #             undue_amt = undue_amounts[partner['partner_id']]
    #
    #         total[6] = total[6] + undue_amt
    #         values['direction'] = undue_amt
    #         if not float_is_zero(values['direction'], precision_rounding=self.env.user.company_id.currency_id.rounding):
    #             at_least_one_amount = True
    #
    #         for i in range(5):
    #             during = False
    #             if partner['partner_id'] in history[i]:
    #                 during = [history[i][partner['partner_id']]]
    #             # Adding counter
    #             total[(i)] = total[(i)] + (during and during[0] or 0)
    #             values[str(i)] = during and during[0] or 0.0
    #             if not float_is_zero(values[str(i)],
    #                                  precision_rounding=self.env.user.company_id.currency_id.rounding):
    #                 at_least_one_amount = True
    #         values['total'] = sum([values['direction']] + [values[str(i)] for i in range(5)])
    #         ## Add for total
    #         total[(i + 1)] += values['total']
    #         values['partner_id'] = partner['partner_id']
    #         if partner['partner_id']:
    #             browsed_partner = self.env['res.partner'].browse(partner['partner_id'])
    #             values['name'] = browsed_partner.name and len(
    #                 browsed_partner.name) >= 45 and browsed_partner.name[
    #                                                 0:40] + '...' or browsed_partner.name
    #             values['trust'] = browsed_partner.trust
    #         else:
    #             values['name'] = _('Unknown Partner')
    #             values['trust'] = False
    #
    #         if at_least_one_amount or (self._context.get('include_nullified_amount') and lines[partner['partner_id']]):
    #             res.append(values)
    #         print('values@##',values)
    #
    #     return res, total, lines

    # unreconciled_aml_ids

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model') or not self.env.context.get('active_id'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        docs = self.env[model].browse(self.env.context.get('active_id'))

        target_move = data['form'].get('target_move', 'all')
        date_from = data['form'].get('date_from', time.strftime('%Y-%m-%d'))

        if data['form']['result_selection'] == 'customer':
            account_type = ['asset_receivable']
        elif data['form']['result_selection'] == 'supplier':
            account_type = ['liability_payable']
        else:
            account_type = ['asset_receivable', 'liability_payable']
        partner_ids = data['form']['partner_ids']
        tags_ids = data['form']['tags']
        movelines, total, dummy = self._get_partner_move_lines(
            account_type, partner_ids, date_from, target_move,data['form']['period_length'], data['form']['slab_1'], data['form']['slab_2'], data['form']['slab_3'],data['form']['slab_4'],data['form']['slab_5'],data['form']['slab_6'],tags_ids,
        )
        return {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data['form'],
            'docs': docs,
            'time': time,
            'get_partner_lines': movelines,
            'get_direction': total,
        }
