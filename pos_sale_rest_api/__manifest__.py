
{
    "name": "POS Sale REST API",
    "summary": "POS Sale REST API",
    "version": "18.0.1.1.1",
    "category": "",
    "website": "https://code-ox.com/",
    "author": "Code-Ox Technologies",
    "license": "AGPL-3",
    "depends": ["base", "sale", "credit_approval","stock"],
    "data": [
        "security/ir.model.access.csv",
        "views/sale_order.xml",
        "views/stock_picking.xml"
    ],
    "installable": True,
}
