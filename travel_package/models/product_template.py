import datetime as dt

from odoo import _, api, fields, models

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = ["product.template"]

    travel_type = fields.Selection(selection_add=[("package", "Package")])

    @api.depends("travel_type")
    def _compute_list_price_child_visibility(self):
        """
        Compute the visibility of the calculation method field based on the travel type.
        """
        for line in self:
            if line.travel_type != "package":
                return super()._compute_list_price_child_visibility()
            line.has_child_price = True

    @api.depends("travel_type")
    def _compute_list_price_infant_visibility(self):
        """
        Compute the visibility of the calculation method field based on the travel type.
        """
        for line in self:
            if line.travel_type != "package":
                return super()._compute_list_price_infant_visibility()
            line.has_infant_price = True

    def set_default_category(self):
        """
        Set the default category for package products.
        """
        if not self.travel_type or self.travel_type != "package":
            return super(ProductTemplate, self).set_default_category()

        category = self.env.ref(
            "travel_package.product_category_package", raise_if_not_found=False
        )
        if not category:
            raise UserError(_("Package product category not found."))
        self.categ_id = category.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("travel_type") == "package" and not vals.get("categ_id"):
                category = self.env.ref(
                    "travel_package.product_category_package", raise_if_not_found=False
                )
                if category:
                    vals["categ_id"] = category.id
        return super().create(vals_list)
