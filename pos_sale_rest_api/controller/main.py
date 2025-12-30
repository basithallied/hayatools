import json
import logging
from odoo import http, fields
from odoo.http import request, Controller
from odoo.exceptions import AccessError, ValidationError

from .token_utils import validate_token

_logger = logging.getLogger(__name__)

class SalesAPIController(Controller):

    def _prepare_response(self, statusOk, statusCode, message, payload, error):
        """
        Standardize API response with status codes
        """
        return request.make_response(
            json.dumps({
            "statusOk": statusOk,
            "statusCode": statusCode,
            "message": message,
            "payload": payload,
            "error": error
        }), 
            headers=[('Content-Type', 'application/json')],
            status=statusCode
        )
    
    def get_sync_domain(self, model):
        sync_record = request.env['sync.tracking'].sudo().search(
                [('model_name', '=', model)],
                limit=1
            )
        if sync_record and sync_record.last_sync_date:
            return ['|', ('create_date', '>', sync_record.last_sync_date), ('write_date', '>', sync_record.last_sync_date)]
        return []
    
    def update_last_sync_date(self, model):
        sync_record = request.env['sync.tracking'].sudo().search(
            [('model_name', '=', model)],
            limit=1
        )
        if sync_record:
            sync_record.sudo().write({'last_sync_date': fields.Datetime.now()})
        else:
            request.env['sync.tracking'].sudo().create({
                'model_name': model,
                'last_sync_date': fields.Datetime.now()
            })

    @http.route('/auth/login', type='http', auth='public', methods=['POST'], csrf=False)
    def authenticate(self):
        """
        Mobile/Web app authentication endpoint with status codes
        """
        try:
            # Parse JSON data
            params = json.loads(request.httprequest.data)
            username = params.get('username')
            password = params.get('password')

            # Validate input
            if not username or not password:
                return self._prepare_response(
                    False, 400, "", None, 'Missing username or password'
                )

            # Authenticate
            db = request.env.cr.dbname
            try:
                credential = {'login': username, 'password': f"{password}", 'type': 'password'}
                uid = request.session.authenticate(db, credential)
                if not uid:
                    return self._prepare_response(False, 401, "", None, 'Invalid Credentials')
                
                # Generate access token
                user = request.env['res.users'].sudo().browse(uid.get('uid'))
                token = request.env['mobile.api.token'].sudo().create_token(user)
                
                return self._prepare_response(
                    statusOk=True,
                    statusCode=200,
                    message='Authentication successful',
                    payload={
                        'token': token,
                        'user_id': user.id,
                        'name': user.name,
                        'email': user.email
                    },
                    error=None
                    )
            
            except Exception as e:
                return self._prepare_response(
                    False, 500, "", None, "Authentication failed"
                )
        
        except json.JSONDecodeError:
            return self._prepare_response(
                False, 400, "", None, "Invalid JSON")
        except Exception as e:
            return self._prepare_response(
                False, 500, "", None, str(e)
            )
        
    @http.route('/logout', type='http', auth='user', methods=['POST'], csrf=False)
    @validate_token
    def logout(self):
        """
        Logout endpoint to revoke tokens for the current user or a specific device.

        Args:
            device_identifier (str, optional): If provided, revokes tokens for a specific device.
        Returns:
            JSON: Logout response with success message or error.
        """
        try:
            # Parse request data (form-encoded or JSON)
            device_identifier = request.httprequest.form.get('device_identifier') or \
                                (json.loads(request.httprequest.data).get('device_identifier') if request.httprequest.data else None)

            # Current user
            token_payload = getattr(request, 'validated_token', {})
            user = token_payload

            auth_header = request.httprequest.headers.get('Authorization')
            token = None
            if auth_header and auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            # Revoke tokens for the current user or specific device
            token_model = request.env['mobile.api.token'].sudo()
            token_model.revoke_tokens(user=user, device_identifier=device_identifier, token=token)

            # Prepare response
            return self._prepare_response(True, 200, "Logout successful. Tokens revoked.", None, None)

        except AccessError:
            return self._prepare_response(False, 401, "Unauthorized access.", None, 'Access Denied')

        except Exception as e:
            return self._prepare_response(False, 500, "An error occurred during logout.", None, str(e))
        
    @http.route('/refresh_token', type='http', auth='public', methods=['POST'], csrf=False)
    def refresh_token(self):
        """
        Endpoint to refresh the JWT access token using the refresh token.
        """
        try:
            # Parse JSON data
            params = json.loads(request.httprequest.data)
            refresh_token = params.get('refresh_token')

            if not refresh_token:
                return self._prepare_response(False, 400, "", None, "Missing refresh token")

            # Refresh the token using the method defined in your model
            token_data = request.env['mobile.api.token'].sudo()._refresh_token(refresh_token)

            return self._prepare_response(
                statusOk=True,
                statusCode=200,
                message='Token refreshed successfully',
                payload=token_data,
                error=None
            )
        except Exception as e:
            return self._prepare_response(
                False, 500, "", None, str(e)
            )


    @http.route('/customers', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_customers(self):
        """
        Fetch customers with proper status codes
        """
        try:
            model = 'res.partner'
            domain = self.get_sync_domain(model)
            domain += [('customer_rank','>', 0)]
            
            customer_list = []
            customers = request.env[model].sudo().search(domain)
            user = getattr(request, 'validated_token', {})
            company = user.company_id
            global_days_limit = int(
                request.env['ir.config_parameter'].sudo().get_param(
                    'credit_management.days_limit', 
                    default=0
                )
            )  
            use_credit_limit = company.account_use_credit_limit
            ResPartner = request.env['res.partner'].sudo()
            global_credit_limit = (
                ResPartner._fields['credit_limit'].get_company_dependent_fallback(ResPartner)
                if use_credit_limit else 0.0
            )
            for customer in customers:
                # Determine Effective Days Limit (Customer-specific takes precedence)
                credit_limit_days = customer.days_limit or global_days_limit
                credit_limit_amount = (customer.credit_limit if customer.credit_limit  else global_credit_limit)
                credit = customer.credit
                child_list = []
                for record in customer.child_ids:
                    child_list.append({
                        'id': record.id,
                        'name': record.name,
                        'type': record.type,
                        'company_type': record.company_type,
                        'email': record.email if record.email else '',
                        'phone': record.phone if record.phone else '',
                        'mobile': record.mobile if record.mobile else '',
                        'vat': record.vat if record.vat else '',
                        'customer_code': record.customer_code if record.customer_code else '',
                        'latitude': record.latitude if record.latitude else '',
                        'longitude': record.longitude if record.longitude else '',
                        'cr_number': record.cr_number if record.cr_number else '',
                        'address': {
                            'street': record.street if record.street else '',
                            'street2': record.street2 if record.street2 else '',
                            'zip': record.zip if record.zip else '',
                            'city': record.city if record.city else '',
                            'state': record.state_id.name if record.state_id else '',
                            'state_id': record.state_id.id if record.state_id else None,
                            'country': record.country_id.name if record.country_id else '',
                            'country_id': record.country_id.id if record.country_id else None
                            }
                    })
                customer_list.append({
                    'id': customer.id,
                    'name': customer.name,
                    'company_type': customer.company_type,
                    'email': customer.email if customer.email else '',
                    'phone': customer.phone if customer.phone else '',
                    'mobile': customer.mobile if customer.mobile else '',
                    'vat': customer.vat if customer.vat else '',
                    'customer_code': customer.customer_code if customer.customer_code else '',
                    'latitude': customer.latitude if customer.latitude else '',
                    'longitude': customer.longitude if customer.longitude else '',
                    'cr_number': customer.cr_number if customer.cr_number else '',
                    'address': {
                        'street': customer.street if customer.street else '',
                        'street2': customer.street2 if customer.street2 else '',
                        'zip': customer.zip if customer.zip else '',
                        'city': customer.city if customer.city else '',
                        'state': customer.state_id.name if customer.state_id else '',
                        'state_id': customer.state_id.id if customer.state_id else None,
                        'country': customer.country_id.name if customer.country_id else '',
                        'country_id': customer.country_id.id if customer.country_id else None,
                    },
                    'credit': credit,
                    'credit_limit_amount': credit_limit_amount,
                    'credit_limit_days': credit_limit_days,
                    'child_ids': child_list
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(
                True, 200, "Successfully fetched customers", customer_list, None)
        
        except AccessError:
            return self._prepare_response(
                False, 403, "", None, "Access denied"
            )
        except Exception as e:
            return self._prepare_response(
                False, 500, "", None, str(e)
            )
        
    @http.route('/customer', type='http', auth='public', methods=['POST'], csrf=False)
    @validate_token
    def create_customer(self):
        try:
            # Parse JSON data
            datas = json.loads(request.httprequest.data)
            payload_data = []
            for data in datas:
                # Validate required fields
                name = data.get('name')
                mobile = data.get('mobile')
                company_type = data.get('company_type')
                django_id = data.get('django_id')
                customer_code = data.get('customer_code', None)
                cr_number = data.get('cr_number', None)
            
                if not name:
                    return self._prepare_response(
                        False, 400, "", None, "Missing name"
                    )
                
                if not mobile:
                    return self._prepare_response(
                        False, 400, "", None, "Missing mobile"
                    )
                
                if not company_type:
                    return self._prepare_response(
                        False, 400, "", None, "Missing company type"
                    )
            
                if company_type not in ['person', 'company']:
                    return self._prepare_response(
                        False, 400, "", None, "Company type should be either person or company"
                    )
                
                if not django_id:
                    return self._prepare_response(
                        False, 400, "", None, "Missing Django Customer ID"
                    )
            
                # Validate partner exists
                partner = request.env['res.partner'].sudo().search([('mobile', '=', mobile)]).exists()
                if partner:
                    return self._prepare_response(
                        False, 409, "", None, "A customer with this mobile already exists"
                    )
                
                partner = request.env['res.partner'].sudo().search([('customer_code', '=', customer_code)]).exists()
                if partner:
                    return self._prepare_response(
                        False, 409, "", None, "A customer with this code already exists"
                    )
                
                partner = request.env['res.partner'].sudo().search([('cr_number', '=', cr_number)]).exists()
                if partner:
                    return self._prepare_response(
                        False, 409, "", None, "A customer with this CR Number already exists"
                    )
                child_list = []
                for record in data.get('child_ids', []):
                    if not record.get('type'):
                        return self._prepare_response(
                            False, 400, "", None, "Missing Address Type"
                        )
                    if record.get('type') not in ['contact', 'invoice', 'delivery', 'other']:
                        return self._prepare_response(
                            False, 400, "", None, "Address Type should be either contact/ invoice/ delivery/ other"
                        )
                    child_list.append(
                        {
                            'name': record.get('name'),
                            'type': record.get('type'),
                            'phone': record.get('phone'),
                            'mobile': record.get('mobile'),
                            'email': record.get('email'),
                            'company_type': record.get('company_type'),
                            'customer_rank': 1,
                            'company_id': record.get('company_id'),
                            'street': record.get('street'),
                            'street2': record.get('street2'),
                            'zip': record.get('zip'),
                            'city': record.get('city'),
                            'country_id': record.get('country_id'),
                            'state_id': record.get('state_id'),
                            'vat': record.get('vat'),
                            'customer_code': record.get('customer_code', ''),
                            'latitude': record.get('latitude', ''),
                            'longitude': record.get('longitude', ''),
                            'cr_number': record.get('cr_number', '')
                        }
                    )
                values = {
                    'name': name,
                    'phone': data.get('phone'),
                    'mobile': mobile,
                    'email': data.get('email'),
                    'company_type': company_type,
                    'customer_rank': 1,
                    'company_id': data.get('company_id'),
                    'street': data.get('street'),
                    'street2': data.get('street2'),
                    'zip': data.get('zip'),
                    'city': data.get('city'),
                    'country_id': data.get('country_id'),
                    'state_id': data.get('state_id'),
                    'vat': data.get('vat'),
                    'child_ids': [(0, 0, child) for child in child_list],
                    'django_id': django_id,
                    'customer_code': data.get('customer_code', ''),
                    'latitude': data.get('latitude', ''),
                    'longitude': data.get('longitude', ''),
                    'cr_number': data.get('cr_number', '')
                }
                # Create customer
                customer = request.env['res.partner'].create(values)
                payload_data.append(
                    {
                        'customer_id': customer.id,
                        'name': customer.name,
                        'django_id': django_id
                    }
                    )
            
            return self._prepare_response(
                True, 201, "Customer created", payload_data, None
                )
        
        except ValidationError as ve:
            return self._prepare_response(
                False, 400, "Validation error", None, str(ve)
            )
        except AccessError:
            return self._prepare_response(
                False, 403, "", None, "Access denied"
            )
        except Exception as e:
            return self._prepare_response(
                False, 500, "", None, str(e)
            )


    @http.route('/products', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_products(self):
        try:
            model = 'product.template'
            domain = self.get_sync_domain(model)
            # Search products
            domain += [('sale_ok', '=', True)]
            base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")
            
            products = request.env[model].sudo().search(domain)
            product_list = []
            for product in products:
                stock_quants = request.env['stock.quant'].sudo().search([
                    ('product_id', '=', product.product_variant_id.id),
                    ('location_id.usage', '=', 'internal')
                ])
                lot_data = []
                for quant in stock_quants:
                    if quant.lot_id:
                        lot_data.append({
                            'id': quant.lot_id.id,
                            'name': quant.lot_id.name,
                            'expiry': quant.lot_id.expiration_date.strftime('%Y-%m-%d') if quant.lot_id.expiration_date else '',
                            'on_hand': quant.quantity,
                            'location_id':quant.location_id.id,
                            'location_name': quant.location_id.display_name
                        })
                product_list.append({
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code if product.default_code else '',
                    'type': product.type,
                    'invoice_policy': product.invoice_policy,
                    'is_storable': product.is_storable,
                    'list_price': product.list_price,
                    'standard_price': product.standard_price,
                    'taxes_id': product.taxes_id.ids,
                    'supplier_taxes_id': product.supplier_taxes_id.ids,
                    'categ_id': product.categ_id.id,
                    'image': f"{base_url}/web/image/product.template/{product.id}/image_1920" if product.id else '',
                    'tracking': product.tracking,
                    'lots': lot_data if lot_data else [],
                    'expense_policy': product.expense_policy,
                    'uom_po_id': product.uom_po_id.id if product.uom_po_id else None,
                    'purchase_method': product.purchase_method
                })
            # self.update_last_sync_date(model)

            return self._prepare_response(True, 200, "Products Fetched successfully", product_list, None)
        
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/product_variants', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_product_variants(self):
        try:
            model = 'product.product'
            domain = self.get_sync_domain(model)
            domain += [('sale_ok', '=', True)]
            
            products = request.env[model].sudo().search(domain)
            product_list = []
            base_url = request.env["ir.config_parameter"].sudo().get_param("web.base.url")
            for product in products:
                stock_quants = request.env['stock.quant'].sudo().search([
                    ('product_id', '=', product.id),
                    ('location_id.usage', '=', 'internal')
                ])
                lot_data = []
                for quant in stock_quants:
                    if quant.lot_id:
                        lot_data.append({
                            'id': quant.lot_id.id,
                            'name': quant.lot_id.name,
                            'expiry': quant.lot_id.expiration_date.strftime('%Y-%m-%d') if quant.lot_id.expiration_date else '',
                            'on_hand': quant.quantity,
                            'location_id':quant.location_id.id,
                            'location_name': quant.location_id.display_name
                        })
                product_list.append({
                    'id': product.id,
                    'name': product.name,
                    'default_code': product.default_code if product.default_code else '',
                    'barcode': product.barcode if product.barcode else '',
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'product_template_variant_value_ids': product.product_template_variant_value_ids.ids,
                    'type': product.type,
                    'invoice_policy': product.invoice_policy,
                    'is_storable': product.is_storable,
                    'list_price': product.list_price,
                    'standard_price': product.standard_price,
                    'taxes_id': product.taxes_id.ids,
                    'supplier_taxes_id': product.supplier_taxes_id.ids,
                    'categ_id': product.categ_id.id,
                    'image_128': product.image_128.decode("utf-8") if product.image_128 else '',
                    'image': f"{base_url}/web/image/product.product/{product.id}/image_1920" if product.id else '',
                    'tracking': product.tracking,
                    'lots': lot_data if lot_data else [],
                    'expense_policy': product.expense_policy,
                    'purchase_method': product.purchase_method
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "Product Variants Fetched successfully", product_list, None)
        
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/product_variant_attribute', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_product_variant_attribute(self):
        try:
            model = 'product.template.attribute.value'
            domain = self.get_sync_domain(model)            
            uoms = request.env[model].sudo().search_read(domain, ['name'])
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "Product Variant Attribute Fetched successfully", uoms, None)
        
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/product_category', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_product_category(self):
        try:
            model = 'product.category'
            domain = self.get_sync_domain(model)
            category_list = []
            product_categories = request.env[model].sudo().search(domain)
            for product_category in product_categories:
                category_list.append({
                    'id': product_category.id,
                    'name': product_category.name,
                    'parent_id': product_category.parent_id.id if product_category.parent_id else None,
                    'property_cost_method': product_category.property_cost_method,
                    'packaging_reserve_method': product_category.packaging_reserve_method
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "Product Category Fetched successfully", category_list, None)
        
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/product_batch', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_product_id_batch(self, **kwargs):
        try:
            model = 'stock.lot'
            domain = self.get_sync_domain(model)
            # domain += [('location_id.usage', '=', 'internal')]
            if kwargs.get('product_id') is not None:
                domain += [('product_id', '=', int(kwargs.get('product_id')))]
            batch_list = []
            product_batches = request.env[model].sudo().search(domain, order='expiration_date')
            for product_batch in product_batches:
                stock_quants = request.env['stock.quant'].sudo().search([
                    ('lot_id', '=', product_batch.id),
                    ('location_id.usage', '=', 'internal')
                ])
                quantity = []
                for quant in stock_quants:
                    if quant.lot_id:
                        quantity.append({
                            'on_hand': quant.quantity,
                            'available_quantity': quant.available_quantity,
                            'location_id':quant.location_id.id,
                            'location_name': quant.location_id.display_name
                        })
                batch_list.append({
                    'id': product_batch.id,
                    'name': product_batch.name,
                    'product_id': product_batch.product_id.id,
                    'cost': product_batch.avg_cost,
                    'available_qty': product_batch.product_qty,
                    'quantity': quantity,
                    'expiration_date': product_batch.expiration_date.strftime('%Y-%m-%d %H:%M:%S') if product_batch.expiration_date else '',
                    'removal_date': product_batch.removal_date.strftime('%Y-%m-%d %H:%M:%S') if product_batch.removal_date else '',
                    'use_date': product_batch.use_date.strftime('%Y-%m-%d %H:%M:%S') if product_batch.use_date else '',
                    'alert_date': product_batch.alert_date.strftime('%Y-%m-%d %H:%M:%S') if product_batch.alert_date else '',
                    
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "Product Batch Fetched successfully", batch_list, None)
        
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))

    @http.route('/sales_persons', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_sales_persons(self):
        try:
            model = 'res.users'
            domain = self.get_sync_domain(model)
            domain += [('groups_id', 'in', request.env.ref('sales_team.group_sale_salesman').id)]
            
            salesperson_list = []
            sales_persons = request.env[model].sudo().search(domain)
            for sales_person in sales_persons:
                admin = False
                if sales_person.has_group('base.group_system'):
                    admin = True
                salesperson_list.append({
                    'id': sales_person.id,
                    'name': sales_person.name,
                    'login': sales_person.login,
                    'company_id': sales_person.company_id.id if sales_person.company_id else None,
                    'phone': sales_person.phone if sales_person.phone else '', 
                    'mobile': sales_person.mobile if sales_person.mobile else '',
                    'email': sales_person.email if sales_person.email else '',
                    'admin': admin,
                    'address': {
                        'street': sales_person.street if sales_person.street else '',
                        'street2': sales_person.street2 if sales_person.street2 else '',
                        'zip': sales_person.zip if sales_person.zip else '',
                        'city': sales_person.city if sales_person.city else '',
                        'state': sales_person.state_id.name if sales_person.state_id else '',
                        'state_id': sales_person.state_id.id if sales_person.state_id else None,
                        'country': sales_person.country_id.name if sales_person.country_id else '',
                        'country_id': sales_person.country_id.id if sales_person.country_id else None
                        },
                    'allowed_company_ids': sales_person.company_ids.ids
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "Salespersons Fetched successfully", salesperson_list, None)

        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/sales_teams', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_sales_teams(self):
        try:
            model = 'crm.team'
            domain = self.get_sync_domain(model)
            # domain += [('groups_id', 'in', request.env.ref('sales_team.group_sale_salesman').id)]
            
            salesteam_list = []
            sales_teams = request.env[model].sudo().search(domain)
            for sales_team in sales_teams:
                salesteam_list.append({
                    'id': sales_team.id,
                    'name': sales_team.name,
                    'team_lead_id': sales_team.user_id.id if sales_team.user_id else None,
                    'team_lead': sales_team.user_id.name if sales_team.user_id else None,
                    'company_id': sales_team.company_id.id if sales_team.company_id else None,
                    'member_ids': sales_team.member_ids.ids, 
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "Salesteam Fetched successfully", salesteam_list, None)

        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/tax', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_tax(self):
        try:
            model = 'account.tax'
            domain = self.get_sync_domain(model)            
            tax_list = []
            taxes = request.env[model].sudo().search(domain)
            for tax in taxes:
                tax_list.append({
                    'id': tax.id,
                    'name': tax.name,
                    'active': tax.active,
                    'invoice_label': tax.invoice_label,
                    'company_id': tax.company_id.id if tax.company_id else None,
                    'company': tax.company_id.name if tax.company_id else None,
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "Tax Fetched successfully", tax_list, None)
        
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/uom_category', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_uom_category(self):
        try:
            model = 'uom.category'
            domain = self.get_sync_domain(model)            
            uoms = request.env[model].sudo().search_read(domain, ['name'])
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "UoM Category Fetched successfully", uoms, None)
        
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/uom', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_uom(self):
        try:
            model = 'uom.uom'
            domain = self.get_sync_domain(model)            
            uoms = request.env[model].sudo().search_read(domain, ['name'])
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "UoM Fetched successfully", uoms, None)
        
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))

    @http.route('/sale_order', type='http', auth='public', methods=['POST'], csrf=False)
    @validate_token
    def create_sale_order(self):
        """
        Create sale order with comprehensive validation and status codes
        """
        try:
            # Parse JSON data
            datas = json.loads(request.httprequest.data)
            user = getattr(request, 'validated_token', {})
            payload_data = []
            for data in datas:
                partner_id = data.get('customer_id')
                order_lines = data.get('order_lines', [])
                new_customer_vals = data.get('new_customer')
                django_sale_order_id = data.get('django_sale_order_id', None)
                django_quotation_id = data.get('django_quotation_id', None)
                sale_type = data.get('sale_type', None)
                
                if not partner_id and not new_customer_vals:
                    return self._prepare_response(
                        False, 400, "", None, "Missing partner_id"
                    )
                
                if not order_lines:
                    return self._prepare_response(
                        False, 400, "", None, "No order lines provided"
                    )
                
                if sale_type not in ['wholesale', 'b2b', 'vansale', None]:
                    return self._prepare_response(
                        False, 400, "", None, "Sale Type should be either wholesale/ b2b/ vansale"
                    )
                # Validate partner exists
                partner = request.env['res.partner'].sudo().browse(partner_id).exists()
                if not partner:
                    return self._prepare_response(
                        False, 404, "", None, "Invalid partner"
                    )
            
                if not django_sale_order_id:
                    return self._prepare_response(
                        False, 404, "", None, "Django Sale Order is missing"
                    )
                
                if not django_quotation_id and not django_sale_order_id:
                    return self._prepare_response(
                        False, 404, "", None, "Django Quotation is missing"
                    )
                
                if django_quotation_id:
                    sale_order = request.env['sale.order'].sudo().search([('django_quotation_id', '=', django_quotation_id)])
                    if sale_order:
                        sale_order.django_id = django_sale_order_id
                        sale_order.order_line.unlink()
                        sale_order_lines = []
                        for line in order_lines:
                            product_id = line.get('product_id')
                            quantity = line.get('product_uom_qty', 1)
                            price_unit = line.get('price_unit')
                            
                            # Validate product
                            product = request.env['product.product'].sudo().browse(product_id).exists()
                            if not product:
                                return self._prepare_response(
                                    False, 404, "", None, f'Invalid product ID: {product_id}'
                                )
                            
                            if not line.get('django_sale_line_id'):
                                return self._prepare_response(
                                    False, 404, "", None, "Django Sale line is missing"
                                )
                            line_vals = {
                                'product_id': product_id,
                                'product_uom_qty': quantity,
                                'price_unit': price_unit or product.list_price,
                                'name': product.name,
                                'tax_id': [(6, 0, line.get('tax_id'), [])],
                                'discount': line.get('discount', 0),
                                'product_uom': line.get('uom_id') if line.get('uom_id') else product.uom_id.id,
                                'purchase_price': line.get('purchase_price'),
                                'django_sale_line_id': line.get('django_sale_line_id', None),
                                'lot_id': line.get('lot_id'),
                            }
                            sale_order_lines.append((0, 0, line_vals))
                        sale_order.sudo().write({'order_line': sale_order_lines})
                        sale_order.sudo().action_confirm()
                else:
                    # Prepare sale order
                    user = getattr(request, 'validated_token', {})
                    sale_order_vals = {
                        'partner_id': partner_id,
                        'company_id': data.get('company_id', None),
                        'user_id': data.get('user_id', user.id),
                        'client_order_ref': data.get('customer_reference', ''),
                        'state': 'draft',
                        'order_line': [],
                        'django_id': django_sale_order_id,
                        "sale_type": sale_type,
                        "user_id": user.id
                    }

                    # Validate and prepare order lines
                    for line in order_lines:
                        product_id = line.get('product_id')
                        quantity = line.get('product_uom_qty', 1)
                        price_unit = line.get('price_unit')
                        
                        # Validate product
                        product = request.env['product.product'].sudo().browse(product_id).exists()
                        if not product:
                            return self._prepare_response(
                                False, 404, "", None, f'Invalid product ID: {product_id}'
                            )
                        
                        tax_ids = line.get('tax_id', []) or product.taxes_id.ids
                        
                        if not line.get('django_sale_line_id'):
                            return self._prepare_response(
                                False, 404, "", None, "Django Sale line is missing"
                            )
                        sale_order_vals['order_line'].append((0, 0, {
                            'product_id': product_id,
                            'product_uom_qty': quantity,
                            'price_unit': price_unit or product.list_price,
                            'name': product.name,
                            'tax_id': [(6, 0, tax_ids)],
                            'discount': line.get('discount', 0),
                            'product_uom': line.get('uom_id') if line.get('uom_id') else product.uom_id.id,
                            'purchase_price': line.get('purchase_price') or product.standard_price,
                            'django_sale_line_id': line.get('django_sale_line_id', None),
                            'lot_id': line.get('lot_id', None),
                        }))
                    
                    # Create Sale Order
                    sale_order = request.env['sale.order'].sudo().create(sale_order_vals)
                    sale_order.sudo().action_confirm()
                payload_data.append({
                    'order_id': sale_order.id,
                    'django_sale_order_id': django_sale_order_id,
                    'order_name': sale_order.name
                    })
                
            return self._prepare_response(
                True, 201, "Sale order created", payload_data, None
                )
        
        except ValidationError as ve:
            return self._prepare_response(
                False, 400, "Validation error", None, str(ve)
            )
        except AccessError:
            return self._prepare_response(
                False, 403, "", None, "Access denied"
            )
        except Exception as e:
            return self._prepare_response(
                False, 500, "", None, str(e)
            )
        
    @http.route('/quotation', type='http', auth='public', methods=['POST'], csrf=False)
    @validate_token
    def create_quotation(self):
        try:
            # Parse JSON data
            datas = json.loads(request.httprequest.data)
            user = getattr(request, 'validated_token', {})
            payload_data = []
            sale_order_vals_list = []
            with request.env.cr.savepoint():  # Start a transaction savepoint
                for data in datas:
                    # Validate required fields
                    partner_id = data.get('customer_id')
                    order_lines = data.get('order_lines', [])
                    new_customer_vals = data.get('new_customer')
                    django_quotation_id = data.get('django_quotation_id', None)
                    sale_type = data.get('sale_type', None)
                    
                    if not partner_id and not new_customer_vals:
                        return self._prepare_response(
                            False, 400, "", None, "Missing partner_id"
                        )
                    
                    if not order_lines:
                        return self._prepare_response(
                            False, 400, "", None, "No order lines provided"
                        )
                    
                    if sale_type not in ['wholesale', 'b2b', 'vansale', None]:
                        return self._prepare_response(
                            False, 400, "", None, "Sale Type should be either wholesale/ b2b/ vansale"
                        )
                    # Validate partner exists
                    partner = request.env['res.partner'].sudo().browse(partner_id).exists()
                    if not partner:
                        return self._prepare_response(
                            False, 404, "", None, "Invalid partner"
                        )
                
                    if not django_quotation_id:
                        return self._prepare_response(
                            False, 404, "", None, "Django Quotation is missing"
                        )
                
                    if new_customer_vals:
                        # Create new customer
                        new_customer_val = {
                            'name': new_customer_vals.get('name'),
                            'phone': new_customer_vals.get('phone'),
                            'mobile': new_customer_vals.get('mobile'),
                            'email': new_customer_vals.get('email'),
                            'company_type': new_customer_vals.get('company_type'),
                            'customer_rank': 1,
                            'company_id': new_customer_vals.get('company_id'),
                            'street': new_customer_vals.get('street'),
                            'street2': new_customer_vals.get('street2'),
                            'zip': new_customer_vals.get('zip'),
                            'city': new_customer_vals.get('city'),
                            'country_id': new_customer_vals.get('country_id'),
                            'state_id': new_customer_vals.get('state_id')
                        }
                        partner_id = request.env['res.partner'].create(new_customer_val).id     
                    # Prepare sale order
                    user = getattr(request, 'validated_token', {})
                    sale_order_vals = {
                        'partner_id': partner_id,
                        'company_id': data.get('company_id', None),
                        'user_id': data.get('user_id', user.id),
                        'client_order_ref': data.get('customer_reference', ''),
                        'state': 'draft',
                        'order_line': [],
                        'django_quotation_id': django_quotation_id,
                        "sale_type": sale_type,
                        'user_id': user.id,
                        'delivery_priority_id': data.get('delivery_priority_id', False),
                        'delivery_description': data.get('delivery_description', '')
                    }
                
                    # Validate and prepare order lines
                    for line in order_lines:
                        product_id = line.get('product_id')
                        quantity = line.get('product_uom_qty', 1)
                        price_unit = line.get('price_unit')
                        
                        # Validate product
                        product = request.env['product.product'].sudo().browse(product_id).exists()
                        if not product:
                            return self._prepare_response(
                                False, 404, "", None, f'Invalid product ID: {product_id}'
                            )
                        tax_ids = line.get('tax_id', []) or product.taxes_id.ids
                        
                        if not line.get('django_quotation_line_id'):
                            return self._prepare_response(
                                False, 404, "", None, "Django Quotation line is missing"
                            )
                        sale_order_vals['order_line'].append((0, 0, {
                            'product_id': product_id,
                            'product_uom_qty': quantity,
                            'price_unit': price_unit or product.list_price,
                            'name': product.name,
                            'tax_id': [(6, 0, tax_ids)],
                            'discount': line.get('discount', 0),
                            'product_uom': line.get('uom_id') if line.get('uom_id') else product.uom_id.id,
                            'django_quotation_line_id': line.get('django_quotation_line_id', None),
                            'purchase_price': line.get('purchase_price') or product.standard_price,
                            'lot_id': line.get('lot_id'),
                        }))
                    # Append Sale Order Values
                    sale_order_vals_list.append(sale_order_vals)
                
                # Create Quotation
                sale_orders = request.env['sale.order'].sudo().create(sale_order_vals_list)
                for sale_order in sale_orders:
                    payload_data.append({
                        'order_id': sale_order.id,
                        'django_quotation_id': sale_order.django_quotation_id,
                        'order_name': sale_order.name
                        })
                    
            return self._prepare_response(
                True, 201, "Quotation created", payload_data, None
                )
        
        except ValidationError as ve:
            request.env.cr.rollback()  # Rollback transaction
            return self._prepare_response(
                False, 400, "Validation error", None, str(ve)
            )
        except AccessError:
            request.env.cr.rollback()  # Rollback transaction
            return self._prepare_response(
                False, 403, "", None, "Access denied"
            )
        except Exception as e:
            request.env.cr.rollback()  # Rollback transaction
            return self._prepare_response(
                False, 500, "", None, str(e)
            )
        
    @http.route('/sales_history', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_sales_history(self, **kwargs):
        try:
            sale_domain = [('state', '=', 'sale'), ('invoice_status', 'in', ['invoiced'])]
            if kwargs.get('product_id'):
                sale_domain += [('product_id', '=', int(kwargs.get('product_id')))]
            if kwargs.get('customer_id'):
                sale_domain += [('order_partner_id', '=', int(kwargs.get('customer_id')))]
            sale_lines = request.env['sale.order.line'].sudo().search(sale_domain, order='create_date DESC, order_id')
            sale_history = []
            for line in sale_lines:
                sale_history.append({
                    'id': line.id,
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'quantity': line.product_uom_qty,
                    'delivered': line.qty_delivered,
                    'billed': line.qty_invoiced,
                    'price_unit': line.price_unit,
                    'date_order': line.order_id.date_order.strftime('%Y-%m-%d %H:%M:%S'),
                    'customer_id': line.order_id.partner_id.id,
                    'customer': line.order_id.partner_id.name,
                    'order_id': line.order_id.id,
                    'order': line.order_id.name,
                    'total_price' : line.price_subtotal,
                    'user_id': line.order_id.user_id.id,
                    'user': line.order_id.user_id.name
                })               
            return self._prepare_response(True, 200, "Sales History fetched Successfully", sale_history, None)
        
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/purchase_history', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_purchase_history(self, **kwargs):
        try:
            purchase_domain = [('state', 'in', ['purchase', 'done'])]
            if kwargs.get('product_id'):
                purchase_domain += [('product_id', '=', int(kwargs.get('product_id')))]
            if kwargs.get('vendor_id'):
                purchase_domain += [('partner_id', '=', int(kwargs.get('vendor_id')))]
            purchase_lines = request.env['purchase.order.line'].sudo().search(purchase_domain, order='create_date DESC, order_id')
            purchase_history = []
            for line in purchase_lines:
                purchase_history.append({
                    'id': line.id,
                    'product_id': line.product_id.id,
                    'product_name': line.product_id.name,
                    'quantity': line.product_uom_qty,
                    'received': line.qty_received,
                    'billed': line.qty_invoiced,
                    'price_unit': line.price_unit,
                    'date_order': line.order_id.date_order.strftime('%Y-%m-%d %H:%M:%S'),
                    'vendor_id': line.order_id.partner_id.id,
                    'vendor': line.order_id.partner_id.name,
                    'order_id': line.order_id.id,
                    'order': line.order_id.name,
                    'total_price' : line.price_subtotal,
                    'user_id': line.order_id.user_id.id,
                    'user': line.order_id.user_id.name
                })        
            return self._prepare_response(True, 200, "Purchase History fetched Successfully", purchase_history, None)
        
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/invoice', type='http', auth='public', methods=['POST'], csrf=False)
    @validate_token
    def create_invoice(self):
        try:
            datas = json.loads(request.httprequest.data)
            payload_data = []
            for data in datas:
                sale_order = request.env['sale.order'].sudo().search([('django_id', '=', int(data.get('django_sale_order_id')))])
                if not sale_order:
                    return self._prepare_response(False, 404, "Sale Order not found", None, None)
                sale_order._create_invoices()
                for invoice in sale_order.invoice_ids:
                    invoice.django_id = data.get('django_invoice_id', None)
                    invoice.action_post()
                payload_data.append({
                    'order_id': sale_order.id,
                    'django_sale_order_id': sale_order.django_id,
                    'django_invoice_id': invoice.django_id,
                    'invoice_id': invoice.id,
                    'invoice_number': invoice.name,
                    'invoice_date': invoice.invoice_date.strftime('%Y-%m-%d')
                })
            return self._prepare_response(
                True, 201, "Invoice created", payload_data, None
                )
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/reset_password', type='http', auth='none', methods=['POST'], csrf=False)
    def reset_password(self):
        try:
            data = json.loads(request.httprequest.data)
            username = data.get('username', None)
            password = data.get('password', None)
            if not username:
                return self._prepare_response(False, 400, "Username is required", None, None)
            if not password:
                return self._prepare_response(False, 400, "Password is required", None, None)
            user = request.env['res.users'].sudo().search([('login', '=', username)], limit=1)
            if not user:
                return self._prepare_response(False, 404, "User not found", None, None)
            mail_values = {
                'subject': 'Password Changed',
                'body_html': f'''
                    <p>Dear {user.name},</p>
                    <p>Your password has been reset successfully. If you did not request this change, please contact support immediately.</p>
                ''',
                'email_to': user.email,
                'email_from': 'cvshayar@gmail.com',
            }
            mail = request.env['mail.mail'].sudo().create(mail_values)
            mail.sudo().send()
            user.sudo()._change_password(password)
            return self._prepare_response(
                True, 201, "Password Reset Successfull", None, None
                )
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e)) 

        
    @http.route('/sales_return', type='http', auth='public', methods=['POST'], csrf=False)
    @validate_token
    def create_sales_return(self):
        try:
            datas = json.loads(request.httprequest.data)
            user = getattr(request, 'validated_token', {})
            payload_data = []
            for data in datas:
                sale_order = request.env['sale.order'].sudo().search([('django_id', '=', int(data.get('django_sale_order_id')))])
                if not sale_order:
                    return self._prepare_response(False, 404, "Sale Order not found", None, None)
                sale_return = sale_order.create_return()
                return_lines = data.get('return_lines', [])   
                django_return_sale_line_ids = [line['django_sale_line_id'] for line in return_lines] # Getting the django sale line
                return_sale_line_ids = sale_order.order_line.filtered(lambda x: x.django_sale_line_id in django_return_sale_line_ids).mapped('id') # Getting Corresponding Sale Order Line
                
                for return_line in return_lines:
                    if not return_line.get('django_sale_line_id', None):
                        return self._prepare_response(
                            False, 404, "", None, "Django Sale line is missing"
                        )
                
                sales_return = request.env['sale.return'].sudo().browse([sale_return.get('res_id')])           
                if sales_return:
                    sales_return.user_id = user.id
                    for return_line in sales_return.return_line_ids:
                        if return_line.sale_order_line_id.id not in return_sale_line_ids:
                            return_line.unlink()
                            continue
                        passed_return_line = next((line for line in return_lines if line['django_sale_line_id'] == return_line.sale_order_line_id.django_sale_line_id), None)
                        return_line.quantity = passed_return_line.get('quantity')  
                    sales_return.request_approval()                  
                    payload_data.append({
                        'return_id': sales_return.id,
                        'order_id': sale_order.id,
                        'django_sale_order_id': sale_order.django_id,
                    })
            return self._prepare_response(
                True, 201, "Sales Return created", payload_data, None
                )
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e)) 
        
    @http.route('/country', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_country(self):
        try:
            model = 'res.country'
            domain = self.get_sync_domain(model)
            
            country_list = []
            countries = request.env[model].sudo().search(domain)
            for country in countries:
                country_list.append({
                    'id': country.id,
                    'name': country.name,
                    'code': country.code,
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "Country Fetched successfully", country_list, None)

        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @http.route('/country_state', type='http', auth='public', methods=['GET'])
    @validate_token
    def get_country_state(self):
        try:
            model = 'res.country.state'
            domain = self.get_sync_domain(model)
            
            state_list = []
            states = request.env[model].sudo().search(domain)
            for state in states:
                state_list.append({
                    'id': state.id,
                    'name': state.name,
                    'code': state.code,
                    'country_id': state.country_id.id,
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, "States Fetched successfully", state_list, None)

        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @validate_token
    @http.route('/einvoice_status/<invoice_id>', type='http', auth='public', methods=['GET'], csrf=False)
    def einvoice_status(self, invoice_id, **kwargs):
        try:
            if not invoice_id:
                return self._prepare_response(False, 400, None, None, "Invoice ID not passed.")
            if not isinstance(invoice_id, int):
                invoice_id = int(invoice_id)
            invoice = request.env['account.move'].sudo().search([('django_id', '=', invoice_id)])
            if not invoice:
                return self._prepare_response(False, 400, None, None, f"Invoice with ID {invoice_id} does not exist.")
            if invoice.edi_state == 'to_sent':
                payload_data = [{
                    "status": "pending",
                    "value": "Pending"
                }]
                return self._prepare_response(True, 200, None, payload_data, None)
            elif invoice.edi_state == "to_cancel":
                payload_data = [{
                    "status": "to_cancel",
                    "value": "To Cancel"
                }]
                return self._prepare_response(True, 200, None, payload_data, None)
            elif invoice.edi_state == "cancelled":
                payload_data = [{
                    "status": "cancelled",
                    "value": "Cancelled"
                }]
                return self._prepare_response(True, 200, None, payload_data, None)
            elif invoice.edi_state == "sent":
                if invoice.edi_error_count > 0:
                    payload_data = [{
                        "status": "reject",
                        "value": "Reject"
                    }]
                    return self._prepare_response(True, 200, None, payload_data, None)
                else:
                    payload_data = [{
                        "status": "completed",
                        "value": "Completed"
                    }]
                    return self._prepare_response(True, 200, None, payload_data, None)
            else:
                payload_data = [{
                    "status": "unavailable",
                    "value": "Not Available"
                }]
                return self._prepare_response(True, 200, None, payload_data, None)
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))

    @validate_token
    @http.route('/companies', type='http', auth='public', methods=['GET'], csrf=False)
    def get_branches(self):
        try:
            model = 'res.company'
            domain = self.get_sync_domain(model)
            payload_data = []
            companies = request.env[model].sudo().search(domain, order='id')
            for company in companies:
                payload_data.append({
                    'id': company.id,
                    'name': company.name,
                    'parent_id': company.parent_id.id,
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, None, payload_data, None)
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
        
    @validate_token
    @http.route('/delivery_priority', type='http', auth='public', methods=['GET'], csrf=False)
    def get_delivery_priority(self):
        try:
            model = 'delivery.priority'
            domain = self.get_sync_domain(model)
            payload_data = []
            priorities = request.env[model].sudo().search(domain)
            for priority in priorities:
                payload_data.append({
                    'id': priority.id,
                    'name': priority.name,
                })
            # self.update_last_sync_date(model)
            return self._prepare_response(True, 200, None, payload_data, None)
        except AccessError:
            return self._prepare_response(False, 403, None, None, "Access denied")
        except Exception as e:
            return self._prepare_response(False, 500, None, None, str(e))
