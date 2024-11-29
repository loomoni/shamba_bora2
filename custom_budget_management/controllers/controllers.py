# -*- coding: utf-8 -*-
from odoo import http

# class CustomBudgetManagement(http.Controller):
#     @http.route('/custom_budget_management/custom_budget_management/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_budget_management/custom_budget_management/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_budget_management.listing', {
#             'root': '/custom_budget_management/custom_budget_management',
#             'objects': http.request.env['custom_budget_management.custom_budget_management'].search([]),
#         })

#     @http.route('/custom_budget_management/custom_budget_management/objects/<model("custom_budget_management.custom_budget_management"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_budget_management.object', {
#             'object': obj
#         })