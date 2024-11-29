# -*- coding: utf-8 -*-
import base64
from io import BytesIO

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class CashRequest(models.Model):
    _name = "account.cash.request"
    _description = "Cash Requests"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("request", "Requested"),
        ("checked_ss", "Checked by SS"),
        ("checked_acc", "Checked by Accountant"),
        ("endorsed", "Endorsed"),
        ("recommended", "Recommended"),
        ("approved", "Approved"),
        ("funds_received", "Funds Received"),
        ("closed", "Closed"),
        ("rejected", "Rejected"),
    ]

    def _default_department(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee and employee.department_id:
            return employee.department_id.id

    def _default_requester(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee:
            return employee.id

    # def _default_reference(self):
    #     itemList = self.env['account.cash.request'].sudo().search_count([])
    #     return 'CASH/REQUEST/00' + str(itemList + 1)

    # @api.depends('department_id')
    # @api.onchange('department_id')
    # def _default_reference(self):
    #     itemList = self.env['account.cash.request'].sudo().search_count([])
    #     department_id = self.env['account.cash.request'].sudo().search([])
    #     return 'CASH/REQUEST/{}/00{}'.format(department_id.code, itemList + 1)

    # def _default_reference(self):
    #     itemList = self.env['account.cash.request'].sudo().search_count([])
    #
    #     # Ensure department_id is available and related to the correct model
    #     department_code = self.department_id.code if self.department_id else 'UNKNOWN'

        # Format the reference string
        # return 'CASH/REQUEST/{}/{}'.format(department_code, str(itemList + 1).zfill(3))

    # @api.onchange('department_id')
    def _default_reference(self):
        # Get the count of records to determine the next sequence number
        itemList = self.env['account.cash.request'].sudo().search_count([])

        # Get the department code of the current user
        department = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1).department_id

        # Ensure department_id is available and related to the correct model
        department_code = department.code if department else 'UNDEFINED'

        # Format the reference string
        return 'CASH/REQUEST/{}/{}'.format(department_code, str(itemList + 1).zfill(3))

    name = fields.Char('Serial No', required=True, default=_default_reference)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get(
                                     'account.cash.request'))
    date = fields.Date(string="Date", required=True, default=fields.Date.today())
    requester_id = fields.Many2one('hr.employee', string="Requested By", required=True, default=_default_requester,
                                   readonly=True, store=True, states={'draft': [('readonly', False)]})
    department_id = fields.Many2one('hr.department', string='Department', required=True, default=_default_department,
                                    readonly=True, store=True, states={'draft': [('readonly', False)]})
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    total_amount = fields.Monetary(string='Total Amount', readonly=True, store=True, compute='_compute_amounts')
    total_used = fields.Monetary(string='Used Amount', store=True, readonly=True, compute='_compute_amounts')
    total_balance = fields.Monetary(string='Total Balance', store=True, readonly=True, compute='_compute_amounts')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Budget Line',
                                          domain="[('department_id','=',department_id)]")
    is_budgeted = fields.Boolean('Budgeted Cash Request', default=False)
    is_hq_request = fields.Boolean('HQ Cash Request', default=False)
    from_journal_id = fields.Many2one('account.journal', string='Credit Journal',
                                      domain="[('type','in',['cash','bank'])]")
    to_journal_id = fields.Many2one('account.journal', string='Debit Journal')
    from_credit_account_id = fields.Many2one('account.account', string='Credit Account', required=False, store=True,
                                             states={'endorsed': [('required', True)]})
    to_debit_account_id = fields.Many2one('account.account', string='Debit Account', required=False, store=True,
                                          states={'endorsed': [('required', True)]})
    payment_line_id = fields.Many2one('account.payment', string='Disbursement Entry', readonly=True, store=True)
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft', store=True)
    line_ids = fields.One2many('account.cash.request.lines', 'cash_request_id', string="Expenditure Lines", index=True,
                               track_visibility='onchange')
    retire_ids = fields.One2many('account.cash.request.retirement.lines', 'cash_request_id', string="Retirement Lines",
                                 index=True,
                                 track_visibility='onchange')

    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         'Serial No Must be Unique'),
    ]

    @api.model
    def company_info(self):
        company = self.env.user.company_id
        logo_data = base64.b64decode(company.logo)
        return {
            'name': company.name,
            'vat': company.vat,
            'vrn': company.company_registry,
            'street': company.street,
            'street2': company.street2,
            'phone': company.phone,
            'email': company.email,
            'website': company.website,
            'logo': BytesIO(logo_data)
        }

    # set default account
    @api.multi
    @api.onchange('department_id')
    def onchange_dept(self):
        if self.department_id and self.department_id.branch_id:
            if self.department_id.branch_id.main_branch:
                self.is_hq_request = True
            else:
                self.is_hq_request = False

    # set default account
    @api.multi
    @api.onchange('from_journal_id', 'to_journal_id')
    def onchange_from_to_account(self):
        for rec in self:
            if not rec.from_journal_id and not rec.to_journal_id:
                return
            # set accounting details
            if rec.from_journal_id:
                if rec.from_journal_id.default_credit_account_id:
                    rec.from_credit_account_id = rec.from_journal_id.default_credit_account_id.id
                else:
                    raise ValidationError(_('Please Set to Default Credit Account For This Payment Journal!'))

            if rec.to_journal_id:
                if not rec.to_journal_id.default_debit_account_id:
                    raise ValidationError(_('Please Set To Default Debit Account For This Receiving Journal!!!'))
                else:
                    rec.to_debit_account_id = rec.to_journal_id.default_debit_account_id.id

    @api.multi
    def button_send_request(self):
        self.write({'state': 'request'})
        mail_template = self.env.ref('cash_requests.notify_supervisor')
        mail_template.send_mail(self.id, force_send=True)
        return True

    @api.multi
    def button_check_ss(self):
        self.write({'state': 'checked_ss'})
        mail_template = self.env.ref('cash_requests.notify_accountant')
        mail_template.send_mail(self.id, force_send=True)
        return True

    @api.multi
    def button_check_acc(self):
        if self.is_hq_request:
            self.write({'state': 'endorsed'})
            # fm = self.env['hr.employee'].sudo().search([('is_fm', '=', True)], limit=1)
            # if fm:
            #     base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            #     base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            #     mail_content = "Dear Finance Manager," + "<br>Cash request is waiting your response.Please click the link below<br/> " + str(
            #         base_url)
            #     values = {'model': 'annual.budget',
            #               'res_id': self.id,
            #               'subject': "Annual Budget Notification",
            #               'body_html': mail_content,
            #               'parent_id': None,
            #               'email_from': fm.user_id.partner_id.company_id.email,
            #               'email_to': fm.user_id.partner_id.email
            #               }
            #     self.env['mail.mail'].sudo().create(values)
        else:
            self.write({'state': 'checked_acc'})
        return True

    @api.multi
    def button_endorse(self):
        self.write({'state': 'endorsed'})
        return True

    @api.multi
    def button_recommend(self):
        if self.is_budgeted:
            if self.from_journal_id and self.to_journal_id:
                payment_methods = self.from_journal_id.inbound_payment_method_ids or self.from_journal_id.outbound_payment_method_ids
                payment_method_id = payment_methods and payment_methods[0] or False
                payment_id = self.env['account.payment'].sudo().create({
                    'staff_payment': True,
                    'staff_payment_to_account_id': self.to_debit_account_id.id,
                    'payment_type': 'outbound',
                    'payment_date': fields.date.today(),
                    'journal_id': self.from_journal_id.id,
                    'destination_journal_id': self.to_journal_id.id,
                    'payment_method_id': payment_method_id.id,
                    'partner_id': self.requester_id.user_id.partner_id.id,
                    'partner_type': 'supplier',
                    'currency_id': self.currency_id.id,
                    'amount': self.total_amount,
                    'analytic_account_id': self.analytic_account_id.id,
                    'communication': self.name,
                    'name': self.name,
                })
                payment_id.post()
                mail_template = self.env.ref('cash_requests.notify_requester_cash_approved')
                mail_template.send_mail(self.id, force_send=True)
                self.write({'state': 'approved', 'payment_line_id': payment_id.id})
        else:
            self.write({'state': 'recommended'})
        return True

    @api.multi
    def button_approve(self):
        if self.from_journal_id and self.to_journal_id:
            payment_methods = self.from_journal_id.inbound_payment_method_ids or self.from_journal_id.outbound_payment_method_ids
            payment_method_id = payment_methods and payment_methods[0] or False
            payment_id = self.env['account.payment'].sudo().create({
                'staff_payment': True,
                'staff_payment_to_account_id': self.to_debit_account_id.id,
                'payment_type': 'outbound',
                'payment_date': fields.date.today(),
                'journal_id': self.from_journal_id.id,
                'destination_journal_id': self.to_journal_id.id,
                'payment_method_id': payment_method_id.id,
                'partner_id': self.requester_id.user_id.partner_id.id,
                'partner_type': 'supplier',
                'currency_id': self.currency_id.id,
                'amount': self.total_amount,
                'communication': self.name,
                'name': self.name,
            })
            payment_id.post()
            self.write({'state': 'approved', 'payment_line_id': payment_id.id})
        return True

    @api.multi
    def button_funds(self):
        if self.requester_id.user_id.id == self.env.uid or self.user_has_groups('cash_requests.cash_request_cashier'):
            self.write({'state': 'funds_received'})
        else:
            raise ValidationError(_('This is Not Your Cash Request!'))
        return True

    @api.multi
    def button_reject(self):
        self.write({'state': 'rejected'})
        return True

    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return True

    @api.depends('line_ids', 'retire_ids')
    def _compute_amounts(self):
        for rec in self:
            totalAmount = 0
            usedAmount = 0
            for line in rec.line_ids:
                totalAmount += line.total_cost
            for line in rec.retire_ids:
                if line.state == 'retired':
                    usedAmount += line.total_amount
            rec.total_amount = totalAmount
            rec.total_used = usedAmount
            rec.total_balance = totalAmount - usedAmount


