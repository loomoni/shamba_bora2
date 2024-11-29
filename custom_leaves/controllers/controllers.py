# -*- coding: utf-8 -*-
from odoo import http

# class CustomLeaves(http.Controller):
#     @http.route('/custom_leaves/custom_leaves/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_leaves/custom_leaves/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_leaves.listing', {
#             'root': '/custom_leaves/custom_leaves',
#             'objects': http.request.env['custom_leaves.custom_leaves'].search([]),
#         })

#     @http.route('/custom_leaves/custom_leaves/objects/<model("custom_leaves.custom_leaves"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_leaves.object', {
#             'object': obj
#         })