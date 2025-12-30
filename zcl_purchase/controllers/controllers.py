# -*- coding: utf-8 -*-
# from odoo import http


# class ZclPurchase/(http.Controller):
#     @http.route('/zcl_purchase//zcl_purchase/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zcl_purchase//zcl_purchase//objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zcl_purchase/.listing', {
#             'root': '/zcl_purchase//zcl_purchase/',
#             'objects': http.request.env['zcl_purchase/.zcl_purchase/'].search([]),
#         })

#     @http.route('/zcl_purchase//zcl_purchase//objects/<model("zcl_purchase/.zcl_purchase/"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zcl_purchase/.object', {
#             'object': obj
#         })

