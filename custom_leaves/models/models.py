# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime

class LeaveCron(models.Model):
    _inherit = 'hr.leave'

    state = fields.Selection([
        ('draft', 'To Submit'),
        ('cancel', 'Cancelled'),
        ('confirm', 'To Approve'),
        ('refuse', 'Refused'),
        ('validate1', 'Second Approval'),
        ('validate', 'Approved')
        ], string='Status', readonly=True, track_visibility='onchange', copy=False, default='draft',
        help="The status is set to 'To Submit', when a leave request is created." +
        "\nThe status is 'To Approve', when leave request is confirmed by user." +
        "\nThe status is 'Refused', when leave request is refused by manager." +
        "\nThe status is 'Approved', when leave request is approved by manager.")

    @api.multi
    def action_confirm(self):
        if self.employee_id.department_id.manager_id.user_id.id == self.env.uid:
            if self.filtered(lambda holiday: holiday.state != 'draft'):
                raise UserError(_('Leave request must be in Draft state ("To Submit") in order to confirm it.'))
            self.write({'state': 'confirm'})
            self.activity_update()
        else:
            raise ValidationError(_('You are not the HOD of this employee`s department '))
        return True