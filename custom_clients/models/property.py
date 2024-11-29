# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PropertyManagement(models.Model):
    _name = "property.management"
    _description = "Property Management"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("maintenance", "Under Maintenance"),
        ("inactive", "Inactive")
    ]

    OWNERSHIP_SELECTION = [
        ("full_owner", "100% Owner"),
        ("joint_venture", "Joint Venture"),
        ("leased", "Lease/Agreement")
    ]

    name = fields.Char('Name', required=True)
    image_small = fields.Binary("Property Image", attachment=True)
    description = fields.Text('Property Description')
    property_no = fields.Char('Property No.', required=True)
    plot_no = fields.Char('Plot No.', required=True)
    block_no = fields.Char('Block No.', required=True)
    region = fields.Many2one(comodel_name='region', string='Region', required=True)
    district = fields.Many2one(comodel_name='district.lines',  string='District', required=True)
    street = fields.Many2one(comodel_name='street.lines', string='Street', required=True)
    ownership_type = fields.Selection(OWNERSHIP_SELECTION, index=True, track_visibility='onchange', required=True,
                                      default='full_owner')
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft')
    property_document = fields.Binary("Property Document", attachment=True)
    unit_ids = fields.One2many('property.units', 'property_id', string="Property Units", index=True,
                               track_visibility='onchange')

    @api.multi
    def button_active(self):
        self.write({'state': 'active'})
        return True

    @api.multi
    def button_maintain(self):
        self.write({'state': 'maintenance'})
        return True

    @api.multi
    def button_inactive(self):
        self.write({'state': 'inactive'})
        return True

    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return True


class PropertyUnits(models.Model):
    _name = "property.units"
    _description = "Property Units"
    _rec_name = 'unit_no'

    STATE_SELECTION = [
        ("empty", "Empty"),
        ("occupied", "Occupied")
    ]

    unit_no = fields.Char(string="Unit No", required=True)
    unit_size = fields.Char(string="Unit Size", required=True)
    usage_type = fields.Char(string="Usage Type", required=True)
    currency_id = fields.Many2one('res.currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    monthly_rate = fields.Monetary(string="Untaxed Monthly Rate", required=True)
    tax_ids = fields.Many2many('account.tax', string='Taxes')
    total_monthly_rate = fields.Monetary(string="Taxed Monthly Rate", readonly=True, compute='_compute_total_rates',
                                         store=True)
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange', default='empty')
    property_id = fields.Many2one('property.management', string="Property Ref")

    @api.multi
    @api.depends('monthly_rate', 'tax_ids')
    def _compute_total_rates(self):
        for record in self:
            total = record.monthly_rate
            taxTotal = 0
            for tax in record.tax_ids:
                if tax.amount_type == 'percent':
                    taxTotal += (tax.amount / 100) * total
                else:
                    taxTotal += tax.amount
            totalCost = total + taxTotal
            record.total_monthly_rate = totalCost
