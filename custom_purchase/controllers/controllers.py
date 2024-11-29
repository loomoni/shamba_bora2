# -*- coding: utf-8 -*-
from odoo import http

# class CustomPurchase(http.Controller):
#     @http.route('/custom_purchase/custom_purchase/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_purchase/custom_purchase/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_purchase.listing', {
#             'root': '/custom_purchase/custom_purchase',
#             'objects': http.request.env['custom_purchase.custom_purchase'].search([]),
#         })

#     @http.route('/custom_purchase/custom_purchase/objects/<model("custom_purchase.custom_purchase"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_purchase.object', {
#             'object': obj
#         })