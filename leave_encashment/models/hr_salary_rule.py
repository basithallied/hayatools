from odoo import _, api, fields, models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        res = super().compute_sheet()
        for payslip in self:
            leave_encashment_amount = self._get_leave_encashment_amount(
                payslip.employee_id, payslip.date_from, payslip.date_to
            )

            encashment_category = self.env['hr.salary.rule.category'].search(
                [('code', '=', 'ENC')], limit=1
            )
            if not encashment_category:
                encashment_category = self.env['hr.salary.rule.category'].create({
                    'name': 'Leave Encashment',
                    'code': 'ENC',
                    'parent_id': self.env.ref('hr_payroll.NET', raise_if_not_found=False).id,
                })

            encashment_rule = self.env['hr.salary.rule'].search(
                [('code', '=', 'LEAVE_ENC')], limit=1
            )
            if not encashment_rule:
                encashment_rule = self.env['hr.salary.rule'].create({
                    'name': 'Leave Encashment',
                    'code': 'LEAVE_ENC',
                    'category_id': encashment_category.id,
                    'sequence': 150,
                    'condition_select': 'none',
                    'amount_select': 'fix',
                    'amount_fix': leave_encashment_amount,
                    'appears_on_payslip': True,
                    'struct_id': payslip.struct_id.id,
                })

            if leave_encashment_amount > 0:
                line_exists = payslip.line_ids.filtered(lambda l: l.code == 'LEAVE_ENC')
                if line_exists:
                    line_exists.amount = leave_encashment_amount
                else:
                    encashment_line = {
                        'name': 'Leave Encashment',
                        'code': 'LEAVE_ENC',
                        'category_id': encashment_category.id,
                        'quantity': 1.0,
                        'rate': 100.0,
                        'amount': leave_encashment_amount,
                        'salary_rule_id': encashment_rule.id,
                    }
                    payslip.write({'line_ids': [(0, 0, encashment_line)]})

                gross_rule = payslip.line_ids.filtered(lambda l: l.code == 'GROSS')
                if gross_rule:
                    current_gross = gross_rule.amount
                    gross_rule.amount = current_gross + leave_encashment_amount

                net_rule = payslip.line_ids.filtered(lambda l: l.code == 'NET')
                if net_rule:
                    current_net = net_rule.amount
                    net_rule.amount = current_net + leave_encashment_amount

        return res

    def _get_leave_encashment_amount(self, employee, date_from, date_to):
        """Fetch the total leave encashment amount for the employee within the given period."""
        if not employee:
            return 0.0
        leave_encashments = self.env['leave.encashment'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'approved'),
            ('date', '>=', date_from),
            ('date', '<=', date_to),
        ])
        return sum(encashment.amount for encashment in leave_encashments)