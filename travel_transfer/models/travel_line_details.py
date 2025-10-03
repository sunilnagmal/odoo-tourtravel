from odoo import _, api, fields, models


class TravelLineDetails(models.Model):
    _inherit = "travel.line.details"

    travel_type = fields.Selection(selection_add=[("transfer", "Transfer")])
    calculation_method = fields.Selection(selection_add=[("vehicles", "Per vehicle")])

    vehicle_type_id = fields.Many2one(
        "product.attribute.value",
        string="Vehicle Type",
        domain=lambda self: [
            ("attribute_id", "=", self.env.ref("travel_transfer.vehicle_type").id)
        ],
    )
    vehicle_confort_id = fields.Many2one(
        "product.attribute.value",
        string="Vehicle Confort",
        domain=lambda self: [
            ("attribute_id", "=", self.env.ref("travel_transfer.vehicle_confort").id)
        ],
    )
    vehicle_guide_id = fields.Many2one(
        "product.attribute.value",
        string="Vehicle Guide",
        domain=lambda self: [
            ("attribute_id", "=", self.env.ref("travel_transfer.vehicle_guide").id)
        ],
    )

    @api.onchange(
        "product_template_id",
        "vehicle_type_id",
        "vehicle_confort_id",
        "vehicle_guide_id",
    )
    def _onchange_attributes_transfer(self):
        """
        Onchange method to set the product name based on the selected attributes
        """
        for line in self:
            if line.travel_type == "transfer":
                if (
                    line.vehicle_type_id
                    and line.vehicle_confort_id
                    and line.vehicle_guide_id
                    and line.product_template_id
                ):
                    attribute_ids = [
                        {
                            "value_ids": line.vehicle_type_id.id,
                            "attribute_id": self.env.ref(
                                "travel_transfer.vehicle_type"
                            ).id,
                        },
                        {
                            "value_ids": line.vehicle_confort_id.id,
                            "attribute_id": self.env.ref(
                                "travel_transfer.vehicle_confort"
                            ).id,
                        },
                        {
                            "value_ids": line.vehicle_guide_id.id,
                            "attribute_id": self.env.ref(
                                "travel_transfer.vehicle_guide"
                            ).id,
                        },
                    ]
                    # Get the product based on the selected attributes
                    product_id = line.product_template_id._get_unique_product_variant_id_from_attributes(
                        attribute_ids
                    )
                    line.product_id = product_id if product_id else False

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
            if record.travel_type != "transfer":
                return super(
                    TravelLineDetails, record
                )._compute_total_travel_line_details()

            if record.calculation_method not in ["passengers", "vehicles"]:
                raise UserError(
                    _("Invalid calculation method '%s' for travel_type %s")
                    % (record.calculation_method, record.travel_type)
                )
            if record.calculation_method == "passengers":
                record.quantity = record.adults + record.children + record.infants
                record.total_cost = (
                    record.cost_unit * record.adults
                    + record.cost_unit_child * record.children
                    + record.cost_unit_infant * record.infants
                )
            elif record.calculation_method == "vehicles":
                record.quantity = 1
                record.total_cost = record.cost_unit
                record.total_price = record.price_unit
