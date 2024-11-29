from odoo import models, fields, api, _
from odoo import exceptions
from odoo.exceptions import ValidationError


class BudgetVersions(models.Model):
    _name = "budget.versions"
    _description = "Budget Versions"
    _order = "version_number desc"

    date = fields.Date('Date', required=True, readonly=True, store=True, default=fields.Date.context_today)
    version_number = fields.Integer(string='Version Number',default=1,required=True)
    annual_budget_id = fields.Many2one('annual.budget', string='Annual Budget', index=True, required=True, store=True)
    version_dept_budget_id = fields.Many2one('crossovered.budget.version', string='Department Budget Version', index=True, required=True, store=True)
    parent_dept_budget_id = fields.Many2one('crossovered.budget', string='Parent Department Budget', index=True, required=True, store=True)
    reallocation_id = fields.Many2one('budget.reallocation', string='Budget Reallocation', store=True)
    supplimentary_id = fields.Many2one('budget.supplimentary', string='Budget Supplimentary', store=True)


class CrossoveredBudgetVersion(models.Model):
    _name = "crossovered.budget.version"
    _description = "Dept Budget Version"

    date = fields.Date('Date', required=True, readonly=True, store=True, default=fields.Date.context_today)
    version_number = fields.Integer(string='Version Number', default=1, required=True)
    parent_dept_budget_id = fields.Many2one('crossovered.budget', string='Parent Department Budget', index=True,
                                            required=True, store=True)
    name = fields.Char('Budget Version Name', required=True)
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    line_ids = fields.One2many('crossovered.budget.version.lines', 'crossovered_budget_version_id', 'Budget Version Lines')
    company_id = fields.Many2one('res.company', 'Company', required=True)
    annual_budget_id = fields.Many2one('annual.budget', string='Annual Budget')
    employee_id = fields.Many2one('hr.employee', string='HOD', index=True)
    department_id = fields.Many2one('hr.department',string="Department")
    amount_total = fields.Float(string='Total', store=True)


class CrossoveredBudgetVersionLines(models.Model):
    _name = 'crossovered.budget.version.lines'
    _description = "Dept Budget Version Lines"

    crossovered_budget_version_id = fields.Many2one('crossovered.budget.version', 'Dept Budget Version', ondelete='cascade', index=True,
                                            required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', 'Budget Line')
    general_budget_id = fields.Many2one('account.budget.post', 'Account')
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    budget_code = fields.Char(string='Budget Code', required=True, store=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True, store=True)
    account_id = fields.Many2one('account.account', string='Account Code', required=True)
    budget_group_id = fields.Many2one('budget.groups', string='Activity', required=True, store=True)
    budget_line_desc = fields.Text(string='Description', required=True, store=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    planned_amount = fields.Monetary(
        'Planned Amount', required=True,
        help="Amount you plan to earn/spend. Record a positive amount if it is a revenue and a negative amount if it is a cost.")
    company_id = fields.Many2one('res.company', string='Company', store=True)
