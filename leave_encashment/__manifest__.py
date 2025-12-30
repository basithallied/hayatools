{
    'name' : 'Custom Leave Encashment',
    'version' : '18.0.1.0',
    'summary' : 'Adds leave encashment functionality',
    "author": "CODE-OX",
    "website": "https://code-ox.com/",
    'license' : 'LGPL-3',
    'depends': ['om_hr_payroll_account', 'hr', 'hr_holidays'],
    'data':[
          'security/ir.model.access.csv',
          'views/leave_encashment_views.xml',
          'views/menu_items.xml',
    ],
}