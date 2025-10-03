import datetime as dt

from odoo import _, api, fields, models

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = ["product.template"]

    travel_type = fields.Selection(selection_add=[("hotel", "Hotel")])
    stars = fields.Selection(
        string="Stars",
        selection=[
            ("0", "0 star"),
            ("1", "1 star"),
            ("2", "2 stars"),
            ("3", "3 stars"),
            ("4", "4 stars"),
            ("5", "5 stars"),
        ],
    )
    res_partner_id = fields.Many2one(
        "res.partner", "Contact", domain=[("parent_id", "=", "chain_id")]
    )
    chain_id = fields.Many2one("res.partner", "Chain")
    destination = fields.Many2one(
        "travel_core.destination",
        "Destination",
        compute=False,  # Désactive le calcul automatique pendant la migration
        store=True,
    )

    allotment_ids = fields.One2many(
        "travel_hotel.allotment", "product_tmpl_id", "Allotment"
    )

    def set_default_category(self):
        """
        Set the default category for hotel products.
        """
        if not self.travel_type or self.travel_type != "hotel":
            return super(ProductTemplate, self).set_default_category()

        category = self.env.ref(
            "travel_hotel.product_category_hotel", raise_if_not_found=False
        )
        if not category:
            raise UserError(_("Hotel product category not found."))
        self.categ_id = category.id

    def set_travel_attributes(self):
        """
        To be overriden n by specific type of travels to add attributes
        """
        attributes_xml_ids = [
            "travel_hotel.product_attribute_meal_plan",
            "travel_hotel.product_attribute_room_view",
            "travel_hotel.product_attribute_room_type",
        ]
        hotel_products = self.filtered(lambda p: p.travel_type == "hotel")
        hotel_products._set_travel_attributes(attributes=attributes_xml_ids)
        super(ProductTemplate, self).set_travel_attributes()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("travel_type") == "hotel" and not vals.get("categ_id"):
                category = self.env.ref(
                    "travel_hotel.product_category_hotel", raise_if_not_found=False
                )
                if category:
                    vals["categ_id"] = category.id
        return super().create(vals_list)


class product_rate(models.Model):
    _name = "product.rate"
    _inherit = "product.rate"

    # TODO Fix based on pricelist
    simple = fields.Float("Simple")
    triple = fields.Float("Triple")
    extra_adult = fields.Float("Extra Adult")
    second_child = fields.Float("Second Child")
