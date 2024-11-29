# -*- coding: utf-8 -*-
import base64
from io import BytesIO

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class WageRequest(models.Model):
    _name = "account.wage.request"
    _description = "Wage Requests"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("checked_ss", "Submitted by SS"),
        ("checked_hr", "Checked by HR"),
        ("recommended", "Recommended"),
        ("endorsed", "Endorsed"),
        ("approved", "Approved"),
        ("payment_initiated", "Payment Initiated"),
        ("payment_confirmed", "Payment Confirmed"),
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

    def _default_reference(self):
        itemList = self.env['account.wage.request'].sudo().search_count([])
        return 'WAGES/REQUEST/00' + str(itemList + 1)

    name = fields.Char('Serial No', required=True, default=_default_reference)
    company_id = fields.Many2one('res.company', 'Company',
                                 default=lambda self: self.env['res.company']._company_default_get('account.cash.request'))
    date = fields.Date(string="Date", required=True, default=fields.Date.today())
    requester_id = fields.Many2one('hr.employee', string="Requested By", required=True, default=_default_requester,
                                   readonly=True, store=True, states={'draft': [('readonly', False)]})
    department_id = fields.Many2one('hr.department', string='Department', required=True, default=_default_department,
                                    readonly=True, store=True, states={'draft': [('readonly', False)]})
    no_of_labourers = fields.Integer('No. of Labourers', required=True)
    activity_desc = fields.Char('Activity Description', required=True)
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    total_amount = fields.Monetary(string='Total Amount', store=True, compute='_compute_labour_amounts')
    from_journal_id = fields.Many2one('account.journal', string='Credit Journal',
                                      domain="[('type','in',['cash','bank'])]")
    to_journal_id = fields.Many2one('account.journal', string='Debit Journal')
    from_credit_account_id = fields.Many2one('account.account', string='Credit Account', required=False, store=True,
                                             states={'payment_confirmed': [('required', True)]})
    to_debit_account_id = fields.Many2one('account.account', string='Debit Account', required=False, store=True,
                                          states={'payment_confirmed': [('required', True)]})
    payment_line_id = fields.Many2one('account.payment', string='Disbursement Entry', readonly=True, store=True)
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft', store=True)
    line_ids = fields.One2many('account.wage.request.lines', 'wage_request_id', string="Wage Labour Lines", index=True,
                               track_visibility='onchange')
    labourer_ids = fields.One2many('account.wage.request.labourers', 'wage_request_id', string="Wage Labourers",
                                   index=True,
                                   track_visibility='onchange')
    supportive_document_line_ids = fields.One2many(comodel_name='wages.support.document.line',
                                                   string="Supportive Document",
                                                   inverse_name="document_ids")
    payment_sheet = fields.Binary("Labourers Payment Signed Sheet", attachment=True)

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
    def button_reject(self):
        self.write({'state': 'rejected'})
        return True

    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return True

    @api.multi
    def button_ss(self):
        self.write({'state': 'checked_ss'})
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        mail_content = "Dear HR," + "<br>A Wage Request Has been Checked By The Department Supervisor.Please click the link below<br/> " + str(
            base_url)
        values = {'model': 'account.wage.request',
                  'res_id': self.id,
                  'subject': "Wage Request Notification",
                  'body_html': mail_content,
                  'parent_id': None,
                  'email_from': self.department_id.branch_id.hr_manager_id.user_id.partner_id.company_id.email,
                  'email_to': self.department_id.branch_id.hr_manager_id.user_id.partner_id.email
                  }
        self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_hr(self):
        self.write({'state': 'checked_hr'})
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        mail_content = "Dear Accountant," + "<br>A Wage Request Has been Checked By The Branch HR.Please click the link below<br/> " + str(
            base_url)
        values = {'model': 'account.wage.request',
                  'res_id': self.id,
                  'subject': "Wage Request Notification",
                  'body_html': mail_content,
                  'parent_id': None,
                  'email_from': self.department_id.branch_id.accountant_id.user_id.partner_id.company_id.email,
                  'email_to': self.department_id.branch_id.accountant_id.user_id.partner_id.email
                  }
        self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_recommend(self):
        self.write({'state': 'recommended'})
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        mail_content = "Dear Branch Manager," + "<br>A Wage Request Has been Recommended By The Branch Accountant.Please click the link below<br/> " + str(
            base_url)
        values = {'model': 'account.wage.request',
                  'res_id': self.id,
                  'subject': "Wage Request Notification",
                  'body_html': mail_content,
                  'parent_id': None,
                  'email_from': self.department_id.branch_id.manager_id.user_id.partner_id.company_id.email,
                  'email_to': self.department_id.branch_id.manager_id.user_id.partner_id.email
                  }
        self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_endorse(self):
        self.write({'state': 'endorsed'})
        fm = self.env['hr.employee'].sudo().search([('is_fm', '=', True)], limit=1)
        if fm:
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            mail_content = "Dear Finance Manager," + "<br>A Wage Request Has been Endorsed By The Branch Manager.Please click the link below<br/> " + str(
                base_url)
            values = {'model': 'account.wage.request',
                      'res_id': self.id,
                      'subject': "Wage Request Notification",
                      'body_html': mail_content,
                      'parent_id': None,
                      'email_from': fm.user_id.partner_id.company_id.email,
                      'email_to': fm.user_id.partner_id.email
                      }
            self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_approve(self):
        self.write({'state': 'approved'})
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        mail_content = "Hello," + "<br>Your Wage Request Has been Approved By The Finance Manager.Please click the link below<br/> " + str(
            base_url)
        values = {'model': 'account.wage.request',
                  'res_id': self.id,
                  'subject': "Wage Request Notification",
                  'body_html': mail_content,
                  'parent_id': None,
                  'email_from': self.requester_id.user_id.partner_id.company_id.email,
                  'email_to': self.requester_id.user_id.partner_id.email
                  }
        self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_payment_initiate(self):
        self.write({'state': 'payment_initiated'})
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        mail_content = "Hello," + "<br>A Labourer Payment List Has Been Prepared By Branch Cashier.Please click the link below<br/> " + str(
            base_url)
        values = {'model': 'account.wage.request',
                  'res_id': self.id,
                  'subject': "Wage Request Notification",
                  'body_html': mail_content,
                  'parent_id': None,
                  'email_from': self.department_id.branch_id.accountant_id.user_id.partner_id.company_id.email,
                  'email_to': self.department_id.branch_id.accountant_id.user_id.partner_id.email
                  }
        self.env['mail.mail'].sudo().create(values)
        return True

    @api.multi
    def button_payment_confirm(self):
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
            self.write({'state': 'payment_confirmed', 'payment_line_id': payment_id.id})
        else:
            raise ValidationError(_('Please Select The Credit and Debit Journal'))
        return True

    @api.depends('line_ids')
    def _compute_labour_amounts(self):
        for rec in self:
            totalAmount = 0
            for line in rec.line_ids:
                totalAmount += line.total_cost
            rec.total_amount = totalAmount


