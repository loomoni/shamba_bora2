# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime


class PurchaseOrderCustom(models.Model):
    _inherit = 'purchase.order'

    supportive_document_line_ids = fields.One2many(comodel_name='purchase.support.document.line',
                                                   string="Supportive Document",
                                                   inverse_name="document_ids")

    def _default_requester(self):
        employee = self.env['hr.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)
        if employee:
            return employee.id

    requester_id = fields.Many2one('hr.employee', string="Requested By", required=True, default=_default_requester,
                                   readonly=True, store=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Draft'),
        ('confirmed', 'Confirmed by PO'),
        ('to approve', 'Recommended By Accountant'),
        ('fm_review', 'Reviewed by FM'),
        ('purchase', 'Approved by MD'),
        ('cashier_handle', 'Cashier'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='sent', track_visibility='onchange')

    @api.multi
    def button_confirm(self):
        self.write({'state': 'confirmed'})
        return {}

    @api.multi
    def button_recommend(self):
        self.write({'state': 'to approve'})
        return {}

    @api.multi
    def button_fm_review(self):
        self.write({'state': 'fm_review'})
        return {}

    @api.multi
    def button_approve(self, force=False):
        self._add_supplier_to_product()
        self.write({'state': 'purchase', 'date_approve': fields.Date.context_today(self)})
        self.filtered(lambda p: p.company_id.po_lock == 'lock').write({'state': 'done'})
        return {}

    @api.multi
    def button_cashier(self):
        self.write({'state': 'cashier_handle'})
        return {}


class PurchaseSupportDocumentLines(models.Model):
    _name = 'purchase.support.document.line'

    document_name = fields.Char(string="Document Name")
    attachment = fields.Binary(string="Attachment", attachment=True, store=True, )
    attachment_name = fields.Char('Attachment Name')
    document_ids = fields.Many2one('purchase.order', string="Document ID")
