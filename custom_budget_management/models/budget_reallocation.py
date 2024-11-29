from odoo import models, fields, api, _
from odoo import exceptions
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp
import time
from datetime import datetime, date, time, timedelta

class BudgetReallocation(models.Model):
    _name = "budget.reallocation"
    _description = "Budget Reallocation"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date"

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("confirmed", "Confirmed"),
        ("approved", "Approved"),
        ("reject", "Rejected"),
    ]

    def _default_department(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee is not None:
            return employee.department_id

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)

    name = fields.Char(string='Reallocation Name',required=True)
    date = fields.Date('Date', required=True, readonly=True,store=True,default=fields.Date.context_today)
    department_id = fields.Many2one('hr.department', string="Department", default=_default_department, readonly=True,
                                    required=True, store=True)
    branch_id = fields.Many2one('hr.branches', string="Branch", related='department_id.branch_id', store=True)
    annual_budget_id = fields.Many2one('annual.budget', string='Annual Budget', readonly=True,
                                       required=True,
                                       states={'draft': [('readonly', False)]}, domain="[('state', '=', 'approved'),('branch_id','=', branch_id)]",
                                       track_visibility='onchange')

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Requestor', index=True, readonly=True,
                                  default=_default_employee)

    line_ids = fields.One2many('budget.reallocation.lines', 'reallocation_id', string='Budget Reallocation Lines',copy=True,store=True)
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft')
    amount_total = fields.Float(string='Total', store=True, readonly=True, compute='_amount_all')


    @api.depends('line_ids.reallocation_amount')
    def _amount_all(self):
        for record in self:
            amount = 0.00
            for line in record.line_ids:
                amount += line.reallocation_amount
            record.update({'amount_total': amount})


    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         'Budget Reallocation Name Must be Unique'),
    ]

    @api.multi
    def action_reject(self):
        self.write({'state': 'reject'})
        return True

    @api.multi
    def action_reset(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def action_confirm(self):
        self.write({'state': 'confirmed'})
        return True

    @api.multi
    def action_approve(self):
        allocate = []
        for line in self.line_ids:
            checkDeptBudget = False
            for x in allocate:
                if x == line.from_dept_budget_id.id:
                    checkDeptBudget = True
                    break
            if checkDeptBudget is False:
                allocate.append(line.from_dept_budget_id.id)

            checkDeptBudget = False
            for x in allocate:
                if x == line.to_dept_budget_id.id:
                    checkDeptBudget = True
                    break
            if checkDeptBudget is False:
                allocate.append(line.to_dept_budget_id.id)

        for item in allocate:
            budgetNumber = self.env["budget.reallocation"].search_count([('annual_budget_id','=',self.annual_budget_id.id)])
            versionNumber = self.env["budget.versions"].search_count([('parent_dept_budget_id','=',item)])
            deptBudget = self.env["crossovered.budget"].search([('id','=',item)])
            version = {
                'name' : deptBudget.name + ' - Reallocation ' + str(budgetNumber + 1),
                'date_from' : deptBudget.date_from,
                'date_to' : deptBudget.date_to,
                'company_id' : deptBudget.company_id.id,
                'annual_budget_id' : deptBudget.annual_budget_id.id,
                'employee_id' : deptBudget.employee_id.id,
                'department_id': deptBudget.department_id.id,
                'amount_total' : deptBudget.amount_total,
                'version_number' : versionNumber + 1,
                'parent_dept_budget_id' : deptBudget.id
            }

            budgetVersion = self.env['crossovered.budget.version'].create(version)
            for line in deptBudget.crossovered_budget_line:
                versionLine = {
                    'crossovered_budget_version_id' : budgetVersion.id,
                    'analytic_account_id': line.analytic_account_id.id,
                    'general_budget_id': line.general_budget_id.id,
                    'date_from': line.date_from,
                    'date_to': line.date_to,
                    'budget_code': line.budget_code,
                    'department_id': line.department_id.id,
                    'account_id': line.account_id.id,
                    'budget_group_id': line.budget_group_id.id,
                    'budget_line_desc': line.budget_line_desc,
                    'currency_id': line.currency_id.id,
                    'planned_amount': line.planned_amount,
                    'company_id': line.company_id.id
                }

                self.env['crossovered.budget.version.lines'].create(versionLine)


            versionDets = {
                'version_number' : versionNumber+1,
                'annual_budget_id' : self.annual_budget_id.id,
                'version_dept_budget_id' : budgetVersion.id,
                'parent_dept_budget_id' : deptBudget.id,
                'reallocation_id' : self.id
            }

            self.env['budget.versions'].create(versionDets)

        for line in self.line_ids:
            rem = line.from_budget_line_id.planned_amount - line.reallocation_amount
            adding = line.to_budget_line_id.planned_amount + line.reallocation_amount

            line.from_budget_line_id.write({'planned_amount':rem})
            line.to_budget_line_id.write({'planned_amount':adding})

        self.write({'state': 'approved'})


class BudgetReallocationLines(models.Model):
    _name = "budget.reallocation.lines"
    _description = "Budget Reallocation Lines"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date"

    def _default_department(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee is not None:
            return employee.department_id

    date = fields.Date('Date', required=True, readonly=True, store=True, default=fields.Date.context_today)
    reallocation_id = fields.Many2one('budget.reallocation', string='Budget Reallocation', index=True,
                              ondelete='cascade',store=True)
    annual_budget_id = fields.Many2one('annual.budget', string='Annual Budget', index=True, required=True,store=True)
    from_dept_budget_id = fields.Many2one('crossovered.budget', string='From Dept Budget', index=True,store=True)
    from_budget_line_id = fields.Many2one('crossovered.budget.lines', string='From Budget Line',
                                     required=True)
    to_dept_budget_id = fields.Many2one('crossovered.budget', string='To Dept Budget', index=True, store=True)
    to_budget_line_id = fields.Many2one('crossovered.budget.lines', string='To Budget Line',
                                          required=True)
    reallocation_amount = fields.Float(string='Reallocation Amount', store=True,required=True)

    @api.onchange('annual_budget_id')
    @api.depends('annual_budget_id')
    def onchange_annual_budget_id(self):
        dept_budget_ids = []
        for dept in self.annual_budget_id.budget_ids:
            dept_budget_ids.append(dept.id)
        return {
            'domain': {'from_dept_budget_id': [('id', 'in', dept_budget_ids)], 'to_dept_budget_id': [('id', 'in', dept_budget_ids)]}}

    @api.onchange('from_dept_budget_id')
    @api.depends('from_dept_budget_id')
    def onchange_from_dept_budget_id(self):
        line_ids = []
        for line in self.from_dept_budget_id.crossovered_budget_line:
            line_ids.append(line.id)

        return {'domain': {'from_budget_line_id': [('id', 'in', line_ids)]}}


    @api.onchange('to_dept_budget_id')
    @api.depends('to_dept_budget_id')
    def onchange_to_dept_budget_id(self):
        line_ids = []
        for line in self.to_dept_budget_id.crossovered_budget_line:
            line_ids.append(line.id)

        return {'domain': {'to_budget_line_id': [('id','in',line_ids)]}}

    @api.onchange('reallocation_amount')
    @api.depends('reallocation_amount')
    def onchange_budget_code_id(self):
        if self.from_budget_line_id:
            rem = self.from_budget_line_id.planned_amount - self.from_budget_line_id.practical_amount
            if self.reallocation_amount >= rem:
                raise ValidationError(
                    _("Please Enter an Amount Less Than the Remaining Amount That can be Reallocated for the Budget Line."))

    @api.multi
    def send_message_on_reallocation_lines(self):
        return {
            'name': 'New Message',
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'views': [(False, 'form')],
            'flags': {'action_buttons': True},
        }


