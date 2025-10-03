import json
from xml.etree import ElementTree as ET

from odoo import _, api, fields, models


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.depends("order_line.product_id.name")
    def _get_hotel_name(self):
        for order in self:
            if order.order_line:
                # Récupérer le nom du produit de la première ligne de commande
                order.hotel_name = order.order_line[0].product_id.name
            else:
                # Si aucune ligne de commande n'existe, assigner une chaîne vide
                order.hotel_name = ""

    hotel_name = fields.Char(
        string="Hotel", required=False, compute=_get_hotel_name, store=True
    )

    def _get_total_rooms(self):
        for order in self:
            rooms = 0
            for line in order.order_line:
                rooms += line.number_of_rooms
            order.total_rooms = rooms

    total_rooms = fields.Integer(
        string="Total Rooms", required=False, compute=_get_total_rooms
    )
