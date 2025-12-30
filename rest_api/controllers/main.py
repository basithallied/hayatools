# -*- coding: utf-8 -*-
###################################################################################

# Author       :  Sayooj t k
# Copyright(c) :  2023-Present Zinfog Codelabs Pvt Ltd (<https://www.zinfog.com>).
# License      :  LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

# This program is free software:
# you can modify it under the terms of the GNU Lesser General Public License (LGPL) as
# published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

###################################################################################


import json
import pytz
import base64
import inspect
import logging
import traceback
from datetime import datetime
import datetime
from datetime import date
from werkzeug import exceptions
import odoo
from odoo.tests import Form
from odoo import api
from odoo import http
from odoo import models
from odoo import release
from odoo.http import request
from odoo.http import Response

_logger = logging.getLogger(__name__)

REST_VERSION = {
    'server_version': release.version,
    'server_version_info': release.version_info,
    'server_serie': release.serie,
    'api_version': 2,
}

NOT_FOUND = {
    'error': 'unknown_command',
}

DB_INVALID = {
    'error': 'invalid_db',
}

FORBIDDEN = {
    'error': 'token_invalid',
}

NO_API = {
    'error': 'rest_api_not_supported',
}

LOGIN_INVALID = {
    'error': 'invalid_login',
}

DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'

Auth_key = 'key=AAAAqml-PGE:APA91bEPKqBbGHannr2U6TNNlpcLtdhowFdfU0F8fuUlieyPodQwGKCn8YFTqBTvPzJAVqXI' \
           '-7V1ARflugl4V_kpGQFXsV8-Rxyf1UjmEDqc1bI1oWt6wDoNQMAC_DegrL74DiOVRlFG '


def abort(message, rollback=False, status=403):
    response = Response(json.dumps(message, sort_keys=True, indent=4, cls=ObjectEncoder), content_type='application/json;charset=utf-8', status=status)
    if request._cr and rollback:
        request._cr.rollback()
    exceptions.abort(response)


def check_token():
    token = request.params.get('token') and request.params.get('token').strip()
    if not token:
        abort(FORBIDDEN)
    env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
    uid = env['sfk_rest.token'].check_token(token)
    if not uid:
        abort(FORBIDDEN)
    request._uid = uid
    request._env = api.Environment(request.cr, uid, request.session.context or {})


def ensure_db():
    db = request.params.get('db') and request.params.get('db').strip()
    if db and db not in http.db_filter([db]):
        db = None
    if not db and request.session.db and http.db_filter([request.session.db]):
        db = request.session.db
    if not db:
        db = http.db_monodb(request.httprequest)
    if not db:
        abort(DB_INVALID, status=404)
    if db != request.session.db:
        request.session.logout()
    request.session.db = db
    try:
        env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
        module = env['ir.module.module'].search([['name', '=', "rest_api"]], limit=1)
        if module.state != 'installed':
            abort(NO_API, status=500)
    except Exception as error:

        _logger.error(error)
        abort(DB_INVALID, status=404)


def check_params(params):
    missing = []
    for key, value in params.items():
        if not value:
            missing.append(key)
    if missing:
        abort({'error': "arguments_missing %s" % str(missing)}, status=400)


class ObjectEncoder(json.JSONEncoder):
    def default(self, obj, item=None):
        def encode(item):
            if isinstance(item, models.BaseModel):
                vals = {}
                for name, field in item._fields.items():
                    if name in item:
                        if isinstance(item[name], models.BaseModel):
                            records = item[name]
                            if len(records) == 1:
                                vals[name] = (records.id, records.sudo().display_name)
                            else:
                                val = []
                                for record in records:
                                    val.append((record.id, record.sudo().display_name))
                                vals[name] = val
                        else:
                            try:
                                vals[name] = item[name].decode()
                            except UnicodeDecodeError:
                                vals[name] = item[name].decode('latin-1')
                            except AttributeError:
                                vals[name] = item[name]
                    else:
                        vals[name] = None
                return vals
            if inspect.isclass(item):
                return item.__dict__
            try:
                return json.JSONEncoder.default(self, item)
            except TypeError:
                return "error"

        try:
            try:
                result = {}
                for key, value in obj.items():
                    result[key] = encode(item)
                return result
            except AttributeError:
                result = []
                for item in obj:
                    result.append(encode(item))
                return result
        except TypeError:
            return encode(item)



