{
    'name' : 'Sales Generic Customisation',
    'version' : '18.0.1.0',
    'summary' : 'Additional field to separate wholesale,b2b and vansale',
    "author": "CODE-OX",
    "website": "https://code-ox.com/",
    'license' : 'LGPL-3',
    'depends': ['sale', 'stock','sales_team', 'sale_order_lot_selection'],
    'data':[    
            'security/ir.model.access.csv',
            'views/sale_order_view.xml',
            'wizard/sale_order_discount.xml',
    ],
}