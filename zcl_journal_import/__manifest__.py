{
    'name': 'ZCL Journal Import',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Import Journal Entries from Excel',
    'description': """
        This module allows users to import journal entries from an Excel file.
        Each row in the Excel file creates one Journal Entry.
        The module automatically creates a balancing line (Contra Line) 
        based on the provided Contra Account and Partner.
    """,
    'author': 'Hayatools',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/journal_import_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
