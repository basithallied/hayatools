# -*- coding: utf-8 -*-
###################################################################################

# Author       :  Sayooj t k
# Copyright(c) :  2023-Present Zinfog Codelabs Pvt Ltd (<https://www.zinfog.com>).
# License      :  LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

# This program is free software:
# you can modify it under the terms of the GNU Lesser General Public License (LGPL) as
# published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

###################################################################################

{
    "name": "Credit note with delivery return",
    "summary": """ Credit note with delivery return """,
    "category": "Zinfog",
    "version": "18.0.1.0.0",
    "author": "Zinfog Codelabs Pvt Ltd",
    "license": "LGPL-3",
    "website": "https://www.zinfog.com",
    "description": """ Credit note with delivery return """,
    "depends": ['base', 'account', 'stock', 'om_account_asset','stock_account', 'zcl_product_wise_auto_lot', 'sale'],
    "data": ["views/account_move_inherit.xml"],
    "application": False,
    "installable": True,
    "auto_install": False,
}
