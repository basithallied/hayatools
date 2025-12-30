{
    'name': 'ZCL Financial Report Access',
    'version': '1.0',
    'category': 'Extra Tools',
    'summary': 'Restrict access to Balance Sheet and Profit and Loss reports based on user settings.',
    'depends': ['base', 'account', 'accounting_pdf_reports'],
    'data': [
        'security/security_groups.xml',
        'views/res_users_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
