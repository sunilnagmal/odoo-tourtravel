from odoo import _, api, fields, models

class Pax(models.Model):
    _name = "travel_core.pax"
    _description = "Person registered on reservation"

    name = fields.Char("Name")
    reservation_number = fields.Char(string="Reservation_number")

    order_id = fields.Many2one(
        string="Sale Order",
        comodel_name="sale.order",
        ondelete="set null",
    )

    order_line_id = fields.Many2one(
        string="Order line",
        comodel_name="sale.order.line",
        domain="[('order_id', '=', order_id)]",
        ondelete="set null",
    )
