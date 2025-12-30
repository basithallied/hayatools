# -*- coding: utf-8 -*-
###################################################################################

# Author       :  Sayooj T k
# Copyright(c) :  2023-Present Zinfog Codelabs Pvt Ltd (<https://www.zinfog.com>).
# License      :  LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

# This program is free software:
# you can modify it under the terms of the GNU Lesser General Public License (LGPL) as
# published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

###################################################################################

{
    "name": "Chart of Account Grouping",
    "summary": """Zcl Chart of Account Grouping""",
    "category": "Account",
    'version': '0.1',
    "author": "Zinfog Codelabs Pvt Ltd",
    "license": "LGPL-3",
    "website": "https://www.zinfog.com",
    "description": """ Zcl Chart of Account Grouping """,
    "depends": ['base','account'],
    "data": [
        'security/ir.model.access.csv',
        'views/account_account_inh.xml',
        'views/account_sub_group.xml',
        'views/account_move_line_inh.xml',
    ],
    "application": True,
    "installable": True,
    "auto_install": False,


}