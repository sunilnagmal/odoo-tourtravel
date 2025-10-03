from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

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

    @api.onchange("travel_type")
    def _compute_calculation_method_visibility(self):
        """
        Compute the visibility of the calculation method field based on the travel type.
        """
        for line in self:
            if not line.travel_type or line.travel_type != "transfer":
                return super(
                    SaleOrderLine, line
                )._compute_calculation_method_visibility()

            line.calculation_method_visible = True
            line.calculation_method = "vehicles"

    @api.depends(
        "adults",
        "children",
        "calculation_method",
    )
    def _compute_quantity(self):
        """
        Compute the quantity based on the calculation method:
        - 'vehicles': provided values
        - 'passengers': paxs
        """
        for line in self:
            if line.travel_type != "transfer":
                return super(SaleOrderLine, line)._compute_quantity()
            if not line.calculation_method:
                line.product_uom_qty = 0
            elif line.calculation_method == "passengers":
                line.paxs = line.adults + line.children
                line.product_uom_qty = line.paxs
            elif line.calculation_method == "vehicles":
                pass
            else:
                raise UserError(
                    _("Invalid calculation method '%s' for  travel_type %s")
                    % line.calculation_method,
                    line.travel_type,
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
