import datetime
import logging
import pprint
from odoo import _, api, fields, models, Command
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_reservations(self):
        result = {}
        order_line = self.env["sale.order.line"]

        for obj in self:
            to_search = [
                ("product_template_id", "=", obj.id),
                ("start_date", ">=", datetime.datetime.today()),
            ]
            l_ids = order_line.search(to_search)
            result[obj.id] = l_ids
            if len(l_ids):
                obj.reservation_ids = l_ids
            else:
                obj.reservation_ids = None

    reservation_ids = fields.Many2many(
        "sale.order.line", "Reservations", compute=_get_reservations
    )

    categ_id = fields.Many2one("product.category")

    travel_product = fields.Boolean(string="Is travel product", default=False)
    travel_type = fields.Selection(string="Travel product type", selection=[])

    list_price_child = fields.Float("Price for children", default=0.0)
    has_child_price = fields.Boolean(compute="_compute_list_price_child_visibility")
    list_price_infant = fields.Float("Price for infant", default=0.0)
    has_infant_price = fields.Boolean(compute="_compute_list_price_infant_visibility")

    standard_price_child = fields.Float("Cost for children", default=0.0)
    standard_price_infant = fields.Float("Cost for infant", default=0.0)

    @api.depends("travel_type")
    def _compute_list_price_child_visibility(self):
        """
        Compute the visibility of the calculation method field based on the travel type.
        """
        for line in self:
            line.has_child_price = False

    @api.depends("travel_type")
    def _compute_list_price_infant_visibility(self):
        """
        Compute the visibility of the calculation method field based on the travel type.
        """
        for line in self:
            line.has_infant_price = False

    @api.onchange("travel_type")
    def _onchange_travel_type(self):
        """
        Set the product type if travel_type is defined to service.
        """
        if self.travel_type:
            self.detailed_type = "service"

    def set_travel_attributes(self):
        """
        To be overriden n by specific type of travels to add attributes
        """
        pass

    def _set_travel_attributes(self, attributes=None):
        """
        Set travel attributes for the product template.
        If attributes is None or empty, does nothing.

        Args:
            attributes (list): List of XML IDs of product.attribute to set.
                            Example: ['module.product_attribute_color', 'module.product_attribute_size']
        """
        if not attributes:
            return

        # Validate XML IDs and collect module.name pairs
        valid_xml_ids = []
        for xml_id in attributes:
            if not isinstance(xml_id, str):
                _logger.warning("Skipping invalid XML ID (not a string): %s", xml_id)
                continue
            if "." not in xml_id:
                _logger.warning(
                    "Skipping invalid XML ID format (missing module): %s", xml_id
                )
                continue
            valid_xml_ids.append(xml_id)

        if not valid_xml_ids:
            return

        # Get all valid attributes in one query
        try:
            # Split the XML IDs into module and name pairs
            xml_pairs = [
                (xml_id.split(".")[0], xml_id.split(".")[1]) for xml_id in valid_xml_ids
            ]

            # Get the attribute IDs
            attribute_ids = []
            for module, name in xml_pairs:
                record = self.env["ir.model.data"].search(
                    [
                        ("model", "=", "product.attribute"),
                        ("module", "=", module),
                        ("name", "=", name),
                    ],
                    limit=1,
                )
                if record:
                    attribute_ids.append(record.res_id)

            if not attribute_ids:
                _logger.warning(
                    "No valid product attributes found for XML IDs: %s", valid_xml_ids
                )
                return

            # Get attributes with their values
            attributes_data = self.env["product.attribute"].search_read(
                [("id", "in", attribute_ids)], ["id", "value_ids"]
            )

            # Prepare attribute lines
            attribute_lines_commands = []
            for attr_data in attributes_data:
                if attr_data["value_ids"]:
                    attribute_lines_commands.append(
                        Command.create(
                            {
                                "attribute_id": attr_data["id"],
                                "value_ids": [Command.set(attr_data["value_ids"])],
                            }
                        )
                    )

            if attribute_lines_commands:
                self.write({"attribute_line_ids": attribute_lines_commands})

        except Exception as e:
            _logger.error("Error setting travel attributes: %s", str(e))
            raise UserError(
                _(
                    "Error setting travel attributes. Please check the attribute XML IDs."
                )
            )

    def set_default_category(self):
        """
        Implement this in specific modules to set the default category
        """
        pass

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override the create method to give attributes for travel_type
        """

        res = super(ProductTemplate, self).create(vals_list)
        travel_products = res.filtered(lambda p: p.travel_type)
        for product in travel_products:
            product.set_default_category()
            product.set_travel_attributes()
        return res

    def _get_unique_product_variant_id_from_attributes(self, attribute_value_ids):
        """
        Gets variants of self that match all the given attributes.
        :param attribute_value_ids: list of dicts [{'value_ids': x, 'attribute_id': y}, ...]
        :return: product.product id or False if not found or multiple matches
        """
        if not attribute_value_ids:
            return None

        # Get all variants for this template
        variants = self.env["product.product"].search(
            [("product_tmpl_id", "=", self.id)]
        )

        try:
            # Filter variants that match ALL specified attribute values
            matching_variants = variants.filtered(
                lambda v: all(
                    any(
                        ptav.product_attribute_value_id.id == value_dict["value_ids"]
                        for ptav in v.product_template_attribute_value_ids
                    )
                    for value_dict in attribute_value_ids
                )
            )
        except Exception as e:
            _logger.error(
                "Error matching product variants with attribute_value_ids: %s. Provided values: %s",
                str(e),
                attribute_value_ids,
            )
            raise UserError(
                _(
                    "Error matching product variants. Please check the format of attribute_value_ids: %s\nProvided values: %s"
                )
                % (str(e), attribute_value_ids)
            )

        return matching_variants.id if len(matching_variants) == 1 else False
