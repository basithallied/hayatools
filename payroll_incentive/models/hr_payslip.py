from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def compute_sheet(self):
        res = super().compute_sheet()
        for payslip in self:
            incentive_bonus = self._get_incentive_bonus(payslip.employee_id.user_id, payslip.date_from, payslip.date_to)
            
            allowance_category = self.env['hr.salary.rule.category'].search([('code', '=', 'ALW')], limit=1)
            if not allowance_category:
                allowance_category = self.env['hr.salary.rule.category'].create({
                    'name': 'Allowance',
                    'code': 'ALW',
                })

            incentive_rule = self.env['hr.salary.rule'].search([('code', '=', 'INCENTIVE')], limit=1)
            if not incentive_rule:
                incentive_rule = self.env['hr.salary.rule'].create({
                    'name': 'Incentive Bonus',
                    'code': 'INCENTIVE',
                    'category_id': allowance_category.id,
                    'sequence': 100,
                    'condition_select': 'none',
                    'amount_select': 'fix',
                    'amount_fix': 0.0,  
                })

            if incentive_bonus > 0:
                incentive_line = {
                    'name': 'Incentive Bonus',
                    'code': 'INCENTIVE',
                    'category_id': allowance_category.id,
                    'quantity': 1.0,
                    'rate': 100.0,
                    'amount': incentive_bonus,
                    'salary_rule_id': incentive_rule.id,
                }
                payslip.write({'line_ids': [(0, 0, incentive_line)]})
        
        return res

    def _get_incentive_bonus(self, employee, date_from, date_to):
        """Fetch incentive bonus for the employee within the given period."""
        if not employee.id:
            return 0.0
        self.env.cr.execute("""
            SELECT COALESCE(SUM(incentive_bonus), 0.0)
            FROM incentive_sql_view
            WHERE sales_person = %s
            AND date >= %s
            AND date <= %s
        """, (employee.id, date_from, date_to))
        result = self.env.cr.fetchone()
        return float(result[0]) if result else 0.0


