from odoo import http, api
from odoo.http import request


class RegistrationForm(http.Controller):
    @http.route('/registration_form', type="http", auth="public", website=True)
    def members_registration_webform(self, **kw):
        industry_rec = request.env['configuration.setting.industry'].sudo().search([])
        cluster_rec = request.env['configuration.setting.cluster'].sudo().search([])
        region_rec = request.env['region'].sudo().search([])
        district_rec = request.env['district.lines'].sudo().search([])
        membership_category_rec = request.env['configuration.setting.category'].sudo().search([])
        return http.request.render('custom_membership.registration_template_form_id', {
            'industry_rec': industry_rec,
            'cluster_rec': cluster_rec,
            'region_rec': region_rec,
            'district_rec': district_rec,
            'membership_category_rec': membership_category_rec})

    @http.route('/create/registration', type="http", auth="public", website=True)
    def create_webpatient(self, **kw):
        print("Data Received.....", kw)
        request.env['res.partner'].sudo().create(kw)
        return request.render("custom_membership.member_thanks", {})
