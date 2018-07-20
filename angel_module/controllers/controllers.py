# -*- coding: utf-8 -*-
from odoo import http

# class AngelModule(http.Controller):
#     @http.route('/angel_module/angel_module/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/angel_module/angel_module/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('angel_module.listing', {
#             'root': '/angel_module/angel_module',
#             'objects': http.request.env['angel_module.angel_module'].search([]),
#         })

#     @http.route('/angel_module/angel_module/objects/<model("angel_module.angel_module"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('angel_module.object', {
#             'object': obj
#         })