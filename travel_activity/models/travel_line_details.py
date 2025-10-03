from odoo import _, api, fields, models


class TravelLineDetails(models.Model):
    _inherit = "travel.line.details"

    travel_type = fields.Selection(selection_add=[("activity", "Actvity")])
