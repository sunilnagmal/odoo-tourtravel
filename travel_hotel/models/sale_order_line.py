import logging
import datetime
import pprint

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange("start_date", "end_date")
    def _compute_nights(self):
        for line in self:
            if line.travel_type != "hotel":
                line.nights = 0
            try:
                line.nights = (line.end_date - line.start_date).days
            except (TypeError, AttributeError) as e:
                line.nights = 0

    product_template_id = fields.Many2one(store=True)
    nights = fields.Integer("Nights", compute=_compute_nights)
    number_of_rooms = fields.Integer(
        string="# Rooms", compute="_compute_number_of_rooms", default=0
    )

    travel_type = fields.Selection(selection_add=[("hotel", "Hotel")])

    calculation_method = fields.Selection(selection_add=[("rooms", "Per Room")])
    meal_plan_id = fields.Many2one(
        "product.attribute.value",
        domain=lambda self: [
            (
                "attribute_id",
                "=",
                self.env.ref("travel_hotel.product_attribute_meal_plan").id,
            )
        ],
    )

    room_type_id = fields.Many2one(
        "product.attribute.value",
        domain=lambda self: [
            (
                "attribute_id",
                "=",
                self.env.ref("travel_hotel.product_attribute_room_type").id,
            )
        ],
    )

    room_view_id = fields.Many2one(
        "product.attribute.value",
        domain=lambda self: [
            (
                "attribute_id",
                "=",
                self.env.ref("travel_hotel.product_attribute_room_view").id,
            )
        ],
    )

    def _get_room_type(self):
        """
        Get the room type from the product template.
        """
        for line in self:
            if line.travel_type == "hotel" and line.product_id:
                room_type = line.product_id._get_travel_product_attribute(
                    "travel_hotel.product_attribute_room_type"
                )
                if room_type:
                    line.room_type_id = room_type.id
                else:
                    line.room_type_id = False

    @api.depends("travel_type")
    def _compute_calculation_method_visibility(self):
        """
        Compute the visibility of the calculation method field based on the travel type.
        """
        for line in self:
            if not line.travel_type or line.travel_type != "hotel":
                return super(
                    SaleOrderLine, line
                )._compute_calculation_method_visibility()

            line.calculation_method_visible = True
            line.calculation_method = "rooms"

    @api.depends("travel_type")
    def _compute_details_tab_visibility(self):
        """
        Compute the visibility of the details tab based on the travel type
        """
        for line in self:
            if line.travel_type != "hotel":
                return super(SaleOrderLine, line)._compute_details_tab_visibility()
            line.details_tab_visible = True

    def get_margin_days(self, params):
        """
        The number of days of the service countable for apply a per day margin.
        Redefining the travel_core function
        """
        return super(SaleOrderLine, self).get_margin_days(params) - 1

    @api.depends("tl_detail_ids")
    def _compute_number_of_rooms(self):
        for line in self:
            if line.travel_type != "hotel":
                line.number_of_rooms = 0
                continue
            number_of_rooms = 0
            for room in line.tl_detail_ids:
                number_of_rooms += room.quantity
            line.number_of_rooms = number_of_rooms

    @api.onchange(
        "tl_detail_ids",
        "tl_detail_ids.quantity",
        "tl_detail_ids.total_price",
        "tl_details_ids.cost_price",
    )
    def _compute_so_line_total_from_tl_details(self):
        """
        Compute the quantity based on the calculation method:
        - 'rooms': number_of_rooms * nights
        - 'passengers': paxs * nights
        """
        for line in self:
            super()._compute_so_line_total_from_tl_details()

            if line.travel_type == "hotel":
                line.number_of_rooms = sum(line.tl_detail_ids.mapped("quantity"))
                if (
                    not line.calculation_method
                ):  # Gestion du cas où calculation_method n'est pas défini
                    line.product_uom_qty = 0
                elif line.calculation_method == "rooms":
                    line.product_uom_qty = (line.number_of_rooms or 0) * (
                        line.nights or 0
                    )
                elif line.calculation_method == "passengers":
                    line.product_uom_qty = (line.paxs or 0) * (line.nights or 0)
                else:
                    raise UserError(
                        _("Invalid calculation method '%s' for  travel_type %s")
                        % line.calculation_method,
                        line.travel_type,
                    )

    def print_voucher(self):
        for reservation in self:
            if reservation.travel_type != "hotel":
                return super().print_voucher()
            if reservation.state in ["sale", "done"]:
                return self.env.ref(
                    "travel_hotel.travel_confirmation_report_document"
                ).report_action(reservation)

    @api.onchange("product_template_id", "meal_plan_id", "room_type_id", "room_view_id")
    def _onchange_attributes_hotel(self):
        """
        Onchange method to set the product name based on the selected attributes
        """
        for line in self:
            if line.travel_type == "hotel":
                if line.meal_plan_id and line.room_type_id and line.product_template_id:
                    attribute_ids = [
                        {
                            "value_ids": line.meal_plan_id.id,
                            "attribute_id": self.env.ref(
                                "travel_hotel.product_attribute_meal_plan"
                            ).id,
                        },
                        {
                            "value_ids": line.room_type_id.id,
                            "attribute_id": self.env.ref(
                                "travel_hotel.product_attribute_room_type"
                            ).id,
                        },
                    ]
                    if line.room_view_id:
                        attribute_ids.append(
                            {
                                "values_ids": line.room_view_id.id,
                                "attribute_id": self.env.ref(
                                    "travel_hotel.product_attribute_room_view"
                                ),
                            }
                        )
                    # Get the product based on the selected attributes
                    product_id = line.product_template_id._get_unique_product_variant_id_from_attributes(
                        attribute_ids
                    )
                    line.product_id = product_id if product_id else False
