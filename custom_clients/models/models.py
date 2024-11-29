# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import math
from odoo.exceptions import ValidationError, UserError


class PropertyClientManagement(models.Model):
    _name = "property.client.management"
    _description = "Client Management"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("expired", "Expired")
    ]

    def _default_creator(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee and employee.user_id:
            return employee.user_id.partner_id.id

    name = fields.Many2one(comodel_name='res.partner', string='Full Name', required=True,
                           domain="[('customer', '=', True)]")
    tin_no = fields.Char(related='name.vat', string='TIN No', required=False, store=True)
    image_small = fields.Binary(
        "Client Image", attachment=True)
    creator_id = fields.Many2one('res.partner', string="Creator", readonly=True, store=True, default=_default_creator)
    property_id = fields.Many2one('property.management', required=True, domain=[('state', '=', 'active')])
    contract_start_date = fields.Date('Contract Start Date', required=True, store=True, default=fields.date.today())
    contract_end_date = fields.Date('Contract End Date', required=True, store=True, default=fields.date.today())
    payment_date = fields.Date(string="Payment Start Date", required=True, default=fields.Date.today())
    no_of_months = fields.Integer('No of Months', required=True, store=True)
    payment_interval = fields.Integer('Payment Interval', required=True, )
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    total_tax = fields.Monetary(string='Total Taxes', required=True, store=True)
    total_rent = fields.Monetary(string='Total Rent', required=True, store=True)
    total_paid = fields.Monetary(string='Total Paid Amount', store=True, readonly=True, compute='_amount_totals')
    total_balance = fields.Monetary(string='Total Balance', store=True, readonly=True, compute='_amount_totals')
    partner_id = fields.Many2one('res.partner', string="Client")
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft')
    payment_plan_ids = fields.One2many('property.client.payment.plan', 'client_id', string="Payment Plans", index=True,
                                       track_visibility='onchange')
    unit_ids = fields.Many2many('property.units', 'property_client_units_rel', 'client_id', 'unit_id', string='Units',
                                domain="[('property_id','=', property_id),('state','=', 'empty')]")
    invoice_ids = fields.One2many('account.invoice', 'client_contract_id', string="Client Invoices", index=True,
                                  track_visibility='onchange')
    contract_file_name = fields.Char('Contract File Name')
    signed_contract = fields.Binary(string="Signed Contract")

    @api.model
    def send_contract_expiry_notification(self):
        contracts = self.search([('contract_end_date', '=', fields.Date.today() + timedelta(days=30))])
        for contract in contracts:
            template = self.env.ref('custom_clients.email_template_contract_expiry_notification')
            template.send_mail(contract.id, force_send=True)

    def schedule_contract_expiry_notification(self):
        # Create or update the scheduled action
        action = self.env.ref('custom_clients.action_send_contract_expiry_notification')
        if action:
            action.write({
                'state': 'code',
                'code': 'model.send_contract_expiry_notification()'
            })
        else:
            action = self.env['ir.actions.server'].create({
                'name': 'Send Contract Expiry Notification',
                'model_id': self.env.ref('custom_clients.model_contract').id,
                'state': 'code',
                'code': 'model.send_contract_expiry_notification()',
                'interval_number': 30,  # Run every 30 days before
                'interval_type': 'days',
                'user_id': self.env.user.id,
            })

        # Set the action to active
        action.write({'active': True})

    @api.multi
    def button_invoice(self):
        rentProduct = self.env['product.template'].sudo().search([('name', '=', 'Rent')], limit=1)
        if not rentProduct:
            rentProduct = self.env['product.template'].sudo().create({
                'name': 'Rent',
                'sale_ok': True,
                'purchase_ok': False
            })

        productRent = self.env['product.product'].sudo().search([('product_tmpl_id', '=', rentProduct.id)],
                                                                limit=1)
        if not productRent:
            productRent = self.env['product.product'].sudo().create({
                'product_tmpl_id': rentProduct.id,
                'active': True,
            })
        line = {
            'product_id': productRent.id,
            'name': 'Rent For ' + str(self.name),
            'quantity': 1
        }
        ctx = {}
        ctx.update({'default_type': 'out_invoice'})
        ctx.update({'default_journal_type': 'sale'})
        ctx.update({'default_client_contract_id': self.id})
        ctx.update({'default_partner_id': self.partner_id.id})
        ctx.update({'default_date_invoice': fields.date.today()})
        ctx.update({'default_date_due': fields.date.today()})
        ctx.update({'default_invoice_line_ids': [(0, 0, line)]})
        return {
            'name': 'Client Rent Invoice',
            'view_id': self.env.ref('account.invoice_form').id,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'context': ctx,
            'domain': [('type', '=', 'out_invoice')]
        }

    @api.multi
    def button_active(self):
        for unit in self.unit_ids:
            unit.write({'state': 'occupied'})
            checkUnit = self.env['property.client.units'].search([('unit_id', '=', unit.id)], limit=1)
            if checkUnit:
                checkUnit.write({'client_id': self.id})
            else:
                self.env['property.client.units'].create({
                    'client_id': self.id,
                    'unit_id': unit.id
                })
        self.write({'state': 'active'})
        return True

    @api.model
    def check_and_expire_contracts(self):
        today = fields.Date.today()
        expired_contracts = self.search([('contract_end_date', '<=', today), ('state', '!=', 'expired')])
        for contract in expired_contracts:
            contract.button_expire()

    @api.multi
    def button_expire(self):
        for unit in self.unit_ids:
            unit.write({'state': 'empty'})
            checkUnit = self.env['property.client.units'].search([('unit_id', '=', unit.id)], limit=1)
            if checkUnit:
                checkUnit.write({'client_id': None})
        self.write({'state': 'expired'})
        return True

    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return True

    @api.onchange('contract_start_date', 'contract_end_date')
    @api.depends('contract_start_date', 'contract_end_date')
    def _calculate_months_no(self):
        if self.contract_start_date and self.contract_end_date:
            self.no_of_months = (self.contract_end_date.year - self.contract_start_date.year) * 12 + (
                    self.contract_end_date.month - self.contract_start_date.month)

    @api.multi
    @api.onchange('unit_ids', 'no_of_months')
    @api.depends('unit_ids', 'no_of_months')
    def onchange_unit_ids(self):
        if self.property_id:
            totalCost = 0
            for unit in self.unit_ids:
                totalCost += unit.total_monthly_rate
            self.total_rent = totalCost * self.no_of_months
            totalTax = 0
            for unit in self.unit_ids:
                total = unit.monthly_rate
                for tax in unit.tax_ids:
                    if tax.amount_type == 'percent':
                        totalTax += (tax.amount / 100) * total
                    else:
                        totalTax += tax.amount
            self.total_tax = totalTax * self.no_of_months

    @api.depends('total_rent', 'payment_plan_ids')
    def _amount_totals(self):
        for record in self:
            amountPaid = 0
            for plan in record.payment_plan_ids:
                if plan.paid:
                    amountPaid += plan.amount
            record.total_paid = amountPaid
            record.total_balance = record.total_rent - amountPaid

    # @api.model
    # def create(self, vals):
    #     res = super(PropertyClientManagement, self).create(vals)
    #     clientDets = self.env['property.client.management'].search([('id', '=', res.id)], limit=1)
    #     if clientDets:
    #         partner = self.env['res.partner'].sudo().search([('name', '=', clientDets.name)], limit=1)
    #         if not partner:
    #             partner = self.env['res.partner'].sudo().create({
    #                 'name': clientDets.name,
    #                 'customer': True
    #             })
    #         else:
    #             partner.sudo().write({'customer': True})
    #         clientDets.sudo().write({'partner_id': partner.id})
    #     return res

    @api.multi
    def compute_rent_installment(self):
        for rent in self:
            if rent.no_of_months and rent.payment_interval:
                rent.sudo().payment_plan_ids.unlink()
                date_start = datetime.strptime(str(rent.payment_date), '%Y-%m-%d')
                installment = math.ceil(rent.no_of_months / rent.payment_interval)
                amount = rent.total_rent / installment
                amountTax = rent.total_tax / installment
                untaxedAmount = amount - amountTax
                for i in range(1, installment + 1):
                    self.env['property.client.payment.plan'].create({
                        'date': date_start,
                        'untaxed_amount': untaxedAmount,
                        'tax_amount': amountTax,
                        'amount': amount,
                        'client_id': rent.id})
                    date_start = date_start + relativedelta(months=rent.payment_interval)
        return True


class PropertyClientPaymentPlan(models.Model):
    _name = "property.client.payment.plan"
    _description = "Client Payment Plans"

    STATE_SELECTION = [
        ("pending", "Pending Payment"),
        ("paid", "Paid")
    ]

    date = fields.Date(string="Payment Date", required=True)
    untaxed_amount = fields.Float(string="Untaxed Amount", required=True, default=0)
    tax_amount = fields.Float(string="Taxes", required=True, default=0)
    amount = fields.Float(string="Total Amount", required=True)
    paid = fields.Boolean(string="Paid")
    client_id = fields.Many2one('property.client.management', string="Client Ref.")
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange', default='pending')

    @api.onchange('state')
    @api.depends('state')
    def onchange_paid(self):
        if self.state == "paid":
            self.paid = True
        else:
            self.paid = False


class PropertyClientUnits(models.Model):
    _name = "property.client.units"
    _description = "Property Client Units"

    unit_id = fields.Many2one('property.units', string="Unit Ref", store=True)
    client_id = fields.Many2one('property.client.management', string="Client Ref", store=True)
    property_id = fields.Many2one('property.management', string="Property Ref", related='unit_id.property_id',
                                  store=True)


class AccountInvoicePaymentsInherit(models.Model):
    _inherit = 'account.invoice'

    client_contract_id = fields.Many2one('property.client.management', string="Client Contract Ref.")


class Region(models.Model):
    _name = 'region'
    _description = 'region table'
    _rec_name = 'name'

    name = fields.Char(string="Region Name", required=False, )
    district_line_ids = fields.One2many(comodel_name="district.lines", inverse_name="district_id",
                                        string="District IDs", required=False, )


class DistrictLine(models.Model):
    _name = 'district.lines'
    _description = 'district line table'

    name = fields.Char(string="District", required=False, )
    district_id = fields.Many2one(comodel_name="region", string="District ID", required=False, )


class District(models.Model):
    _name = 'street'
    _description = 'district table'

    district_id = fields.Many2one(comodel_name="district.lines", required=False, )
    street_line_ids = fields.One2many(comodel_name="street.lines", inverse_name="street_id",
                                      string="Street IDs", required=False, )


class StreetLines(models.Model):
    _name = 'street.lines'
    _description = 'Street line table'

    name = fields.Char(string="Name", required=False, )
    street_id = fields.Many2one(comodel_name="region", string="Street ID", required=False, )
