from odoo import api, fields, models


class InvoiceInherity(models.Model):
    _inherit = "account.invoice"

    reg_payment = fields.Float(string="Registration Payment", related="partner_id.applicable_fee",  required=False, )
    annual_payment = fields.Float(string="Annual Payment", related="partner_id.annual_fee", required=False, )
