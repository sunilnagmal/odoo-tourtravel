from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = ["product.template"]

    travel_type = fields.Selection(selection_add=[("transfer", "Transfer")])

    origin = fields.Many2one("travel_core.destination", "Origin")
    to = fields.Many2one("travel_core.destination", "To")

    def set_travel_attributes(self):
        """
        To be overriden n by specific type of travels to add attributes
        """
        attributes_xml_ids = [
            "travel_transfer.vehicle_type",
            "travel_transfer.vehicle_confort",
            "travel_transfer.vehicle_guide",
        ]
        transfer_products = self.filtered(lambda p: p.travel_type == "transfer")
        transfer_products._set_travel_attributes(attributes=attributes_xml_ids)
        super(ProductTemplate, self).set_travel_attributes()

    def set_default_category(self):
        """
        Set the default category for transfer products.
        """
        if not self.travel_type or self.travel_type != "transfer":
            return super(ProductTemplate, self).set_default_category()

        category = self.env.ref(
            "travel_transfer.product_category_transfer", raise_if_not_found=False
        )
        if not category:
            raise UserError(_("Transfer product category not found."))
        self.categ_id = category.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("travel_type") == "transfer" and not vals.get("categ_id"):
                category = self.env.ref(
                    "travel_transfer.product_category_transfer",
                    raise_if_not_found=False,
                )
                if category:
                    vals["categ_id"] = category.id
        return super().create(vals_list)
