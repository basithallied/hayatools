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
    "name": "Van Sale",
    "summary": """ZCL Van Sale""",
    "category": "Zinfog",
    'version': '0.1',
    "author": "Zinfog Codelabs Pvt Ltd",
    "license": "LGPL-3",
    "website": "https://www.zinfog.com",
    "description": """ ZCL Van Sale : For sale person 
                        wise van sale """,
    "depends": ['base','stock', 'zcl_inventory'],
    "data": [
        # 'security/ir.model.access.csv',
        'views/res_user_inh.xml',
        'views/stock_picking.xml',

    ],
    "application": True,
    "installable": True,
    "auto_install": False,


}