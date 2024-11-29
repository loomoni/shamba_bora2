from odoo import api, fields, models, _


class FormRegistrationContact(models.Model):
    _inherit = 'res.partner'

    @api.onchange('region_select')
    def _onchange_region_select_id(self):
        sections = []
        for section in self.region_select:
            sections.append(section.id)
        return {'domain': {'district_select': [('district_id', 'in', sections)]}}

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approved'),
    ],
        string="Status", default='draft',
        track_visibility='onchange', )

    certificate = fields.Char(string="Certificate of Incorporation", required=False, )
    year_establishment = fields.Char(string="Year of Establishment", required=False, )
    business_no = fields.Char(string="Business License No", required=False, )
    company_status = fields.Selection(string="Institution Status",
                                      selection=[('private', 'Private'), ('public', 'Public'), ], required=False, )
    chairperson_name = fields.Char(string="Chairperson/President Name", required=False, )
    executive_name = fields.Char(string="CEO/MD/ED Name", required=False, )
    pobox = fields.Char(string="P.O.BOX", required=False, )
    region_select = fields.Many2one(comodel_name="region", string="Region", required=False, )
    district_select = fields.Many2one(comodel_name="district.lines", string="District", required=False, )
    ward = fields.Char(string="Ward", required=False, )
    date_registration = fields.Date(string="Member registration date", required=False, )
    sector_industry = fields.Many2one(comodel_name="configuration.setting.industry", string="Sector/ Industry",
                                      required=False, )
    cluster_id = fields.Many2one(comodel_name="configuration.setting.cluster", string="Cluster", required=False, )
    membership_cat = fields.Many2one(comodel_name="configuration.setting.category", string="Category",
                                     required=False, )
    applicable_fee = fields.Float(string="Registration Fees", related="membership_cat.registration_fee",
                                  required=False, )
    annual_fee = fields.Float(string="Annual Fees", related="membership_cat.annual_subscription_fee", required=False, )
    copy_registration_certificate_attachment = fields.Binary(string="Copy of registration certificate", attachment=True,
                                                             store=True, )
    copy_registration_certificate_file_name = fields.Char('Copy registration certificate File Name')
    chair_title = fields.Many2one(comodel_name="contact.title", string="Executive Title", required=False, )
    ceo_title = fields.Many2one(comodel_name="contact.title", string="Officer Title", required=False, )
    membership_number = fields.Char(string='Membership number', required=True, copy=False, readonly=True, index=True,
                                    default=lambda self: _('New'))
    directors_line_ids = fields.One2many(comodel_name="directors.lines", inverse_name="directors_id",
                                         string="Directors", required=False, )
    business_description_ids = fields.One2many(comodel_name="business.description",
                                               inverse_name="business_description_id", string="Business Description",
                                               required=False, )
    general_contact_lines_ids = fields.One2many(comodel_name="general.contact", inverse_name="general_contact_id",
                                                string="Campany", required=False, )
    fax = fields.Char(string="Fax", required=False, )
    dir_mobile = fields.Char(string="Mobile", required=False, )

    def button_approve(self):
        self.ensure_one()
        self.state = 'approve'

    def button_draft(self):
        self.write({'state': 'draft'})
        return True

    # Generating a rondom different number
    @api.model
    def create(self, vals):
        if vals.get('membership_number', _('New')) == _('New'):
            vals['membership_number'] = self.env['ir.sequence'].next_by_code('membership.registration.sequence') or _(
                'New')
        result = super(FormRegistrationContact, self).create(vals)
        return result
