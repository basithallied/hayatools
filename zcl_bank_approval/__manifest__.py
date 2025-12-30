{
    'name': 'ZCL Bank Journal Approval',
    'version': '1.0',
    'category': 'Accounting',
    'summary': 'Add an approval workflow for bank journal transactions.',
    'depends': ['account'],
    'data': [
        'security/security.xml',
        'views/account_move_views.xml',
        'views/account_payment_views.xml',
        'views/res_users_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
