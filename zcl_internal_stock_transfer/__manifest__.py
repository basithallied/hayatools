{
    'name': 'ZCL Internal Stock Transfer',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Internal stock movement between branches with transit stage.',
    'depends': ['stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/res_config_settings_views.xml',
        'views/internal_stock_transfer_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
