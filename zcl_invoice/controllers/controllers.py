# -*- coding: utf-8 -*-
# from odoo import http


# class ZclInvoice/(http.Controller):
#     @http.route('/zcl_invoice//zcl_invoice/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/zcl_invoice//zcl_invoice//objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('zcl_invoice/.listing', {
#             'root': '/zcl_invoice//zcl_invoice/',
#             'objects': http.request.env['zcl_invoice/.zcl_invoice/'].search([]),
#         })

#     @http.route('/zcl_invoice//zcl_invoice//objects/<model("zcl_invoice/.zcl_invoice/"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('zcl_invoice/.object', {
#             'object': obj
#         })

