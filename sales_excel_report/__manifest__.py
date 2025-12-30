{
    "name": "Sale Excel Report",
    "summary": """sales Excel Report.""",
    "author": "CODE-OX",
    "website": "https://code-ox.com/",
    "license": "LGPL-3",
    "category": "Sales",
    "version": "18.0.0.0",
    "depends": ['base', 'sale', 'sales_team', 'web', 'report_xlsx', 'stock'],
    "data": [
        'wizard/sales_excel_wizard_view.xml',
        'reports/sales_report.xml',
        'security/ir.model.access.csv'

    ],
}
