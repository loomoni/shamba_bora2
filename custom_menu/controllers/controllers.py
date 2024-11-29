# -*- coding: utf-8 -*-
from odoo import http

# class CustomMenu(http.Controller):
#     @http.route('/custom_menu/custom_menu/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_menu/custom_menu/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_menu.listing', {
#             'root': '/custom_menu/custom_menu',
#             'objects': http.request.env['custom_menu.custom_menu'].search([]),
#         })

#     @http.route('/custom_menu/custom_menu/objects/<model("custom_menu.custom_menu"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_menu.object', {
#             'object': obj
#         })