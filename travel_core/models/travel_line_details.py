from odoo import _, api, fields, models


class TravelLineDetails(models.Model):
    _name = "travel.line.details"
    _description = "Travel line details"
    _order = "sequence, id"

    order_line_id = fields.Many2one("sale.order.line", "Order Line")
    travel_type = fields.Selection(string="Travel product type", selection=[])
    calculation_method = fields.Selection(
        string="Calculation method", selection=[("passengers", "Per passenger")]
    )
    product_template_id = fields.Many2one(
        "product.template", domain="[('travel_type', '=?', travel_type)]"
    )
    product_id = fields.Many2one(
        "product.product", domain="[('travel_type', '=?', travel_type)]"
    )
    sequence = fields.Integer("Sequence", default=10)
    name = fields.Char("Name")
    traveler_name = fields.Char("Traveler Name")

    currency_id = fields.Many2one(
        "res.currency", related="order_line_id.currency_id", string="Currency"
    )

    adults = fields.Integer(string="Adults", default=0)
    children = fields.Integer(string="Children", default=0)
    infants = fields.Integer(string="Infants", default=0)

    quantity = fields.Float("Quantity")
    price_unit = fields.Float("Unit Price")
    price_unit_child = fields.Float("Child Price")
    price_unit_infant = fields.Float("Infant Price")
    cost_unit = fields.Float("Unit Cost")
    cost_unit_child = fields.Float("Child cost")
    cost_unit_infant = fields.Float("Infant cost")
    total_cost = fields.Float("Total Cost")
    total_price = fields.Float("Total Price")

    start_place = fields.Many2one("travel_core.destination", "From")
    end_place = fields.Many2one("travel_core.destination", "To")
    airline_id = fields.Many2one(related="flight_id.airline_id")

    flight_id = fields.Many2one(
        comodel_name="travel_core.flight",
        string="Flight",
        ondelete="restrict",
    )

    infants_visible = fields.Boolean(
        string="Infants Visibility",
        compute="_compute_infants_visibility",
        default=False,
        store=True,
    )

    @api.onchange("flight_id")
    def _onchange_flight_id(self):
        for record in self:
            if record.flight_id:
                record.airline_id = record.flight_id.airline_id
                record.product_id = (
                    record.flight_id.product_id if record.flight_id else None
                )
                record.start_place = record.flight_id.origin
                record.end_place = record.flight_id.destination

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for record in self:
            if record.product_id:
                record.price_unit = record.product_id.list_price
                record.price_unit_child = record.product_id.list_price_child
                record.price_unit_infant = record.product_id.list_price_infant
                record.cost_unit = record.product_id.standard_price
                record.cost_unit_child = record.product_id.standard_price_child
                record.cost_unit_infant = record.product_id.standard_price_infant

    @api.onchange(
        "adults",
        "children",
        "infants",
        "product_id",
        "price_unit",
        "price_unit_child",
        "price_unit_infant",
        "cost_unit",
        "cost_unit_child",
        "cost_unit_infant",
    )
    def _compute_total_travel_line_details(self):
        for record in self:
            record.quantity = record.adults + record.children + record.infants
            record.total_cost = (
                record.cost_unit * record.adults
                + record.cost_unit_child * record.children
                + record.cost_unit_infant * record.infants
            )
            record.total_price = (
                record.price_unit * record.adults
                + record.price_unit_child * record.children
                + record.price_unit_infant * record.infants
            )

    @api.onchange("travel_type")
    def _compute_infants_visibility(self):
        for record in self:
            record.infants_visible = False
            record.product_id = False
            record.product_template_id = False

    @api.onchange("product_template_id")
    def _onchange_product_template_id(self):
        if self.product_template_id:
            products = self.env["product.product"].search(
                [("product_tmpl_id", "=", self.product_template_id.id)]
            )

            # Update domain
            domain = [("product_tmpl_id", "=", self.product_template_id.id)]

            # Auto-set product_id if there's only one variant
            if len(products) == 1:
                self.product_id = products[0]

            return {"domain": {"product_id": domain}}
        else:
            return {"domain": {"product_id": []}}
