from odoo import _, api, fields, models


class TravelLineDetails(models.Model):
    _inherit = "travel.line.details"

    travel_type = fields.Selection(selection_add=[("car", "Car")])

    transmission_id = fields.Many2one(
        "product.attribute.value",
        domain=lambda self: [
            ("attribute_id", "=", self.env.ref("travel_car.vehicle_transmission").id)
        ],
    )
    class_id = fields.Many2one(
        "product.attribute.value",
        domain=lambda self: [
            ("attribute_id", "=", self.env.ref("travel_car.vehicle_class").id)
        ],
    )

    @api.onchange("product_template_id", "transmission_id", "class_id")
    def _onchange_attributes_car(self):
        """
        Onchange method to set the product name based on the selected attributes
        """
        for line in self:
            if line.travel_type == "car":
                if line.transmission_id and line.class_id and line.product_template_id:
                    # Get the product based on the selected attributes
                    attribute_ids = [
                        {
                            "value_ids": line.transmission_id.id,
                            "attribute_id": self.env.ref(
                                "travel_car.vehicle_transmission"
                            ).id,
                        },
                        {
                            "value_ids": line.class_id.id,
                            "attribute_id": self.env.ref("travel_car.vehicle_class").id,
                        },
                    ]
                    product_id = line.product_template_id._get_unique_product_variant_id_from_attributes(
                        attribute_ids
                    )

                    line.product_id = product_id if product_id else False
