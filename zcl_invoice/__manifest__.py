# -*- coding: utf-8 -*-
{
    'name': "zcl_invoice/",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
Long description of module's purpose
    """,

    'author': "My Company",
    'website': "https://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','account','zcl_inventory','web','l10n_sa', 'om_account_accountant','om_account_followup','l10n_gcc_invoice'],

    # always loaded
    'data': [
        # 'data/sequence.xml',
        'data/date_format_update.xml',
        'wizard/sale_purchase_register_wizard_view.xml',
        'views/account_move_inherit.xml',
        'views/account_move.xml',
        'views/menu.xml',
        'views/menu_hide.xml',
        'views/res_partner_inherit.xml',
        'views/account_payment_views.xml',
        'views/account_journal_inherit.xml',
        'views/account_payment_reconcile_view.xml',
        'security/ir.model.access.csv',
        # 'views/views.xml',
        # 'views/templates.xml',
        'reports/report_paper_format.xml',
        'reports/customer_invoice_pdf_template.xml',
        'reports/invoice_template_with_header.xml',
        'reports/customer_over_due_pdf_template.xml',
        'reports/sale_purchase_register_pdf_template.xml',
        'reports/account_payment_template.xml',

        'reports/report.xml',

    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

