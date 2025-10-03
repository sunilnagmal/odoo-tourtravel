from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = ["product.template"]

    travel_type = fields.Selection(selection_add=[("activity", "Activity")])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("travel_type") == "activity" and not vals.get("categ_id"):
                category = self.env.ref(
                    "travel_activity.product_category_activity",
                    raise_if_not_found=False,
                )
                if category:
                    vals["categ_id"] = category.id
        return super(ProductTemplate, self).create(vals_list)

    def set_default_category(self):
        """
        Set the default category for activity products.
        """
        if not self.travel_type or self.travel_type != "activity":
            return super(ProductTemplate, self).set_default_category()

        category = self.env.ref(
            "travel_activity.product_category_activity", raise_if_not_found=False
        )
        if not category:
            raise UserError(_("Activity product category not found."))
        self.categ_id = category.id