class RESTController(http.Controller):

    # ----------------------------------------------------------
    # Login
    # ----------------------------------------------------------
    @http.route('/api/authenticate', auth="none", type='json', csrf=False, methods=['POST'],)
    def api_authenticate(self, db=None, login=None, password=None, **kw):
        ensure_db()
        try:
            data = json.loads(request.httprequest.data)
            credential = {'login': data['login'], 'password': data['password'], 'type': 'password'}
            uid = request.session.authenticate(data['db'],credential)
            if uid:
                env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
                user = request.env['res.users'].sudo().search([('id', '=', uid.get('uid'))])
                token = env['rest_api.token'].sudo().generate_token(user.id)
                user_type = 'van_user' if user.is_van_user else 'normal_user'
                return {'status': 200, 'msg': "Success", 'token': token.token,
                        'user_id': uid, 'partner_id': user.partner_id.id,'user_type':user_type,
                        'name': user.name}
            else:
                return {'status': 201, 'msg': "Username or Password Incorrect"}

        except Exception as error:
            return {'status': 400, 'msg': "Incorrect Username or Password"}


    # ----------------------------------------------------------
    # login refresh
    # -------------------------------------------------------
    @http.route('/api/authenticate/refresh', auth="none", type='json', csrf=False)
    def api_authenticate_refresh(self, **kw):
        try:
            data = json.loads(request.httprequest.data)
            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().refresh_token(data['token'])
            if uid:
                return {'status': 200, 'message': "Success ", 'body': uid}
            else:
                return {'status': 201, 'message': "Token authentication failed"}
        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)


    # ----------------------------------------------------------
    # STATE LIST
    # -----------------------------------------------------
    @http.route(['/api/search/state'], auth="public", type='http', csrf=False)
    def search_state(self, **kw):
        try:
            state_list = []
            for rec in request.env['res.country.state'].sudo().search([]):
                dic = {
                    'id': rec.id if rec.id else None,
                    'name': rec.name if rec.name else None
                }
                state_list.append(dic)
            return Response(
                json.dumps({"data": state_list, 'message': 'Success', 'success': True},
                           sort_keys=True, indent=4, cls=ObjectEncoder),
                content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)

    # ----------------------------------------------------------
    # COUNTRY LIST
    # -----------------------------------------------------
    @http.route(['/api/search/country'], auth="public", type='http', csrf=False)
    def search_country(self, **kw):
        try:
            country_list = []
            for rec in request.env['res.country'].sudo().search([]):
                dic = {
                    'id': rec.id if rec.id else None,
                    'name': rec.name if rec.name else None
                }
                country_list.append(dic)
            return Response(
                json.dumps({"data": country_list, 'message': 'Success', 'success': True},
                           sort_keys=True, indent=4, cls=ObjectEncoder),
                content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)

    # ----------------------------------------------------------
    # COMPANY LIST
    # -----------------------------------------------------
    @http.route(['/api/get/company/list'], auth="public", type='http', csrf=False)
    def get_company_list(self, token=None, kw=None, **kwargs):
        company_list = []
        if not token:
            return Response(
                json.dumps({"message": "Token is required", "success": False}),
                content_type='application/json;charset=utf-8',
                status=400  # Bad Request
            )

        try:
            check_params({'token': token})
            ensure_db()  # Ensure the database is available

            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().check_token(token)

            if uid:
                # Token is valid, fetch the company data
                for rec in request.env['res.company'].sudo().search([]):
                    company_list.append({
                        'company_id': rec.id if rec.id else None,
                        'company_name': rec.name if rec.name else None
                    })

                return Response(
                    json.dumps({"data": company_list, 'message': 'Success', 'success': True},
                               sort_keys=True, indent=4),
                    content_type='application/json;charset=utf-8',
                    status=200
                )
            else:
                return Response(
                    json.dumps({"status": 401, 'message': "Token authentication failed", 'success': False}),
                    content_type='application/json;charset=utf-8',
                    status=401  # Unauthorized
                )

        except Exception as error:
            _logger.error(f"Error in get_company_list API: {traceback.format_exc()}")
            return Response(
                json.dumps({"error": str(error), 'message': 'Internal server error', 'success': False}),
                content_type='application/json;charset=utf-8',
                status=500  # Internal Server Error
            )

    # ----------------------------------------------------------
    # customer creation
    # ----------------------------------------------------------
    @http.route(['/api/create/new/customer'], auth="public", methods=['POST'], type='json',csrf=False)
    def create_new_customer(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().check_token(data['token'])
            if uid:
                user = request.env['res.users'].sudo().search([('id', '=', uid)])
                customer = request.env['res.partner'].sudo().create({
                    'name': data.get('name'),
                    'mobile': data.get('mobile'),
                    'street': data.get('street'),
                    'city': data.get('city'),
                    'state_id': data.get('state_id'),
                    'country_id': data.get('country_id'),
                    'zip': data.get('zip'),
                    'user_id': user.id,
                    "customer_rank":1,
                    "vat": data.get('vat_number'),
                    "property_payment_term_id": data.get('payment_term_id'),
                })
                if customer:
                    return {'status': 200, 'message': 'Customer Created successfully','customer_id':customer.id}
                else:
                    return {'status': 400, 'message': 'Issue in Creating customer'}
            else:
                return {'status': 202, 'message': 'Token authentication failed'}
        except KeyError as key_error:
            return {'status': 202, 'message': f"Missing required parameter: {str(key_error)}"}

        except Exception as error:
            _logger.error(error)
            return {'status': 400, 'message': 'An error occurred during Customer creation.'}


    # ----------------------------------------------------------
    # all customers
    # ----------------------------------------------------------
    @http.route(['/api/search/all/customer'], auth="public", type='http', csrf=False)
    def search_all_customer(self, **kw):
        try:
            customer_list = []
            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            token = kw.get('token')
            if not token:
                for rec in request.env['res.partner'].sudo().search([('customer_rank', '>', 0)]):
                    dic = {
                        'id': rec.id if rec.id else None,
                        'name': rec.complete_name if rec.complete_name else None,
                        'mobile': rec.mobile if rec.mobile else None,
                        'street': rec.street if rec.street else None,
                        'city': rec.city if rec.city else None,
                        'state_id': rec.state_id.name if rec.state_id else None,
                        'country_id': rec.country_id.name if rec.country_id else None,
                        'zip': rec.zip if rec.zip else None,
                        'contact_type': 'customer',
                    }
                    customer_list.append(dic)
            else:
                uid = env['rest_api.token'].sudo().check_token(token)
                if not uid:
                    return Response(
                        json.dumps({'message': 'Token authentication failed ', 'success': False, 'status': 202, }, sort_keys=True,indent=4),
                        content_type='application/json;charset=utf-8', status=202)

                for rec in request.env['res.partner'].sudo().search([('customer_rank', '>', 0),('user_id', '=', uid)]):
                    dic = {
                        'id': rec.id if rec.id else None,
                        'name': rec.complete_name if rec.complete_name else None,
                        'mobile': rec.mobile if rec.mobile else None,
                        'street': rec.street if rec.street else None,
                        'city': rec.city if rec.city else None,
                        'state_id': rec.state_id.name if rec.state_id else None,
                        'country_id': rec.country_id.name if rec.country_id else None,
                        'zip': rec.zip if rec.zip else None,
                        'contact_type': 'customer',
                    }
                    customer_list.append(dic)

            return Response(json.dumps({"data": customer_list, 'message': 'Success', 'success': True},
                                       sort_keys=True, indent=4, cls=ObjectEncoder),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)

    # ----------------------------------------------------------
    # all product
    # ----------------------------------------------------------
    @http.route(['/api/search/product'], auth="public", type='http', csrf=False)
    def search_all_product(self, **kw):
        try:
            product_list = []
            user_id = kw.get('user_id')
            if not user_id:
                for rec in request.env['product.product'].sudo().search([('qty_available', '>', 0)]):
                    dic = {
                        'id': rec.id if rec.id else None,
                        'name': rec.name if rec.name else None,
                        'price': rec.lst_price if rec.lst_price else None,
                        'cost': rec.standard_price if rec.standard_price else None,
                        'image': rec.image_1920.decode("utf-8") if rec.image_1920 else None,
                        'quantity': rec.qty_available,
                    }
                    product_list.append(dic)
            if user_id:
                user = request.env['res.users'].sudo().search([('id', '=', int(user_id))], limit=1)
                if not user:
                    return {'status': 202, 'message': f"User not exists"}

                if user.allowed_location:
                    stock_quants = request.env['stock.quant'].sudo().search([
                        ('quantity', '>', 0),
                        ('location_id', '=', user.allowed_location.id)
                    ])

                    product_dict = {}
                    for rec in stock_quants:
                        product = rec.product_id
                        if product.id in product_dict:
                            product_dict[product.id]['quantity'] += rec.quantity
                        else:
                            product_dict[product.id] = {
                                'id': product.id,
                                'name': product.name,
                                'price': product.lst_price,
                                'cost': product.standard_price,
                                'image': product.image_1920.decode("utf-8") if product.image_1920 else None,
                                'quantity': rec.quantity,
                            }

                    product_list = list(product_dict.values())




            return Response(json.dumps({"data": product_list, 'message': 'Success', 'success': True},
                                       sort_keys=True, indent=4, cls=ObjectEncoder),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)


    # ----------------------------------------------------------
    # specific product
    # ----------------------------------------------------------
    @http.route(['/api/search/specific/product'], auth="public", type='http', csrf=False)
    def search_specific_product(self, **kw):
        try:
            data = json.loads(request.httprequest.data)
            product_list = []
            for rec in request.env['product.product'].sudo().search([('id', '=', data['product_id'])]):
                dic = {
                    'id': rec.id if rec.id else None,
                    'name': rec.name if rec.name else None,
                    'price': rec.lst_price if rec.lst_price else None,
                    'cost': rec.standard_price if rec.standard_price else None,
                    'image': rec.image_1920.decode("utf-8") if rec.image_1920 else None,
                }
                product_list.append(dic)
                return Response(json.dumps({"data": product_list, 'message': 'Success', 'success': True},
                                           sort_keys=True, indent=4, cls=ObjectEncoder),
                                content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)


    # ----------------------------------------------------------
    # sale order creation
    # ----------------------------------------------------------
    @http.route(['/api/create/sale/order'], auth="public", methods=['POST'], type='json', csrf=False)
    def create_sale_order(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().check_token(data['token'])

            if uid:
                user_id = request.env['res.users'].sudo().search([('id','=',uid)])
                if not data.get('product'):
                    return {'status': 202, 'message': 'Please add products'}
                if data.get('van_sale'):
                    if user_id:
                        if not user_id.allowed_location:
                            return {'status': 202, 'message': 'Please configure van user location'}
                        else:
                            for check in  data['product']:
                                product = request.env['product.product'].sudo().search([('id', '=', int(check['product_id']))])
                                stocks = request.env['stock.quant'].sudo().search([ ('product_id', '=', int(check['product_id'])), ('location_id', '=', user_id.allowed_location.id)])
                                total_qty = sum(stocks.mapped('quantity')) if stocks else 0
                                if float(check['product_uom_qty']) > total_qty:
                                    return {'status': 202, 'message': f'Insufficient quantity of - {product.name}'}

                date_format = "%d/%m/%Y"
                sale_order = request.env['sale.order'].sudo().create({
                    'partner_id': int(data['partner_id']),
                    'state': 'draft',
                    'commitment_date': datetime.datetime.strptime(str(data['date_planned']), date_format),
                    'user_id': user_id.id,
                    'app_create': True,
                    'van_sale': data.get('van_sale') if data.get('van_sale') else False
                })
                for prod in data['product']:
                    product = request.env['product.product'].sudo().search([('id', '=', prod['product_id'])])
                    if product:
                        if int(prod['product_uom_qty']) > 0:
                            lines = request.env['sale.order.line'].sudo().create({'product_id':product.id,'price_unit': prod['unit_price'],
                                                                                  'product_uom_qty': float(prod['product_uom_qty']),
                                                                                  'order_id':sale_order.id})
                if sale_order:
                    return {'status': 200, 'message': 'Sale order created successfully', 'order_id': sale_order.id}
            else:
                return {'status': 202, 'message': 'Token authentication failed'}
        except KeyError as key_error:
            return {'status': 202, 'message': f"Missing required parameter: {str(key_error)}"}
        except Exception as error:
            _logger.error(error)
            return {'status': 400, 'message': 'An error occurred during sale order creation.'}


    # ----------------------------------------------------------
    # Update Sale Quantity
    # ----------------------------------------------------------
    @http.route(['/api/update/qty'], auth="public", methods=['POST'], type='json', csrf=False)
    def update_sale_order_qty(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().check_token(data['token'])
            if not data['sale_line_id']:
                return {'status': 202, 'message': 'Please provide lines id',}
            if uid:
                user_id = request.env['res.users'].sudo().search([('id','=',uid)])
                sale_order_line = request.env['sale.order.line'].sudo().search([('id', '=', int(data['sale_line_id'])),('order_id.state', '=', 'draft')])
                if sale_order_line:
                    sale_order_line.write({'product_uom_qty':float(data['quantity'])})
                    return {'status': 200, 'message': 'Quantity updated successfully'}
                else:
                    return {'status': 202, 'message': 'Order line does not exist'}
            else:
                return {'status': 202, 'message': 'Token authentication failed'}
        except KeyError as key_error:
            return {'status': 202, 'message': f"Missing required parameter: {str(key_error)}"}
        except Exception as error:
            _logger.error(error)
            return {'status': 400, 'message': 'An error occurred during quantity updation'}

    # ----------------------------------------------------------
    # payment terms Info
    # ----------------------------------------------------------
    @http.route(['/api/search/payment/terms'], auth="public", type='http', csrf=False)
    def payment_terms(self, **kw):
        try:
            payment_terms = []
            for rec in request.env['account.payment.term'].sudo().search([]):
                dic = {
                    'id': rec.id if rec.id else None,
                    'name': rec.name if rec.name else None
                }
                payment_terms.append(dic)
            return Response(json.dumps({"data": payment_terms, 'message': 'Success', 'success': True},
                                       sort_keys=True, indent=4, cls=ObjectEncoder),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            _logger.error(error)
        abort({'error': traceback.format_exc()}, rollback=True, status=400)


    # ----------------------------------------------------------
    # sale order confirm
    # ----------------------------------------------------------
    @http.route(['/api/create/sale/order/confirm'], auth="public", methods=['POST'], type='json', csrf=False)
    def confirm_sale_order(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().check_token(data['token'])
            if uid:
                orders = request.env['sale.order'].sudo().search([('id', '=', data['order_id'])])
                if orders:
                    orders.action_confirm()
                    orders._create_invoices()
                    return {'status': 200, 'message': 'Order Confirmed successfully.', 'order_id': orders.id, 'invoice_id': orders.invoice_ids[0].id}
                else:
                    return {'status': 202, 'message': 'Order not found.'}
            else:
                return {'status': 202, 'message': 'Token authentication failed'}

        except KeyError as key_error:
            return {'status': 202, 'message': f"Missing required parameter: {str(key_error)}"}

        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)

    # ----------------------------------------------------------
    # all sale info
    # ----------------------------------------------------------
    # @http.route(['/api/search/sale/order'], auth="public", type='http', csrf=False)
    # def search_sale_order(self, **kw):
    #     try:
    #         sale_list = []
    #         for rec in request.env['sale.order'].sudo().search([]):
    #             dic = {
    #                 'name': rec.partner_id.name if rec.partner_id else None,
    #                 'created_date': rec.date_order.strftime('%Y-%m-%d'),
    #                 'total_amount': rec.amount_total,
    #                 'state': rec.state,
    #                 'order_id': rec.id if rec.id else None,
    #             }
    #             sale_list.append(dic)
    #         return Response(json.dumps({"data": sale_list, 'message': 'Success', 'success': True},
    #                                    sort_keys=True, indent=4, cls=ObjectEncoder),
    #                         content_type='application/json;charset=utf-8', status=200)
    #     except Exception as error:
    #         _logger.error(error)
    #         abort({'error': traceback.format_exc()}, rollback=True, status=400)

    @http.route(['/api/search/sale/order'], auth="public", type='http', csrf=False, methods=['GET'])
    def search_sale_order(self, **kw):
        try:
            date_param = kw.get('date')
            token = kw.get('token')
            if not token:
                return Response(json.dumps({'message': 'Please pass token', 'success': False,'status': 202,},sort_keys=True, indent=4),
                                content_type='application/json;charset=utf-8', status=202)
            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().check_token(token)
            if uid:
                if not date_param:
                    date_param = datetime.datetime.today().strftime('%Y-%m-%d')

                domain = [
                    ('date_order', '>=', date_param),
                    ('date_order', '<', date_param + " 23:59:59"),
                    ('user_id','=', uid),
                    ('app_create', '=',  True)
                    ]

                sale_list = []
                for rec in request.env['sale.order'].sudo().search(domain):
                    dic = {
                        'name': rec.partner_id.name if rec.partner_id else None,
                        'created_date': rec.date_order.strftime('%Y-%m-%d'),
                        'total_amount': rec.amount_total,
                        'state': rec.state,
                        'order_id': rec.id if rec.id else None,
                    }
                    sale_list.append(dic)
            else:
                return Response(json.dumps({'message': 'Token authentication failed', 'success': False, 'status': 202,}, sort_keys=True, indent=4),
                                content_type='application/json;charset=utf-8', status=202)

            return Response(json.dumps({"data": sale_list, 'message': 'Success', 'success': True},
                                       sort_keys=True, indent=4),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            _logger.error(error)
            return Response(json.dumps({'error': str(error)}), status=400)

    # ----------------------------------------------------------
    # specific sale info
    # ----------------------------------------------------------
    @http.route(['/api/search/specific/sale/order'], auth="public", type='http', csrf=False)
    def search_specific_sale(self, **kw):
        try:
            # data = json.loads(request.httprequest.data)
            sale_id = kw.get('sale_id')
            if not sale_id:
                return Response(json.dumps({'message': 'Please pass Sale id', 'success': True},
                                           sort_keys=True, indent=4, cls=ObjectEncoder),
                                content_type='application/json;charset=utf-8', status=202)
            sale_order = {}
            for rec in request.env['sale.order'].sudo().search([('id', '=', int(sale_id))]):
                for res in request.env['res.partner'].sudo().search([('id', '=', rec.partner_id.id)]):
                    sale_order['customer'] = {
                        'id': res.id if res.id else None,
                        'name': res.name if res.name else None,
                        'mobile': res.mobile if res.mobile else None,
                        'street': res.street if res.street else None,
                        'city': res.city if res.city else None,
                        'state_id': res.state_id.name if res.state_id else None,
                        'country_id': res.country_id.name if res.country_id else None,
                        'zip': res.zip if res.zip else None,
                    }
                sale_order['order'] = rec.name
                sale_order['state'] = rec.state
                sale_order['total_amount'] = rec.amount_total
                sale_order['created_date'] = rec.date_order.strftime('%Y-%m-%d')
                products_list = []
                for res in rec.order_line:
                    product_list = {
                        'sale_line_id': res.id,
                        'product_id': res.product_id.id if res.product_id else None,
                        'product_name': res.product_id.name if res.product_id else None,
                        'product_code': res.product_id.default_code if res.product_id.default_code else None,
                        'amount': res.price_unit,
                        'quantity': res.product_uom_qty,
                        'price_subtotal': res.price_subtotal,
                        'image': res.product_id.image_1920.decode("utf-8") if res.product_id.image_1920 else None,
                    }
                    products_list.append(product_list)
                sale_order['products'] = products_list
            if sale_order:
                return Response(json.dumps({"data": sale_order, 'message': 'Success', 'success': True},
                                       sort_keys=True, indent=4, cls=ObjectEncoder),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)


    # ----------------------------------------------------------
    # specific sale info
    # ----------------------------------------------------------

    @http.route(['/api/search/specific/invoice'], auth="public", type='http', csrf=False)
    def search_specific_invoice(self, **kw):
        try:
            invoice_id = kw.get('invoice_id')
            if not invoice_id:
                return Response(json.dumps({'message': 'Please pass invoice_id', 'success': False}),
                                content_type='application/json;charset=utf-8', status=400)

            invoice = request.env['account.move'].sudo().search([('id', '=', int(invoice_id)), ('move_type', '=', 'out_invoice')], limit=1)
            if not invoice:
                return Response(json.dumps({'message': 'Invoice not found', 'success': False}),
                                content_type='application/json;charset=utf-8', status=404)

            customer = invoice.partner_id
            invoice_data = {
                'invoice_number': invoice.name if invoice.name else '/',
                # 'invoice_date': invoice.create_date.strftime('%Y-%m-%d %I:%M %p') if invoice.create_date else None,
                'invoice_date': invoice.create_date.astimezone(pytz.timezone('Asia/Riyadh')).strftime('%Y-%m-%d %I:%M %p') if invoice.create_date else None,
                'state': invoice.state,
                'currency': invoice.currency_id.name,
                'customer': {
                    'id': customer.id,
                    'name': customer.name,
                    'vat': customer.vat,
                    'mobile': customer.mobile,
                    'email': customer.email,
                    'street': customer.street,
                    'city': customer.city,
                    'state': customer.state_id.name if customer.state_id else None,
                    'country': customer.country_id.name if customer.country_id else None,
                    'zip': customer.zip,
                },
                'amount_untaxed': invoice.amount_untaxed,
                'amount_tax': invoice.amount_tax,
                'amount_total': invoice.amount_total,
                'amount_due': invoice.amount_residual,
                'amount_word':invoice.amount_total_words,
                'products': []
            }

            for line in invoice.invoice_line_ids:
                invoice_data['products'].append({
                    'invoice_line_id': line.id,
                    'product_id': line.product_id.id if line.product_id else None,
                    'product_name': line.product_id.name if line.product_id else None,
                    'product_code': line.product_id.default_code if line.product_id else None,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'untax_total': line.price_subtotal,
                    'price_subtotal': line.price_total,
                    'taxes': [tax.name for tax in line.tax_ids],
                    'vat_amount': line.l10n_gcc_invoice_tax_amount,
                    'image': line.product_id.image_1920.decode("utf-8") if line.product_id.image_1920 else None,
                })

            return Response(json.dumps({'data': invoice_data, 'message': 'Success', 'success': True}, indent=4),
                            content_type='application/json;charset=utf-8', status=200)

        except Exception as error:
            _logger.error(f"API Error: {str(error)}\n{traceback.format_exc()}")
            return Response(json.dumps({'error': str(error), 'traceback': traceback.format_exc(), 'success': False}),
                            content_type='application/json;charset=utf-8', status=500)


    @http.route(['/api/search/invoice'], auth="public", type='http', csrf=False, methods=['GET'])
    def search_invoice(self, **kw):
        try:
            date_param = kw.get('date')
            token = kw.get('token')
            if not token:
                return Response(json.dumps({'message': 'Please pass token', 'success': False, 'status': 202}, sort_keys=True, indent=4),
                                content_type='application/json;charset=utf-8', status=202)

            env = api.Environment(request.cr, http.request.uid, request.env.context)
            uid = env['rest_api.token'].sudo().check_token(token)
            if not uid:
                return Response(json.dumps({'message': 'Token authentication failed', 'success': False, 'status': 202}, sort_keys=True, indent=4),
                                content_type='application/json;charset=utf-8', status=202)

            if not date_param:
                date_param = datetime.datetime.today().strftime('%Y-%m-%d')

            domain = [
                ('invoice_date', '>=', date_param),
                ('invoice_date', '<=', date_param),
                ('user_id', '=', uid),
                ('move_type', '=', 'out_invoice'),
                ('state', 'in', ['posted', 'paid', 'draft']),
            ]

            invoice_list = []
            for invoice in request.env['account.move'].sudo().search(domain):
                saudi_time = invoice.create_date.astimezone(pytz.timezone('Asia/Riyadh')).strftime('%Y-%m-%d %I:%M %p') if invoice.create_date else None
                dic = {
                    'customer': invoice.partner_id.name if invoice.partner_id else None,
                    'name': (invoice.name) if invoice.name else '/',
                    'invoice_date': saudi_time,
                    'total_amount': invoice.amount_total,
                    'untaxed_amount': invoice.amount_untaxed,
                    'due_amount': invoice.amount_residual,
                    'state': invoice.state,
                    'invoice_id': invoice.id,
                }
                invoice_list.append(dic)

            return Response(json.dumps({"data": invoice_list, 'message': 'Success', 'success': True}, sort_keys=True, indent=4),
                            content_type='application/json;charset=utf-8', status=200)

        except Exception as error:
            _logger.error(error)
            return Response(json.dumps({'error': str(error)}), status=400)

    @http.route(['/api/search/draft/invoice'], auth="public", type='http', csrf=False, methods=['GET'])
    def search_draft_invoice(self, **kw):
        try:
            token = kw.get('token')
            date_param = kw.get('date')

            if not token:
                return Response(
                    json.dumps({'message': 'Please pass token', 'success': False, 'status': 202}, sort_keys=True,
                               indent=4),
                    content_type='application/json;charset=utf-8', status=202)

            env = api.Environment(request.cr, http.request.uid, request.env.context)
            uid = env['rest_api.token'].sudo().check_token(token)
            if not uid:
                return Response(json.dumps({'message': 'Token authentication failed', 'success': False, 'status': 202},
                                           sort_keys=True, indent=4),
                                content_type='application/json;charset=utf-8', status=202)

            date_domain = []
            if date_param:
                date_domain = [
                    ('create_date', '>=', date_param),
                    ('create_date', '<=', date_param),
                ]

            domain = [
                ('user_id', '=', uid),
                ('move_type', '=', 'out_invoice'),
                ('state', 'in', ['draft',]),
            ]

            invoice_list = []
            for invoice in request.env['account.move'].sudo().search(domain + date_domain):
                saudi_time = invoice.create_date.astimezone(pytz.timezone('Asia/Riyadh')).strftime( '%Y-%m-%d %I:%M %p') if invoice.create_date else None
                dic = {
                    'customer': invoice.partner_id.name if invoice.partner_id else None,
                    'name': (invoice.name) if invoice.name else '/',
                    'invoice_date': saudi_time,
                    'total_amount': invoice.amount_total,
                    'untaxed_amount': invoice.amount_untaxed,
                    'due_amount': invoice.amount_residual,
                    'state': invoice.state,
                    'invoice_id': invoice.id,
                }
                invoice_list.append(dic)

            return Response(
                json.dumps({"data": invoice_list, 'message': 'Success', 'success': True}, sort_keys=True, indent=4),
                content_type='application/json;charset=utf-8', status=200)

        except Exception as error:
            _logger.error(error)
            return Response(json.dumps({'error': str(error)}), status=400)

    # ----------------------------------------------------------
    # Invoice Confirm
    # ----------------------------------------------------------
    @http.route(['/api/invoice/confirm'], auth="public", methods=['POST'], type='json', csrf=False)
    def confirm_invoice(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().check_token(data['token'])
            if uid:
                invoice = request.env['account.move'].sudo().search([('id', '=', data['invoice_id']), ('state', 'not in', ['posted','cancel'])], limit=1)
                if invoice:
                    invoice.action_post()
                    return {'status': 200, 'message': 'Invoice confirmed successfully.', 'invoice_id': invoice.id,}
                else:
                    return {'status': 202, 'message': 'Invoice not exists'}
            else:
                return {'status': 202, 'message': 'Token authentication failed'}

        except KeyError as key_error:
            return {'status': 202, 'message': f"Missing required parameter: {str(key_error)}"}

        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)


    # ----------------------------------------------------------
    # Invoice print bas64
    # ----------------------------------------------------------
    @http.route(['/api/invoice/print/base64'], auth="public", methods=['POST'], type='json', csrf=False)
    def confirm_invoice_printout_base64(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().check_token(data['token'])
            pdf_list = []

            if not uid:
                return {'status': 202, 'message': 'Token authentication failed'}

            invoice = request.env['account.move'].sudo().search([
                ('id', '=', data['invoice_id']),
                ('state', '=', 'posted')
            ], limit=1)

            if not invoice:
                return {'status': 202, 'message': 'Invoice not found or not posted.'}
            try:
                invoice.sudo().action_print_invoice_api()
                return {'status': 200, 'message': 'Invoice PDF generated successfully.', 'invoice_id': invoice.id,
                        'pdf_base64': str(invoice.report_file), 'report_name': str(invoice.report_filename), }
            except Exception as error:
                return {'status': 400, 'message': 'Error while generate pdf', 'error': traceback.format_exc()}

        except Exception as error:
            _logger.error(traceback.format_exc())
            return {'status': 400, 'message': 'Internal Server Error', 'error': traceback.format_exc()}


    # ----------------------------------------------------------
    # Invoice print pdf
    # ----------------------------------------------------------


    @http.route(['/api/invoice/print/pdf'], auth="public", methods=['POST'], type='http', csrf=False)
    def confirm_invoice_printout_pdf(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().check_token(data['token'])

            if not uid:
                return Response(json.dumps({'status': 202, 'message': 'Token authentication failed'}),
                                content_type='application/json', status=202)

            invoice = env['account.move'].sudo().search([
                ('id', '=', data['invoice_id']),
                ('state', '=', 'posted')
            ], limit=1)

            if not invoice:
                return Response(json.dumps({'status': 202, 'message': 'Invoice not found or not posted.'}),
                                content_type='application/json', status=202)

            try:
                invoice.sudo().action_print_invoice_api()
                pdf_data = base64.b64decode(invoice.report_file)
                headers = [
                    ('Content-Type', 'application/pdf'),
                    ('Content-Disposition', f'attachment; filename="{invoice.report_filename}"'),
                ]
                return Response(pdf_data, headers=headers)

            except Exception as error:
                return Response(json.dumps({
                    'status': 400,
                    'message': 'Error while generating PDF',
                    'error': traceback.format_exc()
                }), content_type='application/json', status=400)

        except Exception as error:
            _logger.error(traceback.format_exc())
            return Response(json.dumps({
                'status': 400,
                'message': 'Internal Server Error',
                'error': traceback.format_exc()
            }), content_type='application/json', status=400)



    # ----------------------------------------------------------
    # Invoice payment creation
    # ----------------------------------------------------------


    @http.route(['/api/invoice/payment/creation'], auth="public", methods=['POST'], type='json', csrf=False)
    def pay_invoice(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)

            env = api.Environment(request.cr, odoo.SUPERUSER_ID, {})
            uid = env['rest_api.token'].sudo().check_token(data['token'])

            if not uid:
                return {'status': 401, 'message': 'Token authentication failed'}

            invoice_id = data.get('invoice_id')
            journal_id = data.get('journal_id')
            amount = data.get('amount')

            if not invoice_id or not journal_id or not amount:
                return {'status': 400, 'message': 'Missing invoice_id, journal_id, or amount'}

            if amount <= 0:
                return {'status': 400, 'message': 'Amount should be grater than zero'}

            invoice = request.env['account.move'].sudo().browse(invoice_id)
            if not invoice.exists():
                return {'status': 404, 'message': 'Invoice not found'}

            if invoice.state != 'posted':
                return {'status': 400, 'message': 'Invoice must be in posted state to register payment'}

            if invoice.payment_state in ['paid', 'in_payment']:
                return {'status': 404, 'message': 'Invoice is already paid or in payment.'}

            return_form = Form(request.env["account.payment.register"].sudo().with_context(
                active_ids=invoice.ids,
                active_model="account.move",
                default_amount = float(amount),
                default_journal_id=  int(journal_id),
            ))

            return_wizard = return_form.save()
            action = return_wizard._create_payments()

            return {'status': 200, 'message': 'Payment registered successfully', 'invoice_id': invoice.id, 'due_amount': invoice.amount_residual,}

        except KeyError as key_error:
            return {'status': 400, 'message': f"Missing required parameter: {str(key_error)}"}

        except Exception as error:
            _logger.error(traceback.format_exc())
            abort({'error': traceback.format_exc()}, rollback=True, status=500)

    # ----------------------------------------------------------
    # Journals
    # ----------------------------------------------------------

    @http.route(['/api/search/payment/journal'], auth="public", type='http', csrf=False)
    def get_bank_cash_journals(self, **kw):
        try:
            journals = []
            domain = [('type', '=', ['bank', 'cash'])]
            for journal in request.env['account.journal'].sudo().search(domain):
                journals.append({
                    'id': journal.id,
                    'name': journal.name,
                    'code': journal.code,
                    'type': journal.type,
                })

            return Response(json.dumps({
                'success': True,
                'message': 'Journals fetched successfully',
                'data': journals,
            }, sort_keys=True, indent=4, cls=ObjectEncoder),
                content_type='application/json;charset=utf-8', status=200)

        except Exception as e:
            _logger.error(traceback.format_exc())
            return Response(json.dumps({
                'success': False,
                'message': 'Error occurred',
                'error': str(e),
            }, indent=4), content_type='application/json;charset=utf-8', status=500)




    # ----------------------------------------------------------
    # Customer Report
    # ----------------------------------------------------------
    @http.route(['/api/search/customer/report'], auth="public", methods=['POST'], type='json', csrf=False)
    def generate_partner_ledger_report(self, **kwargs):
        try:
            data = json.loads(request.httprequest.data)
            env = api.Environment(request.cr, http.request.uid, {})
            uid = env['rest_api.token'].sudo().check_token(data.get('token'))

            if not uid:
                return {'status': 202, 'message': 'Token authentication failed'}

            # Get user and their company
            user = request.env['res.users'].sudo().browse(uid)
            company = user.company_id

            # Get all journals for the user's company
            journal_ids = request.env['account.journal'].sudo().search([('company_id', '=', company.id)]).ids

            # Extract fields
            partner_id = data.get('customer_id')
            date_from = data.get('date_from')
            date_to = data.get('date_to')
            target_move = data.get('target_move', 'posted')

            # Parse dates
            if isinstance(date_from, str):
                date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
            if isinstance(date_to, str):
                date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()

            # Create wizard
            wizard = request.env['account.report.partner.ledger'].sudo().create({
                'partner_ids': [(6, 0, [partner_id])] if partner_id else False,
                'date_from': date_from,
                'date_to': date_to,
                'journal_ids': [(6, 0, journal_ids)],
                'company_id': company.id,
                'target_move': target_move,
                'result_selection': 'customer_supplier',
                'reconciled': True,
            })

            # Prepare report data
            data_dict = {
                'ids': [],
                'model': 'account.report.partner.ledger',
                'form': {
                    'id': wizard.id,
                    'date_from': date_from,
                    'date_to': date_to,
                    'journal_ids': journal_ids,
                    'target_move': target_move,
                    'company_id': (company.id, company.name),
                    'used_context': {
                        'journal_ids': journal_ids,
                        'state': target_move,
                        'date_from': date_from,
                        'date_to': date_to,
                        'strict_range': True,
                        'company_id': company.id,
                        'lang': 'en_US',
                    }
                }
            }

            # Generate report
            wizard._print_report(data_dict)

            # Getting data through base functions
            report_data = wizard._get_report_data(data_dict)

            # Generate pdf based on given data
            pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
                'accounting_pdf_reports.action_report_partnerledger',
                res_ids=wizard.ids,
                data=report_data
            )

            pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

            return {
                'status': 200,
                'message': 'Partner Ledger PDF generated successfully.',
                'pdf_base64': pdf_base64,
                'report_name': 'partner_ledger_report.pdf',
            }

        except Exception as e:
            _logger.error(traceback.format_exc())
            return {
                'status': 400,
                'message': 'Internal Server Error',
                'error': traceback.format_exc()
            }



    # ----------------------------------------------------------
    # State Info Based on Country
    # ----------------------------------------------------------
    @http.route(['/api/search/country_state'], auth="public", type='http', csrf=False)
    def search_country_state(self, **kw):
        try:
            state_list = []
            data = json.loads(request.httprequest.data)
            for rec in request.env['res.country.state'].sudo().search([('country_id', '=', data['country_id'])]):
                dic = {
                    'id': rec.id if rec.id else None,
                    'name': rec.name if rec.name else None
                }
                state_list.append(dic)
            return Response(json.dumps({"data": state_list, 'message': 'Success', 'success': True},
                                       sort_keys=True, indent=4, cls=ObjectEncoder),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)

            # __________________search customer balance---------------------

    @http.route(['/api/search/customer/balance'], auth="public", type='http', csrf=False)
    def search_customer_balance(self, **kw):
        try:
            sale_list = []
            sale_orders = request.env['sale.order'].sudo().search([])

            for order in sale_orders:
                partner = order.partner_id
                dic = {
                    'order_id': order.id,
                    'customer_name': partner.name if partner else None,
                    'use_partner_credit_limit': partner.use_partner_credit_limit if partner else None,
                    'credit_limit': partner.credit_limit if hasattr(partner, 'credit_limit') else None
                }
                sale_list.append(dic)


            return Response(json.dumps({"data": sale_list, 'message': 'Success', 'success': True},
                                       sort_keys=True, indent=4, cls=ObjectEncoder),
                            content_type='application/json;charset=utf-8', status=200)
        except Exception as error:
            _logger.error(error)
            abort({'error': traceback.format_exc()}, rollback=True, status=400)


    @http.route(['/api/incentives'], auth="public", type='http', csrf=False, methods=['GET'])
    def get_incentives(self, **kw):
        try:
            token = kw.get('token')
            incentive_id = kw.get('incentive_id')

            if not token:
                return Response(
                    json.dumps({'message': 'Please pass token', 'success': False, 'status': 202}, indent=4),
                    content_type='application/json;charset=utf-8', status=202
                )

            env = api.Environment(request.cr, http.request.uid, request.env.context)
            uid = env['rest_api.token'].sudo().check_token(token)

            if not uid:
                return Response(
                    json.dumps({'message': 'Token authentication failed', 'success': False, 'status': 202}, indent=4),
                    content_type='application/json;charset=utf-8', status=202
                )
            domain = []
            if not incentive_id:
                domain = [('salesperson_id', '=', uid),('state', 'in', ['approved','posted'])]
            else:
                domain = [('id', '=', int(incentive_id))]

            incentive_list = []
            incentives = request.env['salesperson.incentive'].sudo().search(domain)
            if not incentives:
                return Response(
                    json.dumps({"data": incentive_list, 'message': 'No incentives Found', 'success': False}, indent=4),
                    content_type='application/json;charset=utf-8', status=400
                )
            for incentive in incentives:
                saudi_time = (
                    incentive.create_date.astimezone(pytz.timezone('Asia/Riyadh')).strftime('%Y-%m-%d %I:%M %p')
                    if incentive.create_date else None
                )
                dic = {
                    'name': incentive.name,
                    'date_from': incentive.date_from.strftime('%Y-%m-%d') if incentive.date_from else '',
                    'date_to': incentive.date_to.strftime('%Y-%m-%d') if incentive.date_to else '',
                    'target_amount': incentive.target_amount,
                    'incentive_amount': incentive.amount,
                    'sale_amount': incentive.sale_amount,
                    'state': incentive.state,
                    'create_date': saudi_time,
                    'id': incentive.id,
                }
                incentive_list.append(dic)

            return Response(
                json.dumps({"data": incentive_list, 'message': 'Success', 'success': True}, indent=4),
                content_type='application/json;charset=utf-8', status=200
            )

        except Exception as error:
            _logger.error(error)
            return Response(
                json.dumps({'error': str(error)}),
                content_type='application/json;charset=utf-8',
                status=400
            )

