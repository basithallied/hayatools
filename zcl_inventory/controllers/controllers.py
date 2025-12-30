# -*- coding: utf-8 -*-
# from odoo import http


# class ZclInventory/(http.Controller):
#     @http.route('/zcl_inventory//zcl_inventory/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zcl_inventory//zcl_inventory//objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zcl_inventory/.listing', {
#             'root': '/zcl_inventory//zcl_inventory/',
#             'objects': http.request.env['zcl_inventory/.zcl_inventory/'].search([]),
#         })

#     @http.route('/zcl_inventory//zcl_inventory//objects/<model("zcl_inventory/.zcl_inventory/"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zcl_inventory/.object', {
#             'object': obj
#         })

