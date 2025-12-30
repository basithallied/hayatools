# -*- coding: utf-8 -*-
{
    'name': 'Cash Book, Bank Book Financial Reports',
    'version': '1.0.1',
    'category': 'Invoicing Management',
    'summary': 'Cash Book And Bank Book Report For Odoo 18',
    'description': 'Cash Book And Bank Book Report For Odoo 18',
    'author': 'Zinfog Codelabs Pvt Ltd',
    'license': 'LGPL-3',
    'company': 'Zinfog Codelabs Pvt Ltd',
    'maintainer': 'Zinfog Codelabs Pvt Ltd',
    'depends': ['account','zcl_invoice','om_account_daily_reports'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/cash_book_view.xml',
        'reports/cash_book_template.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,

}
