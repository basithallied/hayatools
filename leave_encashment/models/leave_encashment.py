from odoo import models, fields, api
from odoo.exceptions import ValidationError

class LeaveEncashment(models.Model):
    _name = 'leave.encashment'
    _description = 'Leave Encashment'

    name = fields.Char(string='Reference', readonly=True, default=lambda self: 'New')
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    leave_encash = fields.Float(string='Leave Encash', required=True)
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True)
    amount = fields.Float(string='Amount', required=True)
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id', readonly=True)
    job_position = fields.Char(string='Job Position', related='employee_id.job_title', readonly=True)
    leave_type_id = fields.Many2one('hr.leave.type', string='Leave Type', required=True)
    leave_pending = fields.Float(string='Leave Pending', compute='_compute_leave_pending', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approved', 'Approved'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True)

    def action_submit(self):
        self.write({'state': 'submit'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    @api.constrains('leave_encash', 'leave_pending')
    def _check_leave_encashment(self):
        for record in self:
            if record.leave_encash > record.leave_pending:
                raise ValidationError("The Leave Encashment cannot be greater than the Leave Pending.")

    @api.depends('employee_id', 'leave_type_id')
    def _compute_leave_pending(self):
        for record in self:
            if record.employee_id and record.leave_type_id:
                self.env.cr.execute("""
                    SELECT COALESCE(SUM(number_of_days), 0)
                    FROM hr_leave_employee_type_report
                    WHERE employee_id = %s
                    AND leave_type = %s
                    AND holiday_status = 'left'
                """, (record.employee_id.id, record.leave_type_id.id))
                result = self.env.cr.fetchone()
                record.leave_pending = result[0] if result else 0.0
            else:
                record.leave_pending = 0.0