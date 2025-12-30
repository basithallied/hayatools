# -*- coding: utf-8 -*-
# from odoo import http


# class ZclSale/(http.Controller):
#     @http.route('/zcl_sale//zcl_sale/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zcl_sale//zcl_sale//objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zcl_sale/.listing', {
#             'root': '/zcl_sale//zcl_sale/',
#             'objects': http.request.env['zcl_sale/.zcl_sale/'].search([]),
#         })

#     @http.route('/zcl_sale//zcl_sale//objects/<model("zcl_sale/.zcl_sale/"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zcl_sale/.object', {
#             'object': obj
#         })

