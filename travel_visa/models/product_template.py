import datetime as dt

from odoo import _, api, fields, models

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = ["product.template"]

    travel_type = fields.Selection(selection_add=[("visa", "Visa")])

    def set_travel_attributes(self):
        """
        To be overriden n by specific type of travels to add attributes
        """
        attributes_xml_ids = [
            "travel_visa.product_attribute_visa_type",
            "travel_visa.product_attribute_visa_entry_number",
        ]
        visa_products = self.filtered(lambda p: p.travel_type == "visa")
        visa_products._set_travel_attributes(attributes=attributes_xml_ids)
        super(ProductTemplate, self).set_travel_attributes()

    def set_default_category(self):
        """
        Set the default category for visa products.
        """
        if not self.travel_type or self.travel_type != "visa":
            return super(ProductTemplate, self).set_default_category()

        category = self.env.ref(
            "travel_visa.product_category_visa", raise_if_not_found=False
        )
        if not category:
            raise UserError(_("Visa product category not found."))
        self.categ_id = category.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("travel_type") == "visa" and not vals.get("categ_id"):
                category = self.env.ref(
                    "travel_visa.product_category_visa", raise_if_not_found=False
                )
                if category:
                    vals["categ_id"] = category.id
        return super().create(vals_list)
