import logging
import pprint
import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_hotel_name(self):
        for move in self:
            hotel_name = []
            for invoice_line in move.invoice_line_ids:
                for sale_line in invoice_line.sale_line_ids:
                    if sale_line.product_id.travel_type == "hotel":
                        hotel_name.append(sale_line.order_id.hotel_id.name)
            move.hotel_name = ", ".join(hotel_name) if hotel_name else False

    def _get_total_rooms(self):
        for move in self:
            total_rooms = 0
            for invoice_line in move.invoice_line_ids:
                for sale_line in invoice_line.sale_line_ids:
                    if sale_line.product_id.travel_type == "hotel":
                        total_rooms += sale_line.number_of_rooms
            move.total_rooms = total_rooms

    hotel_name = fields.Char(string="Hotel", required=False, compute=_get_hotel_name)

    total_rooms = fields.Integer(string="Total Rooms", compute=_get_total_rooms)
