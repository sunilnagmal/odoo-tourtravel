import datetime as dt

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class ProductTemplate(models.Model):
    _inherit = ["product.template"]

    travel_type = fields.Selection(selection_add=[("car", "Car")])

    passengers = fields.Integer("Passengers")

    def set_travel_attributes(self):
        """
        To be overriden n by specific type of travels to add attributes
        """
        attributes_xml_ids = [
            "travel_car.vehicle_transmission",
            "travel_car.vehicle_class",
        ]
        car_products = self.filtered(lambda p: p.travel_type == "car")
        car_products._set_travel_attributes(attributes=attributes_xml_ids)
        super(ProductTemplate, self).set_travel_attributes()

    def set_default_category(self):
        """
        Set the default category for car products.
        """
        if not self.travel_type or self.travel_type != "car":
            return super(ProductTemplate, self).set_default_category()

        category = self.env.ref(
            "travel_car.product_category_car", raise_if_not_found=False
        )
        if not category:
            raise UserError(_("Car product category not found."))
        self.categ_id = category.id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("travel_type") == "car" and not vals.get("categ_id"):
                category = self.env.ref(
                    "travel_car.product_category_car", raise_if_not_found=False
                )
                if category:
                    vals["categ_id"] = category.id
        return super(ProductTemplate, self).create(vals_list)
