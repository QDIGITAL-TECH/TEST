# -*- coding: utf-8 -*-
from odoo import http

# class Procurement.group.mod(http.Controller):
#     @http.route('/procurement.group.mod/procurement.group.mod/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/procurement.group.mod/procurement.group.mod/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('procurement.group.mod.listing', {
#             'root': '/procurement.group.mod/procurement.group.mod',
#             'objects': http.request.env['procurement.group.mod.procurement.group.mod'].search([]),
#         })

#     @http.route('/procurement.group.mod/procurement.group.mod/objects/<model("procurement.group.mod.procurement.group.mod"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('procurement.group.mod.object', {
#             'object': obj
#         })