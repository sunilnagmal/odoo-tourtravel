import datetime as dt

from odoo import _, api, fields, models

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = ["product.template"]

    travel_type = fields.Selection(selection_add=[("misc", "Misc")])

    def set_default_category(self):
        """
        Set the default category for miscellaneous products.
        """
        if not self.travel_type or self.travel_type != "misc":
            return super(ProductTemplate, self).set_default_category()

        category = self.env.ref(
            "travel_misc.product_category_misc", raise_if_not_found=False
        )
        if not category:
            raise UserError(_("Miscellaneous product category not found."))
        self.categ_id = category.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("travel_type") == "misc" and not vals.get("categ_id"):
                category = self.env.ref(
                    "travel_misc.product_category_misc", raise_if_not_found=False
                )
                if category:
                    vals["categ_id"] = category.id
        return super().create(vals_list)
