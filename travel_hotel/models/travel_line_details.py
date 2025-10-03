from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class TravelLineDetails(models.Model):
    _inherit = "travel.line.details"

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
                                "value_ids": line.room_view_id.id,
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

    @api.depends("adults", "children")
    def _compute_pax(self):
        """Compute total pax (adults + children)"""
        for record in self:
            record.pax = record.adults + record.children

    @api.onchange("adults")
    def _validate_rooms_occupation(self):
        """Validate maximum adults per room"""
        for record in self:
            if record.travel_type == "hotel" and record.adults > 3:
                raise ValidationError(_("The maximum number of adults is 3 per room."))

    @api.onchange(
        "adults",
        "children",
        "infants",
        "product_id",
        "price_unit",
        "price_unit_child",
        "price_unit_infant",
        "cost_unit",
        "cost_unit_child",
        "cost_unit_infant",
    )
    def _compute_total_travel_line_details(self):
        for record in self:
            if record.travel_type != "hotel":
                return super(
                    TravelLineDetails, record
                )._compute_total_travel_line_details()
            if record.calculation_method not in ["rooms", "passengers"]:
                raise ValidationError(
                    _("Invalid calculation method '%s' for travel_type %s")
                    % (record.calculation_method, record.travel_type)
                )
            if record.calculation_method == "rooms":
                record.quantity = 1
                record.total_cost = (
                    record.cost_unit + record.cost_unit_child + record.cost_unit_infant
                )
                record.total_price = (
                    record.price_unit
                    + record.price_unit_child
                    + record.price_unit_infant
                )
            elif record.calculation_method == "passengers":
                record.quantity = record.adults + record.children + record.infants
                record.total_cost = (
                    record.cost_unit * record.adults
                    + record.cost_unit_child * record.children
                    + record.cost_unit_infant * record.infants
                )
                record.total_price = (
                    record.price_unit * record.adults
                    + record.price_unit_child * record.children
                    + record.price_unit_infant * record.infants
                )
