import time
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountAgedTrialBalance(models.TransientModel):
    _name = 'account.aged.trial.balance'
    _inherit = 'account.common.partner.report'
    _description = 'Account Aged Trial balance Report'

    period_length = fields.Integer(string='Period Length (days)', required=True, default=30)
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True)
    tags = fields.Many2many('res.partner.category', string='Tags' )
    date_from = fields.Date(default=lambda *a: time.strftime('%Y-%m-%d'))
    slab_1 = fields.Integer(string='Bucket 1', required=True, default=10)
    slab_2 = fields.Integer(string='Bucket 2', required=True, default=20)
    slab_3 = fields.Integer(string='Bucket 3', required=True, default=30)
    slab_4 = fields.Integer(string='Bucket 4', required=True, default=40)
    slab_5 = fields.Integer(string='Bucket 5', required=True, default=50)
    slab_6 = fields.Integer(string='Bucket 6', required=True, default=60)

    # def _get_report_data(self, data):
    #     res = {}
    #     data = self.pre_print_report(data)
    #     data['form'].update(self.read(['period_length'])[0])
    #     period_length = data['form']['period_length']
    #     if period_length <= 0:
    #         raise UserError(_('You must set a period length greater than 0.'))
    #     if not data['form']['date_from']:
    #         raise UserError(_('You must set a start date.'))
    #     start = data['form']['date_from']
    #     for i in range(5)[::-1]:
    #         print('rec', i)
    #         stop = start - relativedelta(days=period_length - 1)
    #         res[str(i)] = {
    #             'name': (i != 0 and (str((5 - (i + 1)) * period_length) + '-' + str((5 - i) * period_length)) or (
    #                         '+' + str(4 * period_length))),
    #             'stop': start.strftime('%Y-%m-%d'),
    #             'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
    #         }
    #         start = stop - relativedelta(days=1)
    #     data['form'].update(res)
    #     return data

    def _get_report_data(self, data):
        res = {}
        data = self.pre_print_report(data)
        print("data,data", data)
        data['form'].update(self.read(['period_length'])[0])
        data['form'].update(self.read(['slab_1'])[0])
        data['form'].update(self.read(['slab_2'])[0])
        data['form'].update(self.read(['slab_3'])[0])
        data['form'].update(self.read(['slab_4'])[0])
        data['form'].update(self.read(['slab_5'])[0])
        data['form'].update(self.read(['slab_6'])[0])
        data['form'].update(self.read(['slab_6'])[0])
        period_length = data['form']['period_length']
        slab_1 = data['form']['slab_1']
        slab_2 = data['form']['slab_2']
        slab_3 = data['form']['slab_3']
        slab_4 = data['form']['slab_4']
        slab_5 = data['form']['slab_5']
        slab_6 = data['form']['slab_6']

        data['form']['tags'] = self.tags.ids

        # if period_length <= 0:
        #     raise UserError(_('You must set a period length greater than 0.'))

        if not data['form']['date_from']:
            raise UserError(_('You must set a start date.'))
        start = data['form']['date_from']

        for i in range(7)[::-1]:
            if i == 6:
                stop = start - relativedelta(days=slab_1 - 1)
                res[str(i)] = {
                    'name': f"Upto_{slab_1}",
                    'stop': start.strftime('%Y-%m-%d'),
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop - relativedelta(days=1)
            elif i == 5:
                stop = start - relativedelta(days=(slab_2-slab_1)- 1)
                res[str(i)] = {
                    'name': f"{slab_1}_{slab_2}",
                    'stop': start.strftime('%Y-%m-%d'),
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop - relativedelta(days=1)
            elif i == 4:
                stop = start - relativedelta(days=(slab_3-slab_2) - 1)
                res[str(i)] = {
                    'name': f"{slab_2}_{slab_3}",
                    'stop': start.strftime('%Y-%m-%d'),
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop - relativedelta(days=1)
            elif i == 3:
                stop = start - relativedelta(days=(slab_4-slab_3) - 1)
                res[str(i)] = {
                    'name': f"{slab_3}_{slab_4}",
                    'stop': start.strftime('%Y-%m-%d'),
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop - relativedelta(days=1)
            elif i == 2:
                stop = start - relativedelta(days=(slab_5-slab_4) - 1)
                res[str(i)] = {
                    'name': f"{slab_4}_{slab_5}",
                    'stop': start.strftime('%Y-%m-%d'),
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop - relativedelta(days=1)

            elif i == 1:
                stop = start - relativedelta(days=(slab_6-slab_5) - 1)
                res[str(i)] = {
                    'name': f"{slab_5}_{slab_6}",
                    'stop': start.strftime('%Y-%m-%d'),
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop - relativedelta(days=1)

            elif i == 0:
                stop = start - relativedelta(days=slab_6 - 1)
                res[str(i)] = {
                    'name': f"Above_{slab_6}",
                    'stop': start.strftime('%Y-%m-%d'),
                    'start': (i != 0 and stop.strftime('%Y-%m-%d') or False),
                }
                start = stop - relativedelta(days=1)

        data['form'].update(res)
        return data

    def _print_report(self, data):
        data = self._get_report_data(data)
        return self.env.ref('accounting_pdf_reports.action_report_aged_partner_balance'). \
            with_context(landscape=True).report_action(self, data=data)
