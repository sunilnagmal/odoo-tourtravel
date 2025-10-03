# pylint: disable=pointless-statement
{
    "name": "Travel Agency - Visa",
    "version": "16.0.1.0.0",
    "author": "OpenJAF, Business Solutions For Africa",
    "maintainer": "Vincent LUBA",
    "website": "https://www.biz-4-africa.com/odoo-travel",
    "category": "Sales",
    "description": ("Travel Agency - Visa"),
    "depends": ["travel_core"],
    "data": [
        "data/categories.xml",
        "data/attributes.xml",
        "data/demo_data.xml",
        "views/product_template.xml",
        "views/sale_order_line.xml",
        "views/travel_line_details.xml",
        "report/sale_report.xml",
    ],
    "demo": [],
    "application": False,
    "installable": True,
    "license": "OPL-1",
}
