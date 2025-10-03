##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2023 Odoo S.A. (<https://www.odoo.com>).
#
##############################################################################

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_round


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    pricelist_item_ids = fields.One2many(
        "product.pricelist.item",
        "pricelist_id",
        string="Items",
        compute="_compute_pricelist_items",
    )

    def _compute_pricelist_items(self):
        for pricelist in self:
            items = self.env["product.pricelist.item"].search(
                [("pricelist_id", "=", pricelist.id)]
            )
            pricelist.pricelist_item_ids = items

    def _get_price_rule(self, products, quantity, date=False, uom_id=False):
        """Override to add margin per pax calculation"""
        self.ensure_one()
        date = date or fields.Date.today()

        if not products:
            return {}

        rules = self._get_rules(products, quantity, date, uom_id)
        prices = {}

        for product in products:
            rule_id = rules.get(product.id)
            if not rule_id:
                continue

            rule = self.env["product.pricelist.item"].browse(rule_id)
            price = product._get_price_from_rule(rule)

            # Add margin per pax calculation if available in context
            if "params" in self._context:
                paxs = self.env["sale.order.line"].get_total_paxs(
                    self._context["params"]
                )
                days = self.env["sale.order.line"].get_margin_days(
                    self._context["params"]
                )
                price += days * paxs * (rule.margin_per_pax or 0.0)

            prices[product.id] = price

        return prices

    def _get_rules(self, products, quantity, date, uom_id):
        """Get applicable rules for products"""
        self.ensure_one()
        domain = [
            ("pricelist_id", "=", self.id),
            "|",
            ("date_start", "=", False),
            ("date_start", "<=", date),
            "|",
            ("date_end", "=", False),
            ("date_end", ">=", date),
            "|",
            ("product_tmpl_id", "in", products.mapped("product_tmpl_id").ids),
            "|",
            ("product_id", "in", products.ids),
            "&",
            ("categ_id", "in", products.mapped("categ_id").ids),
            ("applied_on", "=", "2_product_category"),
        ]

        if uom_id:
            domain += ["|", ("min_quantity", "<=", quantity), ("min_quantity", "=", 0)]

        rules = self.env["product.pricelist.item"].search(
            domain, order="min_quantity desc"
        )
        return {
            product.id: rules.filtered(
                lambda r: self._is_rule_applicable(r, product, quantity)
            ).id
            for product in products
        }

    def _is_rule_applicable(self, rule, product, quantity):
        """Check if rule is applicable to product"""
        if rule.min_quantity and quantity < rule.min_quantity:
            return False

        if rule.product_tmpl_id and product.product_tmpl_id != rule.product_tmpl_id:
            return False

        if rule.product_id and product != rule.product_id:
            return False

        if rule.categ_id:
            return (
                product.categ_id == rule.categ_id
                or product.categ_id.parent_id == rule.categ_id
            )

        return True


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    margin_per_pax = fields.Float(
        string="Margin per Pax",
        digits="Product Price",
        help="Additional margin applied per passenger",
    )

    supplier_id = fields.Many2one(
        "res.partner", string="Supplier", domain="[('supplier_rank', '>', 0)]"
    )

    @api.model
    def _get_default_supplier(self):
        """Get default supplier from context"""
        return self._context.get("supplier_id", False)
