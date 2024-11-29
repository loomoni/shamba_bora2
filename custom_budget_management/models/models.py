# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo import exceptions
from odoo.exceptions import ValidationError
from datetime import datetime

class BudgetGroups(models.Model):
    _name = 'budget.groups'
    _description = "Budget Groups"
    _order = "group_code"

    ACTIVITY_TYPE_SELECTION = [
        ("inflow", "INFLOW"),
        ("outflow", "OUTFLOW"),
    ]

    name = fields.Char(string="Name",required=True)
    group_code = fields.Char(string="Group Code", required=True)
    group_type = fields.Selection(ACTIVITY_TYPE_SELECTION, index=True, track_visibility='onchange', required=True, default='outflow')
    department_id = fields.Many2one('hr.department', string="Department")
    branch_id = fields.Many2one('hr.branches', string="Branch", related='department_id.branch_id', store=True)
    account_id = fields.Many2one('account.account', string='Account')

    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         'Budget Group Name Must be Unique'),
        ('group_code_unique',
         'UNIQUE(group_code)',
         'Group Code Must be Unique'),
    ]

class AnnualBudget(models.Model):
    _name = "annual.budget"
    _description = "Annual Budget"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date_start"

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("released", "Released"),
        ("recommended", "Recommend"),
        ("consolidated", "Consolidated"),
        ("approved", "Approved"),
        ("closed", "Closed"),
        ("cancel", "Cancelled"),
        ("reject", "Rejected"),
    ]

    @api.depends('budget_ids', 'budget_ids.amount_total')
    def _compute_total_budget_amount(self):
        for rec in self:
            for budget in rec.budget_ids:
                for line in budget.crossovered_budget_line:
                    if line.budget_group_id.group_type == "outflow":
                        rec.total_budget_amount += line.planned_amount

    name = fields.Char(string='Annual Budget', index=True,required=True)
    branch_id = fields.Many2one('hr.branches', string='Branch', required=True, readonly=True, states={'draft': [('readonly', False)]}, store=True)
    active = fields.Boolean('Active', default=True)
    currency_id = fields.Many2one(
        'res.currency',
        store=True,
        string="Currency",
        default=lambda self: self.env.user.currency_id,
        readonly=True,
    )
    date_start = fields.Date(string=' Start Budget Period Date', required=True,
                                 readonly=True, states={'draft': [('readonly', False)]})
    date_end = fields.Date(string='End Budget Period Date', required=True,
                               readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft')
    budget_ids = fields.One2many('crossovered.budget', 'annual_budget_id', string='Department Budgets',
                               readonly=True, store=True, domain=['|',('state','=','validate'),('state','=','done')])
    total_budget_amount = fields.Float(string='Total Projected Outflows', compute='_compute_total_budget_amount')
    fm_comments = fields.Html('Finance Manager Comments')
    md_comments = fields.Html(string='Managing Director Comments')
    consolidater_id = fields.Many2one(
        'res.users',
        string="Consolidated By",
        readonly=True,
        copy=False,
    )
    consolidation_date = fields.Date(
        'Consolidation Date',
        readonly=True,
        copy=False,
    )

    approve_id = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        copy=False,
    )
    approve_date = fields.Date(
        'Approved Date',
        readonly=True,
        copy=False,
    )

    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         'Annual Budget Name Must be Unique'),
    ]

    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        if self.date_start >= self.date_end or self.date_end < fields.Date.today():
            raise exceptions.Warning('Please check budget dates!')
        if self.env['annual.budget'].search(
                [('state', '=', 'approved'), ('date_end', '>', self.date_start), ('branch_id','=',self.branch_id.id)]):
            raise exceptions.Warning(
                'Please check budget dates.There is an annual budget for the specified period for the specified branch!')

    @api.multi
    def button_release(self):
        self.write({'state': 'released'})
        depts = self.env['hr.department'].sudo().search([('branch_id','=',self.branch_id.id)])
        for dept in depts:
            if dept.manager_id and dept.manager_id.user_id:
                mail_content = "Dear HOD," + "<br>The Budget Version of Period "+ str(self.date_start)+" - "+str(self.date_end) + " Has Been Released.Please Add Your Department Budget Lines"
                values = {'model': 'annual.budget',
                          'res_id': self.id,
                          'subject': "Annual Budget Release Notification",
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
            mail_content = "Dear Finance Manager," + "<br>Annual Budget ready for consolidation.Please click the link below<br/> " + str(
                base_url)
            values = {'model': 'annual.budget',
                      'res_id': self.id,
                      'subject': "Annual Budget Notification",
                      'body_html': mail_content,
                      'parent_id': None,
                      'email_from': fm.user_id.partner_id.company_id.email,
                      'email_to': fm.user_id.partner_id.email
                      }
            self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_cancel(self):
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        for line in self.budget_ids:
            line.write({'state': 'draft'})
        return True

    @api.multi
    def button_approve(self):
        if not self.budget_ids:
            raise exceptions.Warning('Department Budgets Missing for the Annual Budget')
        self.write({
            'state': 'approved',
            'approve_id': self.env.user.id,
            'approve_date': fields.datetime.today()
        })
        amount = 0.0
        for line in self.budget_ids:
            amount += line.amount_total
            line.write({'state': 'validate'})
        self.write({'total_budget_amount': amount})
        return True

    @api.multi
    def button_consolidate(self):
        if not self.budget_ids:
            raise exceptions.Warning('Department Budgets Missing for the Annual Budget')
        self.write({
            'state': 'consolidated',
            'advise_id': self.env.user.id,
            'advise_date': fields.datetime.today()
        })
        md = self.env['hr.employee'].sudo().search([('is_md', '=', True)], limit=1)
        if md:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            mail_content = "Dear MD," + "<br>Annual Budget ready for approval.Please click the link below<br/> " + str(
                base_url)
            values = {'model': 'annual.budget',
                      'res_id': self.id,
                      'subject': "Annual Budget Notification",
                      'body_html': mail_content,
                      'parent_id': None,
                      'email_from': md.user_id.partner_id.company_id.email,
                      'email_to': md.user_id.partner_id.email
                      }
            self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_reject(self):
        self.write({'state': 'reject'})
        return True

    @api.multi
    def button_close(self):
        budgets = self.env['crossovered.budget'].search([('annual_budget_id', '=', self.id)])
        for budget in budgets:
            budget.state = 'closed'
        self.write({'state': 'closed'})
        return True



class CrossoveredBudgetInherit(models.Model):
    _inherit = 'crossovered.budget'

    def _default_employee(self):
        return self.env.context.get('default_employee_id') or self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)

    def _default_department(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee is not None:
            return employee.department_id

    ANNUAL_STATE_SELECTION = [
        ("draft", "Draft"),
        ("released", "Released"),
        ("recommended", "Recommend"),
        ("consolidated", "Consolidated"),
        ("approved", "Approved"),
        ("closed", "Closed"),
        ("cancel", "Cancelled"),
        ("reject", "Rejected"),
    ]


    @api.onchange('annual_budget_id')
    @api.depends('annual_budget_id')
    def _compute_date_start_end(self):
        for rec in self:
            rec.date_from = rec.annual_budget_id.date_start
            rec.date_to = rec.annual_budget_id.date_end

    @api.onchange('crossovered_budget_line', 'crossovered_budget_line.planned_amount')
    @api.depends('crossovered_budget_line', 'crossovered_budget_line.planned_amount')
    def _onchange_crossovered_budget_line(self):
        for budget in self:
            amount = 0.0
            for line in budget.crossovered_budget_line:
                amount += line.planned_amount
            budget.amount_total = amount

    department_id = fields.Many2one('hr.department', string="Department", default=_default_department, readonly=True,
                                    required=True, store=True)
    branch_id = fields.Many2one('hr.branches', string="Branch", related='department_id.branch_id', store=True)
    annual_budget_id = fields.Many2one('annual.budget', string='Annual Budget', readonly=True,
                                 required=True,
                                 states={'draft': [('readonly', False)]}, domain="[('state', '=', 'released'),('branch_id','=', branch_id)]", track_visibility='onchange',)

    annual_budget_status =  fields.Selection(ANNUAL_STATE_SELECTION, related='annual_budget_id.state', store=True)
    employee_id = fields.Many2one(comodel_name='hr.employee', string='HOD Employee', index=True, readonly=True,
                                  default=_default_employee)
    date_from = fields.Date('Start Date', required=True, readonly=True, store=True)
    date_to = fields.Date('End Date', required=True, readonly=True, store=True)
    active = fields.Boolean('Active', default=True)
    amount_total = fields.Float(string='Total', store=True, readonly=True, default="0.00", compute='_onchange_crossovered_budget_line')
    version_number = fields.Integer("Budget Versions", compute='_compute_versions_count')

    @api.multi
    def _compute_versions_count(self):
        for record in self:
            record.version_number = self.env["budget.versions"].search_count(
                [('parent_dept_budget_id', '=', record.id)])

    @api.multi
    def action_budget_cancel(self):
        self.write({'state': 'cancel'})
        self.write({'state': 'draft'})

    @api.multi
    def send_message_on_dept_budget(self):
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

    @api.model
    def create(self, vals):
        annualBudget = self.env['annual.budget'].search([('id','=',vals.get('annual_budget_id'))])
        vals['date_from'] = annualBudget.date_start
        vals['date_to'] = annualBudget.date_end
        res = super(CrossoveredBudgetInherit, self).create(vals)
        return res


class CrossoveredBudgetLinesInherit(models.Model):
    _inherit = 'crossovered.budget.lines'

    def _default_department(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee is not None:
            return employee.department_id

    analytic_account_id = fields.Many2one('account.analytic.account', 'Budget Line')
    general_budget_id = fields.Many2one('account.budget.post', 'Account')
    department_id = fields.Many2one('hr.department', string='Department', required=True, store=True,
                                    default=_default_department)
    budget_group_id = fields.Many2one('budget.groups', string='Budget Group', required=True, store=True)
    budget_code = fields.Char(string='Budget Code', required=True, store=True)
    account_id = fields.Many2one('account.account', string='Account', required=True)
    budget_line_desc = fields.Text(string='Description', required=True, store=True)

    @api.onchange('budget_group_id')
    @api.depends('budget_group_id')
    def onchange_account_id(self):
        if self.crossovered_budget_id:
            self.department_id = self.crossovered_budget_id.department_id
        if self.budget_group_id:
            self.budget_code = self.budget_group_id.group_code
            if self.budget_group_id.account_id:
                self.account_id = self.budget_group_id.account_id
            checkAnalytic = self.env['account.analytic.account'].search(
                [('department_id', '=', self.department_id.id), ('name', '=', self.budget_code)])
            if not checkAnalytic:
                analytic = {
                    'name': self.budget_code,
                    'department_id': self.department_id.id,
                    'display_name': str(self.budget_code)+ ' - ' + str(self.budget_line_desc),
                }
                analytic_id = self.env['account.analytic.account'].create(analytic)
                self.analytic_account_id = analytic_id.id
            else:
                self.analytic_account_id = checkAnalytic.id
        if self.account_id:
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


    @api.constrains('general_budget_id', 'analytic_account_id')
    def _must_have_analytical_or_budgetary_or_both(self):
        for record in self:
            if not record.analytic_account_id and not record.general_budget_id:
                raise ValidationError(
                    _("You have to enter at least an account or budget line on a budget line."))

    @api.multi
    def _compute_line_name(self):
        # just in case someone opens the budget line in form view
        for record in self:
            computed_name = record.crossovered_budget_id.name
            if record.general_budget_id:
                computed_name += ' - ' + record.general_budget_id.name
            if record.analytic_account_id:
                computed_name += ' - ' + record.analytic_account_id.name
            record.name = computed_name

    @api.multi
    def _compute_practical_amount(self):
        for line in self:
            acc_ids = line.general_budget_id.account_ids.ids
            date_to = line.date_to
            date_from = line.date_from
            if line.analytic_account_id.id:
                analytic_line_obj = self.env['account.analytic.line']
                domain = [('account_id', '=', line.analytic_account_id.id),
                          ('date', '>=', date_from),
                          ('date', '<=', date_to),
                          ]
                # if acc_ids:
                #     domain += [('general_account_id', 'in', acc_ids)]

                where_query = analytic_line_obj._where_calc(domain)
                analytic_line_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT SUM(amount) from " + from_clause + " where " + where_clause

            else:
                aml_obj = self.env['account.move.line']
                domain = [('account_id', 'in',
                           line.general_budget_id.account_ids.ids),
                          ('date', '>=', date_from),
                          ('date', '<=', date_to)
                          ]
                where_query = aml_obj._where_calc(domain)
                aml_obj._apply_ir_rules(where_query, 'read')
                from_clause, where_clause, where_clause_params = where_query.get_sql()
                select = "SELECT sum(credit)-sum(debit) from " + from_clause + " where " + where_clause

            self.env.cr.execute(select, where_clause_params)
            line.practical_amount = self.env.cr.fetchone()[0] or 0.0

class AnalyticalAccountInherit(models.Model):
    _inherit = 'account.analytic.account'

    def _default_department(self):
        employee = self.env['hr.employee'].search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee is not None:
            return employee.department_id

    department_id = fields.Many2one(
        'hr.department',
        string="Department",
        default=_default_department
    )
    display_name = fields.Text(string='Display Name', store=True)

    @api.multi
    @api.depends('name')
    def name_get(self):
        result = []
        for item in self:
            nameAcc = item.name
            for rec in item.crossovered_budget_line:
                nameAcc = nameAcc + ' ' + rec.budget_line_desc
                break
            if "False" in item.display_name:
                item.display_name = nameAcc
            result.append((item.id, nameAcc))
        return result
