from odoo import _, api, fields, models


class TravelLineDetails(models.Model):
    _inherit = "travel.line.details"

    travel_type = fields.Selection(selection_add=[("visa", "Visa")])
    visa_type_id = fields.Many2one(
        "product.attribute.value",
        string="Visa Type",
        domain=lambda self: [
            (
                "attribute_id",
                "=",
                self.env.ref("travel_visa.product_attribute_visa_type").id,
            )
        ],
    )

    number_of_entries_id = fields.Many2one(
        "product.attribute.value",
        string="Number of entries",
        domain=lambda self: [
            (
                "attribute_id",
                "=",
                self.env.ref("travel_visa.product_attribute_visa_entry_number").id,
            )
        ],
    )

    visa_validity = fields.Integer(string="Visa Validity", help="Visa Validity")
    visa_validity_unit = fields.Selection(
        string="Visa Validity Unit",
        selection=[
            ("day", "Day"),
            ("week", "Week"),
            ("month", "Month"),
            ("year", "Year"),
        ],
        help="Select the unit of visa validity",
    )

    @api.onchange("product_template_id", "visa_type_id", "number_of_entries_id")
    def _onchange_attributes_visa(self):
        """
        Onchange method to set the product name based on the selected attributes
        """
        for line in self:
            if line.travel_type == "visa":
                if (
                    line.visa_type_id
                    and line.number_of_entries_id
                    and line.product_template_id
                ):
                    attributes_ids = [
                        {
                            "attribute_id": self.env.ref(
                                "travel_visa.product_attribute_visa_type"
                            ).id,
                            "value_ids": line.visa_type_id.id,
                        },
                        {
                            "attribute_id": self.env.ref(
                                "travel_visa.product_attribute_visa_entry_number"
                            ).id,
                            "value_ids": line.number_of_entries_id.id,
                        },
                    ]
                    # Get the product based on the selected attributes
                    product_id = line.product_template_id._get_unique_product_variant_id_from_attributes(
                        attributes_ids
                    )
                    line.product_id = product_id if product_id else False
