import time
from datetime import datetime
import logging
import pprint

from xml.etree import ElementTree as ET

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_compare, float_is_zero, float_round

_logger = logging.getLogger(__name__)


class sale_order_line(models.Model):
    _inherit = "sale.order.line"

    description = fields.Text("Full Description")
    travel_type = fields.Selection(string="Travel product type", selection=[])
    price_unit_cost = fields.Float("Cost Price", digits="Product Price")
    start_date = fields.Date("Start Date")
    end_date = fields.Date("End Date")
    category_id = fields.Many2one("product.category", "Product Category")
    supplier_id = fields.Many2one("res.partner", "Supplier")
    category = fields.Char("Travel Category")
    adults = fields.Integer("Adults")
    children = fields.Integer("Children")
    infants = fields.Integer("Infants")
    start_time = fields.Char("Start Time")
    start_place = fields.Many2one("travel_core.destination", "From")
    end_time = fields.Char("End Time")
    end_place = fields.Many2one("travel_core.destination", "To")
    reservation_number = fields.Char("Reservation")
    paxs = fields.Integer("Paxs", compute="_compute_paxs", store=True)
    # TODO Why did we redefine this field Cause #298
    product_uom_qty = fields.Float(
        string="Quantity",
        digits="Product Unit of Measure",
        required=True,
        default=0.0,
        compute="_compute_quantity",
        store=True,
        readonly=False,
    )
    validity_date = fields.Date("Validity Date", related="order_id.validity_date")

    calculation_method = fields.Selection(
        string="Calculation method", selection=[("passengers", "Per passenger")]
    )

    tl_detail_ids = fields.One2many(
        "travel.line.details", "order_line_id", "Travel line details"
    )

    # Fields visibility
    infants_visible = fields.Boolean(compute="_compute_infants_visibility")

    details_tab_visible = fields.Boolean(compute="_compute_details_tab_visibility")

    calculation_method_visible = fields.Boolean(
        compute="_compute_calculation_method_visibility"
    )

    @api.depends("travel_type")
    def _compute_details_tab_visibility(self):
        """
        Compute the visibility of the details tab based on the travel type.
        Hidden by default. Inherit in modules
        """
        for line in self:
            line.details_tab_visible = False

    @api.depends("travel_type")
    def _compute_infants_visibility(self):
        """
        Compute the visibility of the details tab based on the travel type.
        Hidden by default. Inherit in modules
        """
        for line in self:
            line.infants_visible = False

    @api.depends("travel_type", "tl_detail_ids")
    def _compute_tl_details_fields_visibility(self):
        """
        Compute the visibility of the transfer based on the travel type.
        """
        pass

    @api.depends("travel_type")
    def _compute_calculation_method_visibility(self):
        """
        Compute the visibility of the calculation method field based on the travel type.
        """
        for line in self:
            line.calculation_method_visible = False

    @api.depends("adults", "children", "infants")
    def _compute_paxs(self):
        for order in self:
            order.paxs = order.adults + order.children + order.infants

    def default_currency_cost(self):
        company = self.env.user.company_id
        return company.currency_id

    currency_cost_id = fields.Many2one(
        "res.currency",
        "Currency Cost",
        default=lambda self: self.env.company.currency_id,
    )
    customer_id = fields.Many2one(
        "res.partner",
        string="Customer Travel",
        related="order_id.partner_id",
        readonly=True,
        store=True,
    )

    def _compute_price_unit(self):
        """
        Compute the price unit for each sale order line.

        This method overrides the default behavior to check if the price unit
        is already set. If the price unit is not zero, it will not change the
        price. Otherwise, it will call the parent class's _compute_price_unit
        method to compute the price unit.

        Returns:
            None
        """
        for line in self:
            if line.price_unit != 0:
                # Do not change anything if price already set.
                continue
            super(sale_order_line, self)._compute_price_unit()

    def to_request(self):
        """
        Update the state of each sale order line to 'request'.

        This method iterates over each sale order line in the recordset and updates
        the 'state' field to 'request'.

        Returns:
            None
        """
        for line in self:
            line.update({"state": "request"})

    def to_requested(self):
        for line in self:
            line.update({"state": "requested"})

    def to_confirm(self):
        for line in self:
            line.update({"state": "sale"})

    def to_cancel(self):
        for line in self:
            line.update({"state": "cancel"})

    @api.onchange("travel_type")
    def _onchange_travel_type(self):
        for line in self:
            line.product_template_id = None
            line.product_id = None

    @api.onchange("product_template_id")
    def _onchange_product_template_id(self):
        """
        Handle the onchange event for the product_template_id field.

        When the product_template_id is changed:
        - Searches for all product variants associated with the selected product template.
        - Sets the domain for the product_id field to only include products from the selected template.
        - If there is only one product variant, automatically sets the product_id to that variant.

        Returns:
            dict: A dictionary specifying the domain for the product_id field.
        """
        if self.product_template_id:
            products = self.env["product.product"].search(
                [("product_tmpl_id", "=", self.product_template_id.id)]
            )
            domain = [("product_tmpl_id", "=", self.product_template_id.id)]

            # Auto-set product_id if there's only one variant
            if len(products) == 1:
                self.product_id = products[0]

            return {"domain": {"product_id": domain}}
        else:
            return {"domain": {"product_id": []}}

    def _get_seller_info(self, product_id, partner_id, quantity=0.0, date=None):
        self.ensure_one()
        if not product_id or not partner_id:
            return None
        res = self.env["product.supplierinfo"]
        search_domain = [
            ("product_id", "=", product_id.id),
            ("partner_id", "=", partner_id.id),
        ]
        candidates = self.env["product.supplierinfo"].search(search_domain)

        for seller in candidates:
            if seller.date_start and date and seller.date_start > date:
                _logger.info("Exit on date")
                continue
            if seller.date_end and date and seller.date_end < date:
                _logger.info("Exit on date 2")
                continue
            res |= seller

        return res.sorted("price")[:1]

    @api.onchange("product_id", "supplier_id", "start_date", "product_uom_qty")
    def _compute_so_line(self):
        for line in self:
            if not line.product_id:
                line.price_unit_cost = 0
                continue
            elif line.price_unit_cost != 0:
                continue
            else:
                if not line.supplier_id:
                    # We use standard price
                    po_line_uom = line.product_uom or line.product_id.uom_po_id
                    price_unit = line.env[
                        "account.tax"
                    ]._fix_tax_included_price_company(
                        line.product_id.uom_id._compute_price(
                            line.product_id.standard_price, po_line_uom
                        ),
                        line.product_id.supplier_taxes_id,
                        line.tax_id,
                        line.company_id,
                    )

                    line.price_unit_cost = float_round(
                        line.product_id.currency_id._convert(
                            price_unit,
                            line.currency_id,
                            line.company_id,
                            line.start_date or fields.Date.context_today(line),
                            False,
                        ),
                        precision_digits=max(
                            line.currency_id.decimal_places,
                            self.env["decimal.precision"].precision_get(
                                "Product Price"
                            ),
                        ),
                    )
                    continue

            if line.supplier_id and line.product_id:
                # We have a supplier define and a product_id
                seller = self._get_seller_info(
                    line.product_id,
                    line.supplier_id,
                    line.product_uom_qty,
                    line.start_date or fields.Date.context_today(line),
                )
                if not seller:
                    # No matching price rule
                    # raise UserError(_('No supplier rules matches this product'))
                    continue

                price_unit = (
                    line.env["account.tax"]._fix_tax_included_price_company(
                        seller.price,
                        line.product_id.supplier_taxes_id,
                        line.tax_id,
                        line.company_id,
                    )
                    if seller
                    else 0.0
                )
                price_unit = seller.currency_id._convert(
                    price_unit,
                    line.currency_id,
                    line.company_id,
                    line.start_date or fields.Date.context_today(line),
                    False,
                )
                price_unit = float_round(
                    price_unit,
                    precision_digits=max(
                        line.currency_id.decimal_places,
                        self.env["decimal.precision"].precision_get("Product Price"),
                    ),
                )

                line.price_unit_cost = seller.product_uom._compute_price(
                    price_unit, line.product_uom
                )

            else:
                # We do not have supplier defined or product defined.
                # Reset sale price to 0
                line.price_unit_cost = 0

    @api.onchange("product_id")
    def _on_change_product_id(self):
        for line in self:
            # lang = lang or self._context.get('lang')
            if not line.order_id.partner_id:
                raise UserError(
                    _(
                        "No Customer Defined !"
                        "Before choosing a product,\n select a customer in the sales form."
                    )
                )
            if not line.order_id.date_order:
                raise UserError(
                    _(
                        "No Date Order Defined"
                        "Before choosing a product,\n select a date order in the sales form."
                    )
                )
            warning = {}
            uom_uom_obj = self.env["uom.uom"]
            partner_obj = self.env["res.partner"]
            product_obj = self.env["product.product"]
            supplier_id = line.supplier_id
            params = self._context.get("params")

            if line.order_id.partner_id:
                lang = line.order_id.partner_id.lang

            #
            # if not line.product_id:
            #     return {'value': {
            #         'product_uos_qty': qty},
            #             'domain': {'uom_uom': [],
            #                        'product_uos': []}}
            if not line.order_id.date_order:
                line.order_id.date_order = time.strftime(DF)

            result = {}
            warning_msgs = ""
            product_obj = line.product_id

            uom2 = False
            uom = line.product_uom
            if uom:
                uom2 = uom
                if product_obj.uom_id.category_id.id != uom2.category_id.id:
                    uom = False
            if product_obj.uom_po_id:
                uos2 = line.product_id.uom_po_id
                if product_obj.uom_po_id.category_id.id != uos2.category_id.id:
                    line.product_id.uom_po_id = False
            else:
                line.product_id.uom_po_id = False
            afp = self.env["account.fiscal.position"]
            fpos = (
                line.order_id.fiscal_position_id
                and afp.browse(line.order_id.fiscal_position_id.id)
                or False
            )

            # update_tax is True if product_id has triggerred the onchange method.
            update_tax = self.product_id == self._origin.product_id
            if update_tax and fpos:
                line.tax_id = fpos.map_tax(product_obj.taxes_id)

            # flag is False on product_id change and True on product_uom_qty change
            flag = line.product_id != line._origin.product_id
            if not flag and line.product_id:
                line.name = line.product_id.name_get()[0][1]
                if product_obj.description_sale:
                    line.name += "\n" + product_obj.description_sale
            domain = {}
            if (not uom) and (not line.product_id.uom_po_id):
                line.product_uom = product_obj.uom_id.id
                if product_obj.uom_po_id:
                    result["product_uos"] = product_obj.uom_po_id.id
                    result["product_uos_qty"] = line.product_uom_qty
                    uos_category_id = product_obj.uom_po_id.category_id.id
                else:
                    result["product_uos"] = False
                    result["product_uos_qty"] = line.product_uom_qty
                    uos_category_id = False
                domain = {
                    "uom_uom": [
                        ("category_id", "=", product_obj.uom_id.category_id.id)
                    ],
                    "product_uos": [("category_id", "=", uos_category_id)],
                }
            elif line.product_id.uom_po_id and not uom:
                line.product_uom = product_obj.uom_id and product_obj.uom_id.id
                result["uom_uom_qty"] = qty_uos / product_obj.uos_coeff
            elif uom:
                default_uom = product_obj.uom_id and product_obj.uom_id.id
                q = uom_uom_obj._compute_quantity(
                    line.product_uom_qty, uom, default_uom
                )
                if product_obj.uom_po_id:
                    result["product_uos"] = product_obj.uom_po_id.id
                    result["product_uos_qty"] = line.product_uom_qty
                else:
                    result["product_uos"] = False
                    result["product_uos_qty"] = line.product_uom_qty

            if not uom2:
                uom2 = product_obj.uom_id

            if not line.pricelist_item_id:
                warn_msg = _(
                    "You have to select a pricelist or a customer in the sales form !\n"
                    "Please set one before choosing a product."
                )
                warning_msgs += _("No Pricelist ! : ") + warn_msg + "\n\n"
            else:
                price = line.pricelist_item_id._compute_price(
                    line.product_id,
                    line.product_uom_qty or 1.0,
                    line.product_uom,
                    line.start_date,
                )
                if price == 0:
                    price = line.product_id.list_price
                sale_currency_id = line.order_id.currency_id

                if price is False:
                    warn_msg = _(
                        "Cannot find a pricelist line matching this product and quantity.\n"
                        "You have to change either the product, the quantity or the pricelist."
                    )

                    # warning_msgs += _("No valid pricelist line found ! :") + warn_msg +"\n\n"
                else:
                    line.price_unit = price

                if supplier_id:
                    cost_price, currency_cost_id = self.show_cost_price(
                        result,
                        line.product_id,
                        line.product_uom_qty,
                        line.order_id.partner_id,
                        uom,
                        line.start_date,
                        supplier_id,
                        params,
                        line.pricelist_item_id,
                    )
                    if sale_currency_id != currency_cost_id:
                        line.price_unit_cost = currency_cost_id._convert(
                            cost_price,
                            sale_currency_id,
                            line.order_id.company_id,
                            line.start_date,
                            round=False,
                        )
                    else:
                        line.price_unit_cost = cost_price

                else:
                    cost_currency_id = False

    def get_supplierinfo(self, product_id, supplier_id):
        product_id = product_id.product_tmpl_id
        suppinfo_obj = self.env["product.supplierinfo"]
        suppinfo_ids = suppinfo_obj.search(
            [
                ("product_tmpl_id", "=", product_id.id),
                ("partner_id", "=", supplier_id.id),
            ]
        )
        if len(suppinfo_ids) == 1:
            return suppinfo_ids.currency_cost_id
        elif len(suppinfo_ids) > 1:
            raise UserError(
                _(
                    "Warning!"
                    "More that one price option for this product and supplier."
                )
            )
        return None

    def show_cost_price(
        self,
        result,
        product,
        qty,
        partner_id,
        uom,
        date_order,
        supplier_id,
        params,
        pricelist,
        context=None,
    ):
        product_id = product.product_tmpl_id
        suppinfo_obj = self.env["product.supplierinfo"]
        suppinfo_ids = suppinfo_obj.search(
            [
                ("product_tmpl_id", "=", product_id.id),
                ("partner_id", "=", supplier_id.id),
            ]
        )

        cp_ids = []
        pl_obj = self.env["product.pricelist"]
        if suppinfo_ids:
            currency_id = suppinfo_ids.currency_cost_id
            cost_price = suppinfo_ids.price  # TODO consider min_qtyfield

            #            cost_currency_id = sup.currency_id
            #            sale_currency_id = pl_obj.browse(pricelist).currency_id.id
            #            if sale_currency_id != cost_currency_id:
            #                cr_obj = self.env['res.currency')
            #                cost_price = cr_obj.compute(cost_currency_id,
            #                                            sale_currency_id, cost_price,
            #                                            round=False)
            return cost_price, currency_id

        return 0.0, pricelist.currency_id

    @api.onchange("category_id")
    def _on_change_category(self):
        for line in self:
            if line.category_id and len(line.category_id.name):
                line.category = line.category_id.name.lower()
            else:
                line.category = False

    def go_to_order(self):
        for obj in self:
            # obj = self.browse(ids[0])
            return {
                "type": "ir.actions.act_window",
                "view_type": "form",
                "view_mode": "form",
                "res_model": "sale.order",
                "res_id": obj.order_id.id,
            }

    def get_margin_days(self, params):
        """
        The number of days of the service countable for apply a per day margin
        """
        days = 0
        if params.get("supplement_ids"):
            ini = datetime.strptime(params["start_date"], DF)
            end = datetime.strptime(params["end_date"], DF)
            days = (end - ini).days + 1
        return days

    def print_voucher(self):
        for reservation in self:
            return self.env.ref("travel_core.travel_voucher_report_id").report_action(
                reservation
            )

    @api.onchange("travel_type")
    def _compute_quantity(self):
        # Override this in business apps
        return

    @api.onchange(
        "tl_detail_ids",
        "tl_detail_ids.quantity",
        "tl_detail_ids.total_price",
        "tl_details_ids.cost_price",
    )
    def _compute_so_line_total_from_tl_details(self):
        """
        Computes and updates various aggregate fields on the sale order line based on related travel line details.

        For each sale order line:
            - Skips computation if the details tab is not visible.
            - Aggregates the total price, total cost, number of adults, children, infants, and total quantity from related `tl_detail_ids`.
            - Updates the sale order line fields: `price_unit`, `price_unit_cost`, `adults`, `children`, `infants`, `paxs`, and `product_uom_qty` with the computed values.
            - If multiple different products are present in the details, sets the order line's description to a predefined combo product name or a default string.

        This method is intended to keep the sale order line's summary fields in sync with its associated travel line details.
        """
        for order in self:
            if not order.details_tab_visible:
                continue
            total_price = 0.0
            total_cost = 0.0
            adults = 0
            children = 0
            infants = 0
            paxs = 0
            quantity = 0

            product_ids = set()
            for detail in order.tl_detail_ids:
                adults += detail.adults
                children += detail.children
                infants += detail.infants
                paxs += detail.quantity

                total_cost += detail.total_cost
                total_price += detail.total_price
                quantity += detail.quantity

                if detail.product_id:
                    product_ids.add(detail.product_id.id)

            order.price_unit = total_price
            order.price_unit_cost = total_cost
            order.adults = adults
            order.children = children
            order.infants = infants
            order.paxs = paxs
            order.product_uom_qty = quantity

            if len(product_ids) > 1:
                combo_product = self.env.ref(
                    "travel_core.product_combo_travel_product", raise_if_not_found=False
                )
                if combo_product:
                    order.description = combo_product.name
                else:
                    order.description = "Combo Product"
