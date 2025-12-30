# -*- coding: utf-8 -*-

{
    'name': "Previous History Of Products",
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': """Sales And Purchase history of products from Sales Order Lines.""",
    'description': """This module enable the users to view the Sales and Purchase history of
    the products from the Sale Order Lines.""",
    'author': "Zinfog Codelabs Pvt Ltd",
    'company': "Zinfog Codelabs Pvt Ltd",
    'website': "https://zinfog.com/",
    'depends': ['sale_management'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_sale_order_history_wizard_views.xml',
        'views/sale_order_views.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False
}
