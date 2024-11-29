from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class FormRegistration(models.Model):
    _name = "form.registration"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Registration form membership table"
#
#     @api.onchange('region_select')
#     def _onchange_region_select_id(self):
#         sections = []
#         for section in self.region_select:
#             sections.append(section.id)
#         return {'domain': {'district_select': [('district_id', 'in', sections)]}}
#
#     state = fields.Selection([
#         ('draft', 'Draft'),
#         ('approve', 'Approved'),
#     ],
#         string="Status", default='draft',
#         track_visibility='onchange', )
#
#     region_select = fields.Many2one(comodel_name="region", string="Region", required=False, )
#     district_select = fields.Many2one(comodel_name="district.lines", string="District", required=False, )
#     name = fields.Char(string="Name", required=True)
#     certificate = fields.Char(string="Certificate of Incorporation", required=False, )
#     year_establishment = fields.Char(string="Year of Establishment", required=False, )
#     membership_number = fields.Char(string='Membership number', required=True, copy=False, readonly=True, index=True,
#                                     default=lambda self: _('New'))
#     business_no = fields.Char(string="Business License No", required=False, )
#     company_status = fields.Selection(string="Institution Status",
#                                       selection=[('private', 'Private'), ('public', 'Public'), ], required=False, )
#     chairperson_name = fields.Char(string="Chairperson/President Name", required=False, )
#     executive_name = fields.Char(string="CEO/MD/ED Name", required=False, )
#     copy_registration_certificate_attachment = fields.Binary(string="Copy of registration certificate", attachment=True,
#                                                              store=True, )
#     copy_registration_certificate_file_name = fields.Char('Copy registration certificate File Name')
#     date_registration = fields.Date(string="Member registration date", required=False, )
#     sector_industry = fields.Many2one(comodel_name="configuration.setting.industry", string="Sector/ Industry",
#                                       required=False, )
#     cluster_id = fields.Many2one(comodel_name="configuration.setting.cluster", string="Cluster", required=False, )
#     membership_cat = fields.Many2one(comodel_name="configuration.setting.category", string="Category",
#                                      required=False, )
#     applicable_fee = fields.Float(string="Registration Fees", related="membership_cat.registration_fee",
#                                   required=False, )
#     annual_fee = fields.Float(string="Annual Fees", related="membership_cat.annual_subscription_fee", required=False, )
#     street = fields.Char(string="Street", required=False, )
#     street_two = fields.Char(string="Street two", required=False, )
#     chair_title = fields.Many2one(comodel_name="contact.title", string="Executive Title", required=False, )
#     ceo_title = fields.Many2one(comodel_name="contact.title", string="Officer Title", required=False, )
#     ward = fields.Char(string="Ward", required=False, )
#     pobox = fields.Char(string="P.O.BOX", required=False, )
#     telephone = fields.Char(string="Tel Phone", required=False, )
#     email = fields.Char(string="Email", required=False, )
#     website = fields.Char(string="Website", required=False, )
#     directors_line_ids = fields.One2many(comodel_name="directors.lines", inverse_name="directors_id",
#                                          string="Directors", required=False, )
#     business_description_ids = fields.One2many(comodel_name="business.description",
#                                                inverse_name="business_description_id", string="Business Description",
#                                                required=False, )
#     general_contact_lines_ids = fields.One2many(comodel_name="general.contact", inverse_name="general_contact_id",
#                                                 string="Campany", required=False, )
#
#     def button_approve(self):
#         self.ensure_one()
#         self.state = 'approve'
#
#     def button_draft(self):
#         self.write({'state': 'draft'})
#         return True
#
#     # Generating a rondom different number
#     @api.model
#     def create(self, vals):
#         if vals.get('membership_number', _('New')) == _('New'):
#             vals['membership_number'] = self.env['ir.sequence'].next_by_code('membership.registration.sequence') or _(
#                 'New')
#         result = super(FormRegistration, self).create(vals)
#         return result


class DirectorsLines(models.Model):
    _name = "directors.lines"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "directors record table"
    _rec_name = "name"

    name = fields.Char(string="Name", required=False, )
    nationality = fields.Char(string="Nationality", required=False, )
    directors_id = fields.Many2one(comodel_name="res.partner", string="Directors Id", required=False, )


