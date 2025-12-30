# -*- coding: utf-8 -*-
###################################################################################

# Author       :  Varsha PN
# Copyright(c) :  2023-Present Zinfog Codelabs Pvt Ltd (<https://www.zinfog.com>).
# License      :  LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

# This program is free software:
# you can modify it under the terms of the GNU Lesser General Public License (LGPL) as
# published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

###################################################################################

{
    "name": "ZCL CUSTOM REPORT",
    "summary": """ZCL REPORT""",
    "category": "Zinfog",
    "version": "18.0.1.0.0",
    "author": "Zinfog Codelabs Pvt Ltd",
    "license": "LGPL-3",
    "website": "https://www.zinfog.com",
    "description": """ ZCL REPORT""",
    "depends": ['base','account',],
    "data": [
        'security/ir.model.access.csv',
        'data/account_financial_report_data.xml',
        'wizard/partner_ledger.xml',
        'reports/report.xml',
        'reports/report_partner_ledger_with_background.xml',

    ],
    "application": True,
    "installable": True,
    "auto_install": False,


}
