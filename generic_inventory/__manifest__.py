{
    'name' : 'Generic Inventory',
    'version' : '18.0.1.0',
    'summary' : 'Inventory Generic Customisation',
    'author': 'CODE-OX',
    'website': 'https://code-ox.com/',
    'icon': '/static/description/icon.png',
    'license' : 'LGPL-3',
    'depends': [
        'stock', 'purchase', 'account'
    ],
    'data':[
        'security/security.xml',
        'views/account_move.xml',
        'views/stock_location.xml',
        'views/product_product.xml'
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}  