class BusinessDescription(models.Model):
    _name = "business.description"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "business description table"

    business_description = fields.Text(string="Business Description", required=False, )
    business_description_id = fields.Many2one(comodel_name="res.partner", string="Business Description Id",
                                              required=False, )


class GeneralContact(models.Model):
    _name = "general.contact"
    _description = "table to store general contact of hte company"
    _rec_name = 'email'

    name = fields.Char(string="Contact Name", required=True)
    title = fields.Many2one(comodel_name="contact.title", string="Title", required=False, )
    job_position = fields.Char(string="Job Position", required=False)
    phone = fields.Char(string="Phone", required=False)
    email = fields.Char(string="Email", required=False)
    mobile = fields.Char(string="Mobile", required=False)
    general_contact_id = fields.Many2one(comodel_name="res.partner", string="General Contact", required=False, )


class Payment(models.Model):
    _name = "payment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Record payment table"

    name = fields.Many2one(comodel_name="res.partner", string="Company Name", required=True, )
    reg_fee = fields.Float(string="registration fee", related="name.applicable_fee", required=False,
                           group_operator=True)
    annual_fee = fields.Float(string="annual fee", related="name.annual_fee", required=False, group_operator=True)
    fee_amount = fields.Float(string="Amount", required=True, compute="amount_required", group_operator=True)
    amount_paid = fields.Float(string="Amount Paid", required=False, compute="amount_paid_compute", group_operator=True)
    amount_remain = fields.Float(string="Amount Remain", required=False, compute="compute_amount_remain_unpaid",
                                 group_operator=True)
    category = fields.Char(string="Category", related="name.membership_cat.name", required=False, )
    cluster = fields.Char(string="Cluster", related="name.cluster_id.name", required=False, )
    pay_year = fields.Selection(string="For Year", selection=[('2017', '2017'), ('2018', '2018'), ('2019', '2019'),
                                                              ('2020', '2020'), ('2021', '2021'), ('2022', '2022'),
                                                              ('2023', '2023'), ('2024', '2024'), ('2025', '2025'),
                                                              ('2026', '2026'), ('2027', '2027'), ('2028', '2028'),
                                                              ('2029', '2029'), ('2030', '2030'), ('2031', '2031'),
                                                              ('2032', '2032'), ('2033', '2033'), ('2034', '2034'),
                                                              ('2035', '2035'), ('2036', '2036'), ('2037', '2037'),
                                                              ('2038', '2038'), ('2039', '2039'), ('2040', '2040'),
                                                              ('2041', '2041'), ('2042', '2042'), ('2043', '2043'),
                                                              ('2044', '2044'), ('2045', '2045'), ('2046', '2046'),
                                                              ('2047', '2047'), ('2048', '2048'), ('2049', '2049'),
                                                              ('2050', '2050'), ('2051', '2051'), ('2052', '2052'),
                                                              ('2053', '2053'), ('2054', '2054'), ('2055', '2055'),
                                                              ('2056', '2056'), ('2057', '2057'), ('2058', '2058'),
                                                              ('2059', '2059'), ('2060', '2060'), ('2061', '2061'),
                                                              ('2062', '2062'), ('2063', '2063'), ('2064', '2064'),
                                                              ('2065', '2065'), ('2066', '2066'), ('2067', '2067'),
                                                              ('2068', '2068'), ('2069', '2069'), ('2070', '2070'),
                                                              ('2071', '2071'), ('2072', '2072'), ('2073', '2073'),
                                                              ('2074', '2074'), ('2075', '2075'), ('2076', '2076'),
                                                              ('2077', '2077'), ('2078', '2078'), ('2079', '2079'),
                                                              ('2080', '2080'), ('2081', '2081'), ('2082', '2082'),
                                                              ('2083', '2083'), ('2084', '2084'), ('2085', '2085'),
                                                              ('2086', '2086'), ('2087', '2087'), ('2088', '2089'),
                                                              ('2090', '2090'), ('2091', '2091'), ('2092', '2092'),
                                                              ('2093', '2093'), ('2094', '2094'), ('2095', '2095'),
                                                              ('2096', '2096'), ('2097', '2097'), ('2098', '2098'),
                                                              ('2099', '2099'), ('3000', '3000'), ],
                                required=False, )
    pay_date = fields.Date(string="Payment Date", required=False, )
    type = fields.Selection(string="Type of Payment", selection=[('annual', 'Annual'),
                                                                 ('reg_fee', 'Registration Fees'), ], required=True, )
    receipt = fields.Binary(string="Attach Receipt", attachment=True, store=True, )
    receipt_file_name = fields.Char('Receipt File Name')
    state = fields.Selection(string="Status", selection=[('unpaid', 'Unpaid'),
                                                         ('partial', 'Partial Paid'),
                                                         ('paid', 'Paid'),
                                                         ], track_visibility='onchange',
                             readonly=True, required=True, copy=False, default='unpaid')
    is_active = fields.Boolean(string="Active", default=False)
    payment_lines_ids = fields.One2many(comodel_name="payment.lines", inverse_name="payment_id", string="Payment Lines",
                                        required=False, )

    @api.depends('payment_lines_ids.amount_payment')
    def amount_paid_compute(self):
        for record in self:
            paid = 0
            for line in record.payment_lines_ids:
                paid += line.amount_payment
            record.amount_paid = paid

    @api.depends('type', 'annual_fee', 'reg_fee')
    def amount_required(self):
        for rec in self:
            if rec.type == 'annual':
                rec.fee_amount = rec.annual_fee
            elif rec.type == 'reg_fee':
                rec.fee_amount = rec.reg_fee

    @api.depends('fee_amount', 'amount_paid')
    def compute_amount_remain_unpaid(self):
        for rec in self:
            rec.amount_remain = rec.fee_amount - rec.amount_paid

    @api.multi
    def button_approve(self):
        for rec in self:
            if rec.amount_paid != rec.fee_amount:
                raise ValidationError(
                    _("Fee amount should be equal to paid amount, Payment is marked as Partial Payment"))
        self.write({'state': 'paid'})
        return True

    @api.depends('amount_paid', 'fee_amount')
    @api.multi
    def button_partial_paid(self):
        for rec in self:
            if rec.amount_paid == rec.fee_amount:
                raise ValidationError(_("The payment is marked as full paid not partial"))
            elif rec.amount_paid > rec.fee_amount:
                raise ValidationError(_("Amount Paid should be less or equal to fee amount"))
        self.write({'state': 'partial'})
        return True


