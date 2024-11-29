from odoo import models, fields, api, _
from odoo import exceptions
from odoo.exceptions import ValidationError
import odoo.addons.decimal_precision as dp
import time
from datetime import datetime, date, time, timedelta

class BudgetSupplimentary(models.Model):
    _name = "budget.supplimentary"
    _description = "Budget Supplimentary"
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

    name = fields.Char(string='Supplimentary Name', required=True)
    date = fields.Date('Date', required=True, readonly=True, store=True, default=fields.Date.context_today)
    department_id = fields.Many2one('hr.department', string="Department", default=_default_department, readonly=True,
                                    required=True, store=True)
    branch_id = fields.Many2one('hr.branches', string="Branch", related='department_id.branch_id', store=True)
    annual_budget_id = fields.Many2one('annual.budget', string='Annual Budget', readonly=True,
                                       required=True,
                                       states={'draft': [('readonly', False)]}, domain="[('state', '=', 'approved'),('branch_id','=', branch_id)]",
                                       track_visibility='onchange')

    employee_id = fields.Many2one(comodel_name='hr.employee', string='Branch Manager', index=True, readonly=True,
                                  default=_default_employee)

    old_line_ids = fields.One2many('existing.budget.lines.supplimentary', 'supplimentary_id', string='Existing Budget Lines Supplimentary',
                               copy=True, store=True)
    new_line_ids = fields.One2many('new.budget.lines.supplimentary', 'supplimentary_id', string='New Budget Lines Supplimentary',
                               copy=True, store=True)
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft')
    amount_total = fields.Float(string='Total', store=True, readonly=True, compute='_amount_all')
    fm_comments = fields.Html('Finance Manager Comments')
    md_comments = fields.Html(string='Managing Director Comments')


    @api.depends('old_line_ids.supplimentary_amount','new_line_ids.supplimentary_amount')
    def _amount_all(self):
        for record in self:
            amount = 0.00
            for line in record.old_line_ids:
                amount += line.supplimentary_amount
            for line in record.new_line_ids:
                amount += line.supplimentary_amount
            record.update({'amount_total': amount})

    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         'Budget Supplimentary Name Must be Unique'),
    ]

    @api.multi
    def action_reject(self):
        self.write({'state': 'reject'})
        return True

    @api.multi
    def button_reset_budget(self):
        itemList = self.env['account.analytic.account'].sudo().search([])
        for item in itemList:
            budget = self.env['crossovered.budget.lines'].sudo().search([('analytic_account_id', '=', item.id)],
                                                                        limit=1)
            if budget:
                displayName = str(budget.budget_code)+ ' - ' + str(budget.budget_line_desc)
                item.sudo().write({'display_name': displayName})
        return True

    @api.multi
    def action_confirm(self):
        self.write({'state': 'confirmed'})
        return True

    @api.multi
    def action_reset(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def action_approve(self):
        allocate = []
        for line in self.old_line_ids:
            checkDeptBudget = False
            for x in allocate:
                if x == line.dept_budget_id.id:
                    checkDeptBudget = True
                    break
            if checkDeptBudget is False:
                allocate.append(line.dept_budget_id.id)

        for line in self.new_line_ids:
            checkDeptBudget = False
            for x in allocate:
                if x == line.dept_budget_id.id:
                    checkDeptBudget = True
                    break
            if checkDeptBudget is False:
                allocate.append(line.dept_budget_id.id)

        for item in allocate:
            budgetNumber = self.env["budget.supplimentary"].search_count([('annual_budget_id', '=', self.annual_budget_id.id)])
            versionNumber = self.env["budget.versions"].search_count([('parent_dept_budget_id', '=', item)])
            deptBudget = self.env["crossovered.budget"].search([('id', '=', item)])

            version = {
                'name': deptBudget.name + ' - Supplimentary ' + str(budgetNumber + 1),
                'date_from': deptBudget.date_from,
                'date_to': deptBudget.date_to,
                'company_id': deptBudget.company_id.id,
                'annual_budget_id': deptBudget.annual_budget_id.id,
                'employee_id': deptBudget.employee_id.id,
                'department_id': deptBudget.department_id.id,
                'amount_total': deptBudget.amount_total,
                'version_number': versionNumber + 1,
                'parent_dept_budget_id': deptBudget.id
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
                'version_number': versionNumber + 1,
                'annual_budget_id': self.annual_budget_id.id,
                'version_dept_budget_id': budgetVersion.id,
                'parent_dept_budget_id': deptBudget.id,
                'supplimentary_id': self.id
            }

            self.env['budget.versions'].create(versionDets)

        for line in self.old_line_ids:
            adding = line.budget_line_id.planned_amount + line.supplimentary_amount
            line.budget_line_id.write({'planned_amount':adding})

        for line in self.new_line_ids:
            newLine = {
                'crossovered_budget_id': line.dept_budget_id.id,
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
                'planned_amount': line.supplimentary_amount,
                'company_id': line.company_id.id,
            }
            self.env['crossovered.budget.lines'].create(newLine)

        self.write({'state': 'approved'})
        return True



class ExistingBudgetLinesSupplimentary(models.Model):
    _name = "existing.budget.lines.supplimentary"
    _description = "Existing Budget Lines Supplimentary"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date"

    def _default_department(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee is not None:
            return employee.department_id

    date = fields.Date('Date', required=True, readonly=True, store=True, default=fields.Date.context_today)
    supplimentary_id = fields.Many2one('budget.supplimentary', string='Budget Supplimentary', index=True,
                              ondelete='cascade',store=True)
    annual_budget_id = fields.Many2one('annual.budget', string='Annual Budget', index=True, required=True, store=True)
    dept_budget_id = fields.Many2one('crossovered.budget', string='Dept Budget', index=True, required=True, store=True)
    budget_line_id = fields.Many2one('crossovered.budget.lines', string='Budget Line',
                                     required=True)
    supplimentary_amount = fields.Float(string='Supplimentary Amount', store=True,required=True)

    @api.onchange('annual_budget_id')
    @api.depends('annual_budget_id')
    def onchange_annual_budget_id(self):
        self.dept_budget_id = None
        dept_budget_ids = []
        for dept in self.annual_budget_id.budget_ids:
            dept_budget_ids.append(dept.id)
        return {
            'domain': {'dept_budget_id': [('id', 'in', dept_budget_ids)]}}

    @api.onchange('dept_budget_id')
    @api.depends('dept_budget_id')
    def onchange_dept_budget_id(self):
        self.budget_line_id = None
        line_ids = []
        for line in self.dept_budget_id.crossovered_budget_line:
            line_ids.append(line.id)

        return {'domain': {'budget_line_id': [('id', 'in', line_ids)]}}

    @api.multi
    def send_message_on_supplimentary_lines(self):
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


class NewBudgetLinesSupplimentary(models.Model):
    _name = "new.budget.lines.supplimentary"
    _description = "New Budget Lines Supplimentary"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date"

    def _default_department(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee is not None:
            return employee.department_id

    date = fields.Date('Date', required=True, readonly=True, store=True, default=fields.Date.context_today)
    supplimentary_id = fields.Many2one('budget.supplimentary', string='Budget Supplimentary', index=True,
                              ondelete='cascade',store=True)
    annual_budget_id = fields.Many2one('annual.budget', string='Annual Budget', index=True, required=True,store=True)
    dept_budget_id = fields.Many2one('crossovered.budget', string='Dept Budget', index=True, required=True, store=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Budget Line')
    general_budget_id = fields.Many2one('account.budget.post', 'Account')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    budget_code = fields.Char(string='Budget Code', required=True, store=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True, store=True)
    account_id = fields.Many2one('account.account', string='Account Code', required=True)
    budget_group_id = fields.Many2one('budget.groups', string='Budget Group', required=True, store=True)
    budget_line_desc = fields.Text(string='Description', required=True, store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    supplimentary_amount = fields.Monetary(
        'Projected Amount', required=True,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.")
    company_id = fields.Many2one('res.company', string='Company', store=True)

    @api.onchange('annual_budget_id')
    @api.depends('annual_budget_id')
    def onchange_annual_budget_id(self):
        self.dept_budget_id = None
        dept_budget_ids = []
        for dept in self.annual_budget_id.budget_ids:
            dept_budget_ids.append(dept.id)
        return {
            'domain': {'dept_budget_id': [('id', 'in', dept_budget_ids)]}}

    @api.onchange('dept_budget_id')
    @api.depends('dept_budget_id')
    def onchange_dept_budget_id(self):
        if self.dept_budget_id:
            self.department_id = self.dept_budget_id.department_id
            self.date_from = self.dept_budget_id.date_from
            self.date_to = self.dept_budget_id.date_to

    @api.onchange('budget_group_id')
    @api.depends('budget_group_id')
    def onchange_account_id(self):
        if self.dept_budget_id:
            self.department_id = self.dept_budget_id.department_id
        if self.budget_group_id:
            self.budget_code = self.budget_group_id.group_code
            if self.budget_group_id.account_id:
                self.account_id = self.budget_group_id.account_id
        if self.budget_code:
            checkBudgetCode = False
            for line in self.dept_budget_id.crossovered_budget_line:
                if line.budget_code == self.budget_code:
                    checkBudgetCode = True
                    break
            if checkBudgetCode is True:
                raise ValidationError(
                    _(
                        "This Budget Line Exists.Please Edit it under Existing Budget Lines and not New Budget Lines for the Selected Department Budget"))
            else:
                checkAnalytic = self.env['account.analytic.account'].search(
                    [('department_id', '=', self.department_id.id), ('name', '=', self.budget_code)])
                if not checkAnalytic:
                    analytic = {
                        'name': self.budget_code,
                        'department_id': self.department_id.id,
                        'display_name': str(self.budget_code) + ' - ' + str(self.budget_line_desc),
                    }
                    analytic_id = self.env['account.analytic.account'].create(analytic)
                    self.analytic_account_id = analytic_id.id
                else:
                    self.analytic_account_id = checkAnalytic.id

        if self.account_id and self.dept_budget_id:
            checkBudgetPost = self.env['account.budget.post'].search(
                [('name', '=', self.account_id.name)])
            if not checkBudgetPost:
                account = self.env['account.account'].search(
                    [('id', '=', self.account_id.id)])
                if account:
                    budgetPost = {
                        'name': self.account_id.name,
                        'account_ids': [(4, account.id)]
                    }
                    budget_post_id = self.env['account.budget.post'].create(budgetPost)
                    self.general_budget_id = budget_post_id.id
            else:
                self.general_budget_id = checkBudgetPost.id

    @api.multi
    def send_message_on_supplimentary_lines(self):
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