class CashRequestLines(models.Model):
    _name = "account.cash.request.lines"
    _description = "Cash Request Expenditure"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("checked_ss", "Checked by SS"),
        ("checked_acc", "Checked by Accountant"),
        ("endorsed", "Endorsed"),
        ("recommended", "Recommended"),
        ("approved", "Approved"),
        ("funds_received", "Funds Received"),
        ("rejected", "Rejected"),
    ]

    def _default_requester(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee:
            return employee.id

    def _default_department(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee and employee.department_id:
            return employee.department_id.id

    name = fields.Char('Serial No', required=True)
    cash_request_id = fields.Many2one('account.cash.request', string="Cash Request")
    site_id = fields.Many2one(comodel_name='sites.configuration', string="Site")
    description = fields.Text('Description', required=True)
    attachment = fields.Binary(string="Attachment", attachment=True, store=True, )
    attachment_name = fields.Char('Attachment Name')
    unit_cost = fields.Float(string='Unit Cost', digits=(16, 2), required=True, store=True)
    total_cost = fields.Float(string='Total Cost', digits=(16, 2), required=True, store=True)
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange', related='cash_request_id.state',
                             store=True)


class AccountPaymentManualInherit(models.Model):
    _inherit = 'account.payment'

    staff_payment = fields.Boolean('Staff Payment', default=False)
    staff_payment_to_account_id = fields.Many2one('account.account', string='Payment Debit Account', store=True)

    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        if self.invoice_ids:
            self.destination_account_id = self.invoice_ids[0].account_id.id
        elif self.payment_type == 'transfer':
            if not self.company_id.transfer_account_id.id:
                raise UserError(
                    _('There is no Transfer Account defined in the accounting settings. Please define one to be able to confirm this transfer.'))
            self.destination_account_id = self.company_id.transfer_account_id.id
        elif self.partner_id:
            if self.partner_type == 'customer':
                self.destination_account_id = self.partner_id.property_account_receivable_id.id
            elif self.partner_type == 'supplier' and self.staff_payment is True:
                self.destination_account_id = self.staff_payment_to_account_id.id
            else:
                self.destination_account_id = self.partner_id.property_account_payable_id.id
        elif self.partner_type == 'customer':
            default_account = self.env['ir.property'].get('property_account_receivable_id', 'res.partner')
            self.destination_account_id = default_account.id
        elif self.partner_type == 'supplier':
            default_account = self.env['ir.property'].get('property_account_payable_id', 'res.partner')
            self.destination_account_id = default_account.id


class CashRequestRetirement(models.Model):
    _name = "account.cash.request.retirement"
    _description = "Cash Request Retirement"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("recommended", "Recommended"),
        ("retired", "Retired"),
        ("rejected", "Rejected")
    ]

    def _default_reference(self):
        itemList = self.env['account.cash.request.retirement'].sudo().search_count([])
        return 'CASH/RETIRE/00' + str(itemList + 1)

    def _default_requester(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee:
            return employee.id

    def _default_department(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee and employee.department_id:
            return employee.department_id.id

    name = fields.Char('Serial No', required=True, default=_default_reference)
    date = fields.Date(string="Date", required=True, default=fields.Date.today())
    cash_request_id = fields.Many2one('account.cash.request', string="Cash Request",
                                      domain=[('state', '=', 'funds_received')])
    currency_id = fields.Many2one('res.currency', related='cash_request_id.currency_id')
    requester_id = fields.Many2one('hr.employee', string="Retired By", required=True, default=_default_requester,
                                   readonly=True, store=True, states={'draft': [('readonly', False)]})
    department_id = fields.Many2one('hr.department', string='Department', required=True, default=_default_department,
                                    readonly=True, store=True, states={'draft': [('readonly', False)]})
    total_amount = fields.Monetary(string='Total Amount', store=True, related='cash_request_id.total_amount')
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange', readonly=True, required=True,
                             copy=False, default='draft', store=True)
    line_ids = fields.One2many('account.cash.request.retirement.lines', 'retire_id', string="Retirement Lines",
                               index=True,
                               track_visibility='onchange')

    @api.multi
    def button_reject(self):
        self.write({'state': 'rejected'})
        return True

    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def button_recommend(self):
        self.write({'state': 'recommended'})
        return True

    @api.multi
    def button_retire(self):
        for line in self.line_ids:
            if not line.expense_account_id:
                raise ValidationError(_('Please enter the expense account for the expenditure lines'))
        for line in self.line_ids:
            if line.expense_account_id:
                today = datetime.today().date()
                if self.cash_request_id.is_budgeted:
                    checkAnalytic = self.env['crossovered.budget.lines'].sudo().search(
                        [('date_from', '<=', today), ('date_to', '>=', today),
                         ('analytic_account_id', '=', self.cash_request_id.analytic_account_id.id)], limit=1)
                    if checkAnalytic:
                        company_currency = self.env.user.company_id.currency_id
                        current_currency = self.cash_request_id.currency_id
                        amountTotal = line.total_amount
                        if company_currency != current_currency:
                            if current_currency.rate <= 0:
                                rate = 1
                            else:
                                rate = current_currency.rate
                            amountTotal = line.total_amount / rate
                        if line.retire_type == "expense":
                            move_line_1 = {
                                'name': 'Cash Request Retirement',
                                'account_id': line.expense_account_id.id,
                                'credit': 0.0,
                                'debit': amountTotal,
                                'currency_id': company_currency != current_currency and current_currency.id or False,
                                'amount_currency': company_currency != current_currency and line.total_amount or 0.0,
                                'analytic_account_id': checkAnalytic.analytic_account_id.id,
                                'partner_id': self.requester_id.user_id.partner_id.id
                            }
                            move_line_2 = {
                                'name': 'Cash Request Retirement',
                                'account_id': self.cash_request_id.to_debit_account_id.id,
                                'debit': 0.0,
                                'credit': amountTotal,
                                'currency_id': company_currency != current_currency and current_currency.id or False,
                                'amount_currency': company_currency != current_currency and - 1.0 * line.total_amount or 0.0,
                                'partner_id': self.requester_id.user_id.partner_id.id
                            }
                            move_vals = {
                                'ref': 'CASH/RETIRE/LINE' + str(line.id),
                                'date': self.date or False,
                                'journal_id': self.cash_request_id.to_journal_id.id,
                                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                            }
                            move = self.env['account.move'].sudo().create(move_vals)
                            move.post()
                        else:
                            move_line_1 = {
                                'name': 'Cash Request Retirement',
                                'account_id': line.expense_account_id.id,
                                'credit': 0.0,
                                'debit': amountTotal,
                                'currency_id': company_currency != current_currency and current_currency.id or False,
                                'amount_currency': company_currency != current_currency and line.total_amount or 0.0,
                                'partner_id': self.requester_id.user_id.partner_id.id
                            }
                            move_line_2 = {
                                'name': 'Cash Request Retirement',
                                'account_id': self.cash_request_id.to_debit_account_id.id,
                                'debit': 0.0,
                                'credit': amountTotal,
                                'currency_id': company_currency != current_currency and current_currency.id or False,
                                'amount_currency': company_currency != current_currency and - 1.0 * line.total_amount or 0.0,
                                'analytic_account_id': checkAnalytic.analytic_account_id.id,
                                'partner_id': self.requester_id.user_id.partner_id.id
                            }
                            move_vals = {
                                'ref': 'CASH/RETIRE/LINE' + str(line.id),
                                'date': self.date or False,
                                'journal_id': self.cash_request_id.to_journal_id.id,
                                'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                            }
                            move = self.env['account.move'].sudo().create(move_vals)
                            move.post()
                else:
                    company_currency = self.env.user.company_id.currency_id
                    current_currency = self.cash_request_id.currency_id
                    amountTotal = line.total_amount
                    if company_currency != current_currency:
                        if current_currency.rate <= 0:
                            rate = 1
                        else:
                            rate = current_currency.rate
                        amountTotal = line.total_amount / rate
                    move_line_1 = {
                        'name': 'Cash Request Retirement',
                        'account_id': line.expense_account_id.id,
                        'credit': 0.0,
                        'debit': amountTotal,
                        'currency_id': company_currency != current_currency and current_currency.id or False,
                        'amount_currency': company_currency != current_currency and line.total_amount or 0.0,
                        'partner_id': self.requester_id.user_id.partner_id.id
                    }
                    move_line_2 = {
                        'name': 'Cash Request Retirement',
                        'account_id': self.cash_request_id.to_debit_account_id.id,
                        'debit': 0.0,
                        'credit': amountTotal,
                        'currency_id': company_currency != current_currency and current_currency.id or False,
                        'amount_currency': company_currency != current_currency and - 1.0 * line.total_amount or 0.0,
                        'partner_id': self.requester_id.user_id.partner_id.id
                    }
                    move_vals = {
                        'ref': line.name,
                        'date': self.date or False,
                        'journal_id': self.cash_request_id.to_journal_id.id,
                        'line_ids': [(0, 0, move_line_1), (0, 0, move_line_2)],
                    }
                    move = self.env['account.move'].sudo().create(move_vals)
                    move.post()
        self.write({'state': 'retired'})
        self.cash_request_id.write({'state': 'closed'})
        return True


class CashRequestRetirementLines(models.Model):
    _name = "account.cash.request.retirement.lines"
    _description = "Cash Request Retirement Lines"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("recommended", "Recommended"),
        ("approved", "Approved"),
        ("rejected", "Rejected")
    ]

    RETIRE_TYPE = [
        ("expense", "Expense"),
        ("refund", "Refund")
    ]

    name = fields.Char('Serial No', required=True)
    retire_type = fields.Selection(RETIRE_TYPE, required=True, default='expense', store=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.today())
    retire_id = fields.Many2one('account.cash.request.retirement', string="Cash Request Retirement")
    cash_request_id = fields.Many2one('account.cash.request', string="Cash Request",
                                      related='retire_id.cash_request_id', store=True)
    requester_id = fields.Many2one('hr.employee', string="Retired By", related='retire_id.requester_id', store=True)
    description = fields.Text('Description', required=True)
    total_amount = fields.Float(string='Total Amount', digits=(16, 2), required=True, store=True)
    upload_receipt = fields.Binary("Receipt", attachment=True)
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange', default='draft',
                             related='retire_id.state', store=True)
    expense_journal_id = fields.Many2one('account.journal', string='Expense/Refund Journal', store=True)
    expense_account_id = fields.Many2one('account.account', string='Expense/Refund Account', store=True)

    @api.multi
    @api.onchange('expense_journal_id')
    def onchange_expense_journal(self):
        for rec in self:
            if not rec.expense_journal_id:
                return
            if rec.expense_journal_id:
                if not rec.expense_journal_id.default_debit_account_id:
                    raise ValidationError(_('Please Set To Default Debit Account For This Journal!!!'))
                else:
                    rec.expense_account_id = rec.expense_journal_id.default_debit_account_id.id