class PaymentsLines(models.Model):
    _name = "payment.lines"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "payments line records table"

    amount_payment = fields.Float(string="Amount Paid", required=False, )
    payment_date = fields.Date(string="Date", required=False, )
    receipt = fields.Binary(string="Receipt", attachment=True, store=True, )
    receipt_file_name = fields.Char('Receipt File Name')
    payment_id = fields.Many2one(comodel_name="payment", string="Payment ID", required=False, )


class ConfigurationSettingCategory(models.Model):
    _name = "configuration.setting.category"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "configuration setting table category"
    _rec_name = "name"

    name = fields.Char(string="Category name", required=True, )
    registration_fee = fields.Float(string="Registration Fee", required=False, )
    annual_subscription_fee = fields.Float(string="Annual Subscription Fee", required=False, )


class ConfigurationSettingCluster(models.Model):
    _name = "configuration.setting.cluster"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "configuration setting table cluster "
    _rec_name = "name"

    name = fields.Char(string="Cluster name", required=True, )


class ConfigurationSettingIndustry(models.Model):
    _name = "configuration.setting.industry"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "configuration setting table cluster "
    _rec_name = "name"

    name = fields.Char(string="Industry Type", required=True, )


class ContactTitle(models.Model):
    _name = "contact.title"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "contact title table"
    _rec_name = "name"

    name = fields.Char(string="Title", required=True, )
    abbreviation = fields.Char(string="Abbreviation", required=False, )


