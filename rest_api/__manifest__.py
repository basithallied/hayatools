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
    "name": "Rest API",
    "summary": """ Restful API""",
    "category": "Zinfog",
    "version": "18.0.1.0.0",
    "author": "Zinfog Codelabs Pvt Ltd",
    "license": "LGPL-3",
    "website": "https://www.zinfog.com",
    "description": """ Restful API""",
    "depends": ['base','sale', 'stock'],
    "data": ["security/ir.model.access.csv",
             "views/rest_menu.xml",
             "views/rest_token_view.xml"],
    "application": False,
    "installable": True,
    "auto_install": False,
}
