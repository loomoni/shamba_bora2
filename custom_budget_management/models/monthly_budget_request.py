# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo import exceptions
from odoo.exceptions import ValidationError
from datetime import datetime

class ConsolidatedMonthlyBudget(models.Model):
    _name = "monthly.budget.consolidated"
    _description = "Monthly Budget"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date_start"

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("released", "Released"),
        ("recommended", "Recommend"),
        ("consolidated", "Consolidated"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    @api.depends('budget_ids', 'budget_ids.amount_total')
    def _compute_total_budget_amount(self):
        for rec in self:
            for budget in rec.budget_ids:
                for line in budget.crossovered_budget_line:
                    if line.budget_group_id.group_type == "outflow":
                        rec.total_budget_amount += line.planned_amount

    name = fields.Char(string='Monthly Budget Name', index=True,required=True)
    branch_id = fields.Many2one('hr.branches', string='Branch', required=True, readonly=True, states={'draft': [('readonly', False)]}, store=True)
    date_start = fields.Date(string=' Start Budget Period Date', required=True,
                                 readonly=True, states={'draft': [('readonly', False)]})
    date_end = fields.Date(string='End Budget Period Date', required=True,
                               readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft')
    annual_budget_id = fields.Many2one('annual.budget', string='Annual Budget', readonly=True,
                                       required=True,
                                       states={'draft': [('readonly', False)]},
                                       domain="[('state', '=', 'approved'),('branch_id','=', branch_id)]",
                                       track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', related='annual_budget_id.currency_id', store=True)
    monthly_budget_ids = fields.One2many('monthly.budget.request', 'consolidated_monthly_budget_id', string='Department Monthly Budgets',
                               readonly=True, store=True, domain=['|',('state','=','approved'),('state','=','submit')])
    total_budget_amount = fields.Float(string='Total Requested Amount', compute='_compute_total_mbudget_amount')

    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         'Consolidated Monthly Budget Name Must be Unique'),
    ]

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if self.date_start >= self.date_end or self.date_end < fields.Date.today():
            raise exceptions.Warning('Please check budget dates!')
        if self.env['monthly.budget.consolidated'].search(
                [('state', '=', 'approved'), ('date_end', '>', self.date_start), ('branch_id','=',self.branch_id.id)]):
            raise exceptions.Warning(
                'Please check budget dates.There is a monthly budget version for the specified period for the specified branch!')


    @api.depends('monthly_budget_ids', 'monthly_budget_ids.request_total')
    def _compute_total_mbudget_amount(self):
        for rec in self:
            for budget in rec.monthly_budget_ids:
                for line in budget.line_ids:
                    rec.total_budget_amount += line.request_amount

    @api.multi
    def button_reject(self):
        self.write({'state': 'rejected'})
        return True

    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        for line in self.monthly_budget_ids:
            line.write({'state': 'draft'})
        return True

    @api.multi
    def button_release(self):
        self.write({'state': 'released'})
        depts = self.env['hr.department'].sudo().search([('branch_id','=',self.branch_id.id)])
        for dept in depts:
            if dept.manager_id and dept.manager_id.user_id:
                mail_content = "Dear HOD," + "<br>The Monthly Budget Version of Period "+ str(self.date_start)+" - "+str(self.date_end) + " Has Been Released.Please Add Your Department Budget Lines"
                values = {'model': 'monthly.budget.consolidated',
                          'res_id': self.id,
                          'subject': "Monthly Budget Release Notification",
                          'body_html': mail_content,
                          'parent_id': None,
                          'email_from': dept.manager_id.user_id.partner_id.company_id.email,
                          'email_to': dept.manager_id.work_email
                          }
                self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_recommend(self):
        self.write({'state': 'recommended'})
        fm = self.env['hr.employee'].sudo().search([('is_fm', '=', True)], limit=1)
        if fm:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            mail_content = "Dear Finance Manager," + "<br>A Monthly Budget Version Has Been Recommended.Please click the link below<br/> " + str(
                base_url)
            values = {'model': 'monthly.budget.consolidated',
                      'res_id': self.id,
                      'subject': "Monthly Budget Recommended Notification",
                      'body_html': mail_content,
                      'parent_id': None,
                      'email_from': fm.user_id.partner_id.company_id.email,
                      'email_to': fm.user_id.partner_id.email
                      }
            self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_consolidate(self):
        self.write({'state': 'consolidated'})
        md = self.env['hr.employee'].sudo().search([('is_md', '=', True)], limit=1)
        if md:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            mail_content = "Dear Finance Manager," + "<br>A Monthly Budget Request Has Been Recommended by Finance Manager.Please click the link below<br/> " + str(
                base_url)
            values = {'model': 'monthly.budget.consolidated',
                      'res_id': self.id,
                      'subject': "Monthly Budget Consolidated Notification",
                      'body_html': mail_content,
                      'parent_id': None,
                      'email_from': md.user_id.partner_id.company_id.email,
                      'email_to': md.user_id.partner_id.email
                      }
            self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_approve(self):
        self.write({'state': 'approved'})
        amount = 0.0
        for line in self.monthly_budget_ids:
            amount += line.request_total
            line.write({'state': 'approved'})
        self.write({'total_budget_amount': amount})
        return True


class MonthlyBudgetRequest(models.Model):
    _name = "monthly.budget.request"
    _description = "Monthly Budget Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id"

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("submit", "Submitted"),
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

    name = fields.Char(string='Serial No', required=True)
    department_id = fields.Many2one('hr.department', string="Department", default=_default_department, readonly=True,
                                    required=True, store=True)
    branch_id = fields.Many2one('hr.branches', string="Branch", related='department_id.branch_id', store=True)
    consolidated_monthly_budget_id = fields.Many2one('monthly.budget.consolidated',
                                                     string="Consolidated Monthly Budget", readonly=True, store=True,
                                 states={'draft': [('readonly', False)]}, domain="[('state', '=', 'released'),('branch_id','=', branch_id)]", track_visibility='onchange')
    date_start = fields.Date(string=' Start Budget Period Date', related='consolidated_monthly_budget_id.date_start', store=True)
    date_end = fields.Date(string='End Budget Period Date', related='consolidated_monthly_budget_id.date_end', store=True)
    annual_budget_id = fields.Many2one('annual.budget', string='Annual Budget', related='consolidated_monthly_budget_id.annual_budget_id', store=True)
    dept_budget_id = fields.Many2one('crossovered.budget', string='Department Budget', readonly=True,
                                       required=True,
                                       states={'draft': [('readonly', False)]},
                                       domain="[('annual_budget_id','=', annual_budget_id),('department_id','=',department_id)]",
                                       track_visibility='onchange')
    currency_id = fields.Many2one('res.currency', related='dept_budget_id.company_id.currency_id', readonly=True)
    request_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_compute_amount_all')
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft')

    line_ids = fields.One2many('monthly.budget.request.lines', 'monthly_budget_request_id', string='Monthly Budget Request Lines', store=True)


    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         'Serial No Must be Unique'),
    ]

    @api.depends('line_ids.request_amount')
    def _compute_amount_all(self):
        for record in self:
            amount = 0.00
            for line in record.line_ids:
                amount += line.request_amount
            record.request_total = amount

    @api.multi
    def action_reset(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def action_submit(self):
        self.write({'state': 'submit'})
        bm = self.env['hr.branches'].sudo().search([('id', '=', self.branch_id.id)], limit=1)
        if bm:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            mail_content = "Dear Branch Manager," + "<br>A Monthly Budget Request Has Been Made.Please click the link below<br/> " + str(
                base_url)
            values = {'model': 'monthly.budget.request',
                      'res_id': self.id,
                      'subject': "Monthly Budget Request Notification",
                      'body_html': mail_content,
                      'parent_id': None,
                      'email_from': bm.manager_id.user_id.partner_id.company_id.email,
                      'email_to': bm.manager_id.user_id.partner_id.email
                      }
            self.env['mail.mail'].sudo().create(values)
        return True

class MonthlyBudgetRequestLines(models.Model):
    _name = "monthly.budget.request.lines"
    _description = "Monthly Budget Request Lines"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id"

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("submit", "Submitted"),
        ("approved", "Approved"),
        ("reject", "Rejected"),
    ]

    def _default_department(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee is not None:
            return employee.department_id

    date = fields.Date('Date', required=True, readonly=True, store=True, default=fields.Date.context_today)
    monthly_budget_request_id = fields.Many2one('monthly.budget.request', string='Monthly Budget Request Ref', store=True)
    dept_budget_id = fields.Many2one('crossovered.budget', string='Department Budget', store=True)
    from_budget_line_id = fields.Many2one('crossovered.budget.lines', string='From Budget Line', domain="[('crossovered_budget_id','=',dept_budget_id)]", required=True)
    currency_id = fields.Many2one('res.currency', related='dept_budget_id.company_id.currency_id', readonly=True)
    remaining_amount = fields.Monetary(string='Remaining Amount', readonly=True, store=True, default=0)
    request_amount = fields.Monetary(string='Requested Amount', required=True, store=True, default=0)
    state = fields.Selection(STATE_SELECTION, related='monthly_budget_request_id.state', store=True)

    @api.onchange('from_budget_line_id')
    @api.depends('from_budget_line_id')
    def onchange_from_budget_line_id(self):
        if self.from_budget_line_id:
            self.remaining_amount = self.from_budget_line_id.planned_amount - self.from_budget_line_id.practical_amount


    @api.onchange('request_amount')
    @api.depends('request_amount')
    def onchange_request_amount(self):
        if self.request_amount > self.remaining_amount:
            self.request_amount = 0
            raise ValidationError(_("Please enter an amount less than the remaining amount"))