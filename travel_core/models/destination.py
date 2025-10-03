import datetime as dt

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class Destination(models.Model):
    _name = "travel_core.destination"
    _description = "Travel Destination"

    code = fields.Char("Code")
    name = fields.Char("Name", required=True)
    description = fields.Text("Description")
    parent_id = fields.Many2one("travel_core.destination", "Parent")
    child_ids = fields.One2many("travel_core.destination", "parent_id", "Children")


class destination_distance(models.Model):
    _name = "travel_core.destination.distance"
    _description = "Destination distance"

    origin = fields.Many2one("travel_core.destination", "Origin")
    target = fields.Many2one("travel_core.destination", "Target")
    distance = fields.Float("Distance")
