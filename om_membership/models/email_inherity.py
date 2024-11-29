from odoo import api, fields, models


class EmailInherity(models.Model):
    _inherit = "mail.mass_mailing.contact"

    @api.onchange('name')
    def _onchange_name_id(self):
        categories = []
        for category in self.name:
            categories.append(category.id)
        return {'domain': {'company_name': [('membership_cat', 'in', categories)]}}

    @api.onchange('company_name')
    def _onchange_company_name_id(self):
        email = []
        for emails in self.company_name:
            email.append(emails.id)
        return {'domain': {'contact_name': [('general_contact_id', 'in', email)]}}

    name = fields.Many2one(comodel_name="configuration.setting.category", string="Category", required=False, )
    company_name = fields.Many2one(comodel_name="res.partner", string="Company", required=False, )
    contact_name = fields.Many2one(comodel_name="general.contact", string="Emails", required=False, )
    # email = fields.Char(string="Email", related="contact_name.email", required=False)
    # email = fields.Many2one(comodel_name="general.contact", string="Email", required=False)

