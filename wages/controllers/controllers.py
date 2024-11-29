# -*- coding: utf-8 -*-
from odoo import http

# class Wages(http.Controller):
#     @http.route('/wages/wages/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wages/wages/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('wages.listing', {
#             'root': '/wages/wages',
#             'objects': http.request.env['wages.wages'].search([]),
#         })

#     @http.route('/wages/wages/objects/<model("wages.wages"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wages.object', {
#             'object': obj
#         })