class Engagement(models.Model):
    _name = "engagement"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Engagement recording Table"

    @api.onchange('region_select')
    def _onchange_region_select_id(self):
        sections = []
        for section in self.region_select:
            sections.append(section.id)
        return {'domain': {'district_select': [('district_id', 'in', sections)]}}

    member_non_members = fields.Boolean(string="Is Member", default=True )
    blacklist = fields.Boolean(string="blacklist", )
    region_select = fields.Many2one(comodel_name="region", string="Region", required=False, )
    district_select = fields.Many2one(comodel_name="district.lines", string="District", required=False, )
    member_field = fields.Many2many(comodel_name="res.partner", string="Member", required=False, )
    non_member_field = fields.Char(string="Non Member", required=False, )
    agenda = fields.Char(string="Agenda", required=False, )
    engagement_type = fields.Many2one(comodel_name="engagement.type", string="Engagement Type", required=False, )
    description = fields.Text(string="Description", required=False, )
    date = fields.Date(string="Date", required=False, )
    location_name = fields.Char(string="Location Name", required=False, )
    venue_name = fields.Char(string="Venue", required=False, )
    state_select = fields.Many2one(comodel_name="status", string="Status", required=False, )
    # Selection(string="Status",
    #                             selection=[('initiated', 'Initiated'), ('ongoing', 'Ongoing'),
    #                                        ('completed', 'Completed'), ], required=False, )
    outcome = fields.Char(string="Outcome", required=False, )
    attachment_copy = fields.Binary(string="Attachment", attachment=True,
                                    store=True, )
    attachment_copy_file_name = fields.Char('Attachment File Name')


class Issue(models.Model):
    _name = "issue"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Issue table"

    @api.onchange('region_select')
    def _onchange_region_select_id(self):
        sections = []
        for section in self.region_select:
            sections.append(section.id)
        return {'domain': {'district_select': [('district_id', 'in', sections)]}}

    region_select = fields.Many2one(comodel_name="region", string="Region", required=False, )
    district_select = fields.Many2one(comodel_name="district.lines", string="District", required=False, )
    name = fields.Char(string="Issue Name", required=True, )
    member_other = fields.Many2many(comodel_name="res.partner", string="Member", required=False, )
    date = fields.Date(string="Date", required=False, )
    status = fields.Many2one(comodel_name="status", string="Status", required=False, )
    location_name = fields.Char(string="Location Name", required=False, )
    issue_type_id = fields.Many2one(comodel_name="issue.type", string="Issue Type", required=False, )
    recommended_intervation = fields.Text(string="Recommended Intervation", required=False, )
    received_by = fields.Char(string="Received by", required=False, )
    issue_summary = fields.Text(string="Issue Summary", required=False, )
    conclusion = fields.Text(string="Conclusion", required=False, )


class Event(models.Model):
    _name = "event"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "event table"

    @api.onchange('region_select')
    def _onchange_region_select_id(self):
        sections = []
        for section in self.region_select:
            sections.append(section.id)
        return {'domain': {'district_select': [('district_id', 'in', sections)]}}

    region_select = fields.Many2one(comodel_name="region", string="Region/city", required=False, )
    district_select = fields.Many2one(comodel_name="district.lines", string="District", required=False, )
    name = fields.Char(string="Event Name", required=True, )
    expected_no_participant = fields.Integer(string="Expected No of Participant", required=False, )
    start_date = fields.Datetime(string="Start date and time", required=False, )
    finish_date = fields.Datetime(string="Finish date and time", required=False, )
    description = fields.Text(string="Description", required=False, )
    event_them = fields.Many2one(comodel_name="event.theme", string="Event Theme", required=False, )
    event_organizer = fields.Char(string="Event Organizer", required=False, )
    venue = fields.Char(string="Venue", required=False, )
    location_name = fields.Char(string="Location Name", required=False, )
    stakeholder = fields.Char(string="Stakeholder/Participant", required=False, )
    activity_summary = fields.Text(string="Activity Summary", required=False, )
    conclusion = fields.Text(string="Conclusion/Outcome", required=False, )
    attachment_copy = fields.Binary(string="Event Report", attachment=True,
                                    store=True, )
    attachment_copy_file_name = fields.Char('Attachment File Name')


class EngagementType(models.Model):
    _name = "engagement.type"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Engagement Type table"
    _rec_name = "name"

    name = fields.Char(string="Engagement Type", required=True, )


class IssueType(models.Model):
    _name = "issue.type"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Issue Type table"

    name = fields.Char(string="Issue Type", required=True, )


class EventTheme(models.Model):
    _name = "event.theme"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Event Theme Table"

    name = fields.Char(string="Event Theme", required=True, )


class Status(models.Model):
    _name = "status"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Status Table"

    name = fields.Char(string="Status", required=True, )


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


class ChairPersonTitle(models.Model):
    _name = "chair.person.title"
    _description = "Chair person Title table"

    name = fields.Char(string="Title", required=True, )


class CeoTitle(models.Model):
    _name = "ceo.title"
    _description = "CEO, MD, ED table"

    name = fields.Char(string="Title", required=True, )