class WageRequestLines(models.Model):
    _name = "account.wage.request.lines"
    _description = "Wage Request Labour List"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Labour Type', required=True)
    wage_request_id = fields.Many2one('account.wage.request', string="Wage Request")
    quantity = fields.Integer('Quantity', required=True, default=1)
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    unit_cost = fields.Monetary(string='Unit Cost', store=True, required=True)
    total_cost = fields.Float(string='Total Cost', digits=(16, 2), store=True, compute='_compute_item_total')

    @api.depends('quantity', 'unit_cost')
    def _compute_item_total(self):
        for rec in self:
            rec.total_cost = rec.quantity * rec.unit_cost


class WageRequestLabourers(models.Model):
    _name = "account.wage.request.labourers"
    _description = "Wage Request Labourers"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Labourer Name', required=True)
    wage_request_id = fields.Many2one('account.wage.request', string="Wage Request")
    contact = fields.Char('Contact', required=False)
    site = fields.Many2one(comodel_name='sites.configuration', string='Site', required=False)
    no_of_days = fields.Integer('No. of Days', required=False, default=1)
    currency_id = fields.Many2one('res.currency', required=False,
                                  default=lambda self: self.env.user.company_id.currency_id)
    unit_cost = fields.Monetary(string='Unit Cost', store=True, required=False)
    total_cost = fields.Float(string='Total Cost', digits=(16, 2), store=False, compute='_compute_pay_total')

    @api.depends('no_of_days', 'unit_cost')
    def _compute_pay_total(self):
        for rec in self:
            rec.total_cost = rec.no_of_days * rec.unit_cost


class WagesSupportDocumentLines(models.Model):
    _name = 'wages.support.document.line'

    document_name = fields.Char(string="Document Name")
    attachment = fields.Binary(string="Attachment", attachment=True, store=True, )
    attachment_name = fields.Char('Attachment Name')
    document_ids = fields.Many2one('account.wage.request', string="Document ID")


class SiteConfi(models.Model):
    _name = 'sites.configuration'

    name = fields.Char(string="Name")
    location = fields.Char(string="Location")
