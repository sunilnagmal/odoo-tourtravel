import time
import datetime as dt
from xml.etree import ElementTree as ET

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, func


class sale_order(models.Model):
    _inherit = "sale.order"

    def _get_lead_name(self):
        result = {}

        for obj in self:
            result[obj.id] = False
            if obj.pax_ids:
                min = obj.pax_ids[0]
                for pax in obj.pax_ids:
                    if pax.id < min.id:
                        min = pax
                result[obj.id] = min.name

        return result

    def _lead_name_search(self):
        # name = args[0][2]
        values = []
        # ids = self.search([])
        for obj in self:
            if obj.pax_ids and name.lower() in obj.pax_ids[0].name.lower():
                values.append(obj.id)
            result = [("id", "in", values)]
            obj.lead_name = result

    def _get_total_paxs(self):
        result = {}
        uids = [res[0] for res in self.env.cr.fetchall()]
        # for obj in self.browse(self.env.context['active_ids']):
        for obj in self.browse(uids):
            result[obj.id] = False
            result[obj.id] = len(obj.pax_ids)
            obj.total_paxs = result

    state = fields.Selection(
        selection_add=[
            ("draft",),
            ("request", "Request"),
            ("requested", "Requested"),
        ],
        default="draft",
    )

    start_date = fields.Date(
        "Start Date",
        required=True,
        readonly=True,
        index=True,
        states={"draft": [("readonly", False)], "sent": [("readonly", False)]},
        default=dt.date.today(),
    )
    end_date = fields.Date(
        "End Date",
        required=True,
        readonly=True,
        index=True,
        states={"draft": [("readonly", False)], "sent": [("readonly", False)]},
        default=dt.date.today() + dt.timedelta(days=1),
    )

    flight_in = fields.Many2one("travel_core.flight", string="Flight in")
    flight_out = fields.Many2one("travel_core.flight", string="Flight out")
    order_line = fields.One2many(
        "sale.order.line",
        "order_id",
        "Order Lines",
        readonly=True,
        states={
            "draft": [("readonly", False)],
            "sent": [("readonly", False)],
            "manual": [("readonly", False)],
        },
    )

    pax_ids = fields.One2many(
        string="Paxs",
        comodel_name="travel_core.pax",
        inverse_name="order_id",
    )
    total_paxs = fields.Integer("Total paxs", compute=_get_total_paxs, store=True)
    lead_name = fields.Char("Lead Name", compute=_get_lead_name)
    # TODO fnct_search=_lead_name_search)
    # TODO: ref for earchable fields https://www.odoo.com/sl_SI/forum/help-1/calculated-fields-in-search-filter-possible-118501

    supplier_id = fields.Many2one("res.partner", "Supplier")

    @api.model_create_multi
    def create(self, vals_list):
        res = super(sale_order, self).create(vals_list)
        res.check_dates()
        return res

    def write(self, vals):
        res = super(sale_order, self).write(vals)
        res.check_dates()
        return res

    traveler_name = fields.Char(
        string="Traveler Name",
    )

    def _compute_reservation_number(self):
        for order in self:
            reservation_numbers = []
            for pax in order.pax_ids:
                if pax.reservation_number:
                    reservation_numbers.append(pax.reservation_number)

            if len(reservation_numbers) >= 1:
                order.reservation_number = " - ".join(reservation_numbers)
            else:
                order.reservation_number = ""

    @api.model
    def _search_reservation_number(self, operator, value):
        search_string = "%{}%".format(value)
        pax_ids = self.env["travel_core.pax"].search(
            [("reservation_number", operator, search_string)]
        )
        return [("id", "in", pax_ids.order_id.ids)]

    reservation_number = fields.Char(
        string="Reservation Number",
        compute=_compute_reservation_number,
        search=_search_reservation_number,
    )

    _order = "create_date desc"

    def write(self, vals):
        res = super(sale_order, self).write(vals)
        if vals.get("state") in ["sale", "done", "cancel"]:
            for s in self:
                for line in s.order_line:
                    line.write({"state": vals["state"]})
        return res

    def to_confirm(self):
        for order in self:
            order.write({"state": "manual"})

    def to_cancel(self):
        for order in self:
            order.write({"state": "cancel"})

    def check_dates(self):
        for order in self:
            if (
                order.start_date
                and order.end_date
                and order.start_date > order.end_date
            ):
                raise UserError("End Date should be after Start Date\n")

    def _action_cancel(self):
        for order in self:
            super(sale_order, order)._action_cancel()
            for invoice in order.invoice_ids:
                invoice.button_draft()
                invoice._delete_invoice_lines()
                supp_invoices = self.env["account.move"].search(
                    [
                        ("invoice_origin", "=", invoice.invoice_origin),
                        ("move_type", "=", "in_invoice"),
                    ]
                )
                for supp_inv in supp_invoices:
                    supp_inv.button_draft()
                    supp_inv._delete_invoice_lines()

    def _create_invoices(self, grouped=False, final=False, date=None):
        moves = super(sale_order, self)._create_invoices(
            grouped=grouped, final=final, date=date
        )
        for move in moves:
            move.write(
                {
                    "start_date": self.start_date,
                    "end_date": self.end_date,
                    "reservation_number": self.reservation_number,
                    "traveler_name": self.traveler_name,
                    "supplier_id": self.supplier_id,
                }
            )
        return moves
