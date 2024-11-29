# -*- coding: utf-8 -*-
from odoo import http

# class CustomPayroll(http.Controller):
#     @http.route('/custom_payroll/custom_payroll/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_payroll/custom_payroll/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_payroll.listing', {
#             'root': '/custom_payroll/custom_payroll',
#             'objects': http.request.env['custom_payroll.custom_payroll'].search([]),
#         })

#     @http.route('/custom_payroll/custom_payroll/objects/<model("custom_payroll.custom_payroll"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_payroll.object', {
#             'object': obj
#         })