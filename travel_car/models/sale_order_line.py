from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

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
                    # Get the product based on the selected attributes
                    product_id = line.product_template_id._get_unique_product_variant_id_from_attributes(
                        attribute_ids
                    )

                    line.product_id = product_id if product_id else False

    @api.onchange("start_date", "end_date", "travel_type")
    def _compute_nights(self):
        for line in self:
            if line.travel_type != "car":
                line.nights = 0
            try:
                line.nights = (line.end_date - line.start_date).days
            except (TypeError, AttributeError) as e:
                line.nights = 0

    @api.onchange("start_date", "end_date", "travel_type")
    def _compute_quantity(self):
        """
        Compute number of days between date_end and date start
        """
        for line in self:
            if line.travel_type != "car":
                return super(SaleOrderLine, self)._compute_quantity()
            line.product_uom_qty = (line.end_date - line.start_date).days
