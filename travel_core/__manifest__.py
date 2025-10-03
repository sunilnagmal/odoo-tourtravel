{
    "name": "Travel Agency - Core",
    "version": "16.0.1.0.0",
    "author": "OpenJAF, Business Solutions For Africa",
    "maintainer": "Vincent LUBA",
    "website": "https://www.biz-4-africa.com/odoo-travel",
    "category": "Sales",
    "description": """

Base module for managing sales, prices and accounting in a Travel Agency
========================================================================

    """,
    "depends": ["sale", "purchase", "account", "product", "mail", "sale_project"],
    "data": [
        "data/pricelist.xml",
        "data/attributes.xml",
        "data/product.xml",
        "views/menu.xml",
        "views/base.xml",
        "views/pricelist.xml",
        "views/sale.xml",
        "views/product_template.xml",
        "views/account_move.xml",
        "views/attributes.xml",
        "views/destination.xml",
        "views/airline.xml",
        "views/sale_order_line.xml",
        "views/travel_line_details.xml",
        "wizard/imports.xml",
        "wizard/pricelist.xml",
        "report/default_voucher.xml",
        "report/sale_report_view.xml",
        "security/travel_security.xml",
        "security/ir.model.access.csv",
    ],
    "demo": [],
    "application": False,
    "installable": True,
    "license": "OPL-1",
}
