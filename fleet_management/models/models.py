# -*- coding: utf-8 -*-

from odoo import models, fields, api

class FleetVehicleRegistration(models.Model):
    _name = "fleet.vehicle.registration"
    _description = "Vehicle Registration"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reg_no'

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("active", "Active"),
        ("under_maintainance", "Under Maintainance"),
        ("not_running", "Not Running")
    ]

    def _default_department(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee and employee.department_id:
            return employee.department_id.id


    name = fields.Char('Vehicle Name', required=True)
    reg_no = fields.Char('Registration No', required=True)
    vehicle_model = fields.Char('Model Name', required=True)
    date = fields.Date(string="Date", required=True, default=fields.Date.today())
    image_small = fields.Binary("Vehicle Image", attachment=True)
    responsible_driver_id = fields.Many2one('hr.employee', string="Responsible Driver", store=True)
    department_id = fields.Many2one('hr.department', string='Department', required=True, default=_default_department, store=True)
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft', store=True)
    assignment_ids = fields.One2many('fleet.vehicle.assignments', 'vehicle_id', string="Vehicle Assignments", index=True,
                               track_visibility='onchange')
    gate_pass_ids = fields.One2many('fleet.vehicle.gatepass', 'vehicle_id', string="Vehicle GatePass",
                                    index=True, track_visibility='onchange')

    @api.multi
    def button_active(self):
        self.write({'state': 'active'})
        return True

    @api.multi
    def button_maintain(self):
        self.write({'state': 'under_maintainance'})
        return True

    @api.multi
    def button_disabled(self):
        self.write({'state': 'not_running'})
        return True

    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return True


class FleetVehicleAssignment(models.Model):
    _name = "fleet.vehicle.assignments"
    _description = "Vehicle Assignment"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("recommended", "Recommended"),
        ("approved", "Approved"),
        ("rejected", "Rejected")
    ]

    def _default_reference(self):
        itemList = self.env['fleet.vehicle.assignments'].sudo().search_count([])
        return 'VEHICLE/ASSIGN/00' + str(itemList + 1)

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
    date = fields.Date(string="Request Date", required=True, default=fields.Date.today())
    vehicle_id = fields.Many2one('fleet.vehicle.registration', string="Vehicle", domain=[('state','=','active')])
    requester_id = fields.Many2one('hr.employee', string="Requested By", required=True, default=_default_requester,
                                   readonly=True, store=True, states={'draft': [('readonly', False)]})
    driver_id = fields.Many2one('hr.employee', string="Driver", required=True, default=_default_requester,
                                   readonly=True, store=True, states={'draft': [('readonly', False)]})
    department_id = fields.Many2one('hr.department', string='Department', required=True, default=_default_department,
                                    store=True)
    purpose = fields.Text('Purpose', required=True)
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft', store=True)


    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         'Assignment Serial No Must be Unique'),
    ]

    @api.multi
    def button_recommend(self):
        self.write({'state': 'recommended'})
        return True

    @api.multi
    def button_approve(self):
        self.write({'state': 'approved'})
        return True

    @api.multi
    def button_reject(self):
        self.write({'state': 'rejected'})
        return True

    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return True


class FleetVehicleGatePass(models.Model):
    _name = "fleet.vehicle.gatepass"
    _description = "Vehicle GatePass"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    STATE_SELECTION = [
        ("draft", "Draft"),
        ("approved", "Approved"),
        ("checked", "checked By Security"),
        ("returned", "Returned"),
        ("rejected", "Rejected")
    ]

    def _default_reference(self):
        itemList = self.env['fleet.vehicle.assignments'].sudo().search_count([])
        return 'VEHICLE/GATEPASS/00' + str(itemList + 1)

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
    date = fields.Date(string="Gate-Pass Date", required=True, default=fields.Date.today())
    vehicle_id = fields.Many2one('fleet.vehicle.registration', string="Vehicle", domain=[('state','=','active')])
    driver_id = fields.Many2one('hr.employee', string="Driver", required=True, default=_default_requester,
                                   readonly=True, store=True, states={'draft': [('readonly', False)]})
    department_id = fields.Many2one('hr.department', string='Department', required=True, default=_default_department,
                                    store=True)
    purpose = fields.Text('Purpose', required=True)
    time_out = fields.Char('Time Out', readonly=True, store=True, states={'approved': [('readonly', False)]})
    km_out = fields.Char('KM Out', readonly=True, store=True, states={'approved': [('readonly', False)]})
    km_in = fields.Char('KM In', readonly=True, store=True, states={'checked': [('readonly', False)]})
    state = fields.Selection(STATE_SELECTION, index=True, track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='draft', store=True)


    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         'GatePass Serial No Must be Unique'),
    ]

    @api.multi
    def button_approve(self):
        self.write({'state': 'approved'})
        return True

    @api.multi
    def button_check(self):
        self.write({'state': 'checked'})
        return True

    @api.multi
    def button_return(self):
        self.write({'state': 'returned'})
        return True

    @api.multi
    def button_reject(self):
        self.write({'state': 'rejected'})
        return True

    @api.multi
    def button_reset(self):
        self.write({'state': 'draft'})
        return True