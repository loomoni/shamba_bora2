# -*- coding: utf-8 -*-
from odoo import http

# class CashRequests(http.Controller):
#     @http.route('/cash_requests/cash_requests/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/cash_requests/cash_requests/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('cash_requests.listing', {
#             'root': '/cash_requests/cash_requests',
#             'objects': http.request.env['cash_requests.cash_requests'].search([]),
#         })

#     @http.route('/cash_requests/cash_requests/objects/<model("cash_requests.cash_requests"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('cash_requests.object', {
#             'object': obj
#         })