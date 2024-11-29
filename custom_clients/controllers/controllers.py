# -*- coding: utf-8 -*-
from odoo import http

# class CustomClients(http.Controller):
#     @http.route('/custom_clients/custom_clients/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/custom_clients/custom_clients/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('custom_clients.listing', {
#             'root': '/custom_clients/custom_clients',
#             'objects': http.request.env['custom_clients.custom_clients'].search([]),
#         })

#     @http.route('/custom_clients/custom_clients/objects/<model("custom_clients.custom_clients"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('custom_clients.object', {
#             'object': obj
#         })