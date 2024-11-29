# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
from odoo.http import request


class HrLoan(models.Model):
    _name = 'hr.loan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Loan Request"

    @api.model
    def default_get(self, field_list):
        result = super(HrLoan, self).default_get(field_list)
        if result.get('user_id'):
            ts_user_id = result['user_id']
        else:
            ts_user_id = self.env.context.get('user_id', self.env.user.id)
            result['employee_id'] = self.env['hr.employee'].search([('user_id', '=', ts_user_id)], limit=1).id
        return result

    @api.onchange('employee_id')
    @api.depends('employee_id')
    def onchange_employee_details(self):
        if self.employee_id:
            contract = self.env['hr.contract'].sudo().search([('employee_id', '=', self.employee_id.id),('state','=','open')], limit=1)
            if contract:
                self.contract_id = contract.id
            if self.employee_id.user_id:
                banks = []
                empBanks = self.env['res.partner.bank'].search(
                    [('partner_id', '=', self.employee_id.user_id.partner_id.id)])
                for empBank in empBanks:
                    banks.append(empBank.id)
                return {'domain': {'partner_bank_account_id': [('id', 'in', banks)]}}




    @api.onchange('loan_amount','installment','loan_type')
    @api.depends('loan_amount','installment','loan_type')
    def onchange_loan_amount(self):
        if self.loan_amount and not self.loan_type:
            self.loan_amount = 0
            raise UserError(
                'Please Choose a Loan Type First')
        if self.employee_id and not self.contract_id:
            raise UserError(
                'Please Contact Your HR To Check Your Contract')
        if self.contract_id and self.contract_id.wage <= 0:
            raise UserError(
                'Please Contact Your HR To Setup Your Monthly Salary')
        if not self.installment or self.installment <= 0:
            self.installment = 0
            raise UserError(
                'Please Enter a Valid No. of Installment')
        if self.installment:
            if self.loan_type == 'loan' and self.installment > 3:
                self.installment = 0
                raise UserError(
                    'Please Enter a Number Less Than 3 for Installments')
            elif self.loan_type == 'staff_advance' and self.installment > 1:
                self.installment = 1
        if self.contract_id.wage > 0:
            if self.loan_type == 'loan':
                if self.loan_amount > self.contract_id.wage:
                    self.loan_amount = 0
                    raise UserError(
                        'You Cannot Borrow More Than Your Monthly Salary')
            else:
                halfSalary = self.contract_id.wage / 2
                if self.loan_amount > halfSalary:
                    self.loan_amount = 0
                    raise UserError(
                        'You Cannot Borrow More Than Half Your Monthly Salary')

    @api.one
    def _compute_loan_amount(self):
        for loan in self:
            total_paid = 0.0
            for line in loan.loan_lines:
                if line.paid:
                    total_paid += line.amount
            balance_amount = loan.loan_amount - total_paid
            self.total_amount = loan.loan_amount
            self.balance_amount = balance_amount
            self.total_paid_amount = total_paid


    name = fields.Char(string="Serial No", default="LO/")
    date = fields.Date(string="Date", default=fields.Date.today(), store=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True, store=True, required=True, states={
                                               'draft': [('readonly', False)]})
    department_id = fields.Many2one('hr.department', related="employee_id.department_id", readonly=True,
                                    string="Department", store=True, required=True)
    branch_id = fields.Many2one('hr.branches', related="employee_id.department_id.branch_id", readonly=True,
                                    string="Branch", store=True, required=True)
    contract_id = fields.Many2one('hr.contract', string="Employee Contract", required=True, readonly=True, store=True)
    job_position = fields.Many2one('hr.job', related="employee_id.job_id", string="Job Position", store=True)
    installment = fields.Integer(string="No Of Installments", default=1,required=True)
    payment_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.today())
    loan_lines = fields.One2many('hr.loan.line', 'loan_id', string="Loan Line", index=True)
    emp_account_id = fields.Many2one('account.account', string="Credit Account")
    treasury_account_id = fields.Many2one('account.account', string="Debit Account")
    journal_id = fields.Many2one('account.journal', string="Credit Journal",domain=[('type','in',['bank','cash'])])
    to_journal_id = fields.Many2one('account.journal', string="Debit Journal")
    company_id = fields.Many2one('res.company', 'Company', readonly=True,
                                 default=lambda self: self.env.user.company_id,
                                 states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    loan_amount = fields.Float(string="Loan Amount", required=True)
    total_amount = fields.Float(string="Total Amount", readonly=True, compute='_compute_loan_amount')
    balance_amount = fields.Float(string="Balance Amount", compute='_compute_loan_amount')
    total_paid_amount = fields.Float(string="Total Paid Amount", compute='_compute_loan_amount')
    partner_bank_account_id = fields.Many2one('res.partner.bank', string="Employee Bank A/C")
    payment_line_id = fields.Many2one('account.payment', string='Payment Line')
    description = fields.Text(string='Loan Reason Description')

    loan_state = fields.Selection([
        ('original', 'New'),
        ('additional', 'Additional')
    ], string="Loan State", required=True, store=True, default='original')

    payment_method = fields.Selection([
        ('cash', 'Cash'),
        ('bank_deposit', 'Bank Deposit')
    ], string="Payment Method", required=True, store=True, default='bank_deposit')

    loan_type = fields.Selection([
        ('loan', 'Loan'),
        ('staff_advance', 'Staff Advance')
    ], string="Loan Type", required=True, store=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('recommended', 'Checked by SS'),
        ('waiting_approval_1', 'Recommended By HR'),
        ('waiting_approval_2', 'Funds Available'),
        ('approve', 'Approved'),
        ('recovered', 'Recovered'),
        ('refuse', 'Refused'),
        ('cancel', 'Canceled'),
    ], string="State", default='draft', track_visibility='onchange', copy=False, )

    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         'Serial No Must be Unique'),
    ]
    @api.onchange('to_journal_id')
    def onchange_to_journal_id(self):
        if self.to_journal_id:
            if not self.to_journal_id.default_debit_account_id:
                raise UserError(
                    'Please add a default Debit Account to the Journal Setup')
            else:
                self.treasury_account_id = self.to_journal_id.default_debit_account_id.id

    @api.onchange('journal_id')
    def onchange_journal_id(self):
        if self.journal_id:
            if not self.journal_id.default_credit_account_id:
                raise UserError(
                    'Please add a default Credit Account to the Journal Setup')
            else:
                self.emp_account_id = self.journal_id.default_credit_account_id.id

    @api.model
    def create(self, values):
        if values.get('payment_method',False):
            paymentMethod = values.get('payment_method',False)
            if paymentMethod == "bank_deposit" and not values.get('partner_bank_account_id',False):
                raise UserError(
                    'Please Enter Bank Account')
        contract = self.env['hr.contract'].search([('employee_id','=',values.get('employee_id')),('state','=','open')], limit=1)
        if contract:
            values['contract_id'] = contract.id
            if contract.department_id:
                values['department_id'] = contract.department_id.id
                values['branch_id'] = contract.department_id.branch_id.id
            if contract.job_id:
                values['job_position'] = contract.job_id.id

            if contract.date_end:
                today = datetime.today().date()
                diffMonths = (today.year - contract.date_end.year) * 12 + today.month - contract.date_end.month
                diffMonths *= -1
                if diffMonths > 6:
                    checkActiveLoans = False
                    loan_totals = self.env['hr.loan'].search(
                        [('employee_id', '=', values['employee_id']), ('state', '=', 'approve')])
                    for item in loan_totals:
                        total_paid = 0.0
                        for line in item.loan_lines:
                            if line.paid:
                                total_paid += line.amount
                        balance_amount = item.loan_amount - total_paid
                        if balance_amount > 0:
                            checkActiveLoans = True
                            break
                    loanState = values['loan_state']
                    if checkActiveLoans and loanState == "original":
                        raise ValidationError(_("The employee has already a pending installment"))
                    else:
                        values['name'] = self.env['ir.sequence'].get('hr.loan.seq') or ' '
                        res = super(HrLoan, self).create(values)
                        if self.department_id.manager_id:
                            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
                            base_url += '/web#id=%d&view_type=form&model=%s' % (res.id, res._name)
                            mail_content = "Dear HOD," + "<br>There is a loan request from an employee in your department.Please click the link below<br/> " + str(
                                base_url)
                            values = {'model': 'hr.loan',
                                      'res_id': res.id,
                                      'subject': "Loan Request Notification",
                                      'body_html': mail_content,
                                      'parent_id': None,
                                      'email_from': self.sudo().department_id.manager_id.user_id.partner_id.company_id.email,
                                      'email_to': self.sudo().department_id.manager_id.user_id.partner_id.email
                                      }
                            self.env['mail.mail'].sudo().create(values)
                        return res
                else:
                    raise ValidationError(_("You cannot request a loan as your contract validity period is less than 6 months"))
            else:
                raise ValidationError(_("Please Contact HR to Enter Contract End Date"))
        else:
            raise ValidationError(_("Invalid Contract Details"))

    @api.multi
    def action_refuse(self):
        self.write({'state': 'refuse'})
        return True

    @api.multi
    def action_recovered(self):
        for line in self.loan_lines:
            line.write({'paid':True})
        self.write({'state': 'recovered'})
        return True

    @api.multi
    def action_submit(self):
        self.compute_installment()
        self.write({'state': 'recommended'})
        if self.department_id.branch_id.hr_manager_id:
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            mail_content = "Dear HR," + "<br>There is a loan request from an employee that requires accounting entries please proceed.Please click the link below<br/> " + str(
                base_url)
            values = {'model': 'hr.loan',
                      'res_id': self.id,
                      'subject': "Loan Request Notification",
                      'body_html': mail_content,
                      'parent_id': None,
                      'email_from': self.sudo().department_id.branch_id.hr_manager_id.user_id.partner_id.company_id.email,
                      'email_to': self.sudo().department_id.branch_id.hr_manager_id.user_id.partner_id.email
                      }
            self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def action_hr(self):
        self.write({'state': 'waiting_approval_1'})
        if self.department_id.branch_id.accountant_id:
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            mail_content = "Dear Accountant," + "<br>There is a loan request from an employee that requires approval.Please click the link below<br/> " + str(
                base_url)
            values = {'model': 'hr.loan',
                      'res_id': self.id,
                      'subject': "Loan Request Notification",
                      'body_html': mail_content,
                      'parent_id': None,
                      'email_from': self.sudo().department_id.branch_id.accountant_id.user_id.partner_id.company_id.email,
                      'email_to': self.sudo().department_id.branch_id.accountant_id.user_id.partner_id.email
                      }
            self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def action_acc(self):
        self.write({'state': 'waiting_approval_2'})
        fm = self.env['hr.employee'].sudo().search([('is_fm', '=', True)], limit=1)
        if fm:
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            mail_content = "Dear Finance Manager," + "<br>There is a loan request from an employee that requires approval.Please click the link below<br/> " + str(
                base_url)
            values = {'model': 'hr.loan',
                      'res_id': self.id,
                      'subject': "Loan Request Notification",
                      'body_html': mail_content,
                      'parent_id': None,
                      'email_from': fm.user_id.partner_id.company_id.email,
                      'email_to': fm.user_id.partner_id.email
                      }
            self.env['mail.mail'].sudo().create(values)
        return True


    @api.multi
    def action_cancel(self):
        self.write({'state': 'cancel'})
        return True

    @api.multi
    def action_double_approve(self):
        if self.partner_bank_account_id and not self.partner_bank_account_id.currency_id:
            raise ValidationError(_("Please Call HR to Enter Payee Bank Account Currency"))
        if not self.treasury_account_id:
            raise ValidationError(_("Please Select The Credit Account (Where the loan funds are coming from eg Bank A/C)"))
        if not self.emp_account_id:
            raise ValidationError(_("Please Select The Debit Account (Where the loan funds are going to eg Cash A/C)"))
        if not self.journal_id:
            raise ValidationError(_("Please Select The Payment Journal"))
        if not self.to_journal_id:
            raise ValidationError(_("Please Select The Debit Journal"))
        for data in self:
            if not data.loan_lines:
                raise ValidationError(_("Please Compute installment"))
            else:
                self.write({'state': 'approve'})

    @api.multi
    def unlink(self):
        for loan in self:
            if loan.state not in ('draft', 'cancel'):
                raise UserError(
                    'You cannot delete a loan which is not in draft or cancelled state')
        return super(HrLoan, self).unlink()

    @api.multi
    def compute_installment(self):
        """This automatically create the installment the employee need to pay to
        company based on payment start date and the no of installments.
            """
        for loan in self:
            loan.sudo().loan_lines.unlink()
            date_start = datetime.strptime(str(loan.payment_date), '%Y-%m-%d')
            amount = loan.loan_amount / loan.installment
            for i in range(1, loan.installment + 1):
                self.env['hr.loan.line'].create({
                    'date': date_start,
                    'amount': amount,
                    'employee_id': loan.employee_id.id,
                    'loan_id': loan.id})
                date_start = date_start + relativedelta(months=1)
        return True


class InstallmentLine(models.Model):
    _name = "hr.loan.line"
    _description = "Installment Line"

    date = fields.Date(string="Payment Date", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    amount = fields.Float(string="Amount", required=True)
    paid = fields.Boolean(string="Paid")
    loan_id = fields.Many2one('hr.loan', string="Loan Ref.")
    payslip_id = fields.Many2one('hr.payslip', string="Payslip Ref.")


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    @api.one
    def _compute_employee_loans(self):
        """This compute the loan amount and total loans count of an employee.
            """
        self.loan_count = self.env['hr.loan'].search_count([('employee_id', '=', self.id)])

    loan_count = fields.Integer(string="Loan Count", compute='_compute_employee_loans')


