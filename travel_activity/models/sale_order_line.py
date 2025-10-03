from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    travel_type = fields.Selection(selection_add=[("activity", "Activity")])
