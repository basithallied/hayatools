from odoo import models,fields


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        res = super().compute_sheet()
        for payslip in self:
            overtime_hour = self._get_overtime_wage(payslip.employee_id.id, payslip.date_from, payslip.date_to)
            overtime_wage = overtime_hour * payslip.contract_id.overtime_hourly_wage
            allowance_category = self.env['hr.salary.rule.category'].search([('code', '=', 'OT')], limit=1)
            if not allowance_category:
                allowance_category = self.env['hr.salary.rule.category'].create({
                    'name': 'OverTime Allowance',
                    'code': 'OT',
                })

            overtime_rule = self.env['hr.salary.rule'].search([('code', '=', 'OT WAGE')], limit=1)
            if not overtime_rule:
                overtime_rule = self.env['hr.salary.rule'].create({
                    'name': 'OverTime Wage',
                    'code': 'OT WAGE',
                    'category_id': allowance_category.id,
                    'sequence': 100,
                    'condition_select': 'none',
                    'amount_select': 'fix',
                    'amount_fix': 0.0,  
                })

            if overtime_wage > 0:
                ot_wage_line = {
                    'name': 'OverTime Wage',
                    'code': 'OT WAGE',
                    'category_id': allowance_category.id,
                    'quantity': 1.0,
                    'rate': 100.0,
                    'amount': overtime_wage,
                    'salary_rule_id': overtime_rule.id,
                }
                payslip.write({'line_ids': [(0, 0, ot_wage_line)]})
        
        return res
    
    def _get_overtime_wage(self, employee, date_from, date_to):
        """Fetch Overtime Wage for the employee within the given period."""
        if not employee:
            return 0.0
        sql_query = f"""SELECT COALESCE(SUM(validated_overtime_hours), 0.0)
            FROM hr_attendance
            WHERE employee_id = {employee} AND
            (check_in::DATE, check_out::DATE) OVERLAPS (DATE '{date_from}', DATE '{date_to}')
        """
        self.env.cr.execute(sql_query)
        result = self.env.cr.fetchone()
        return round(result[0]) if result else 0.0