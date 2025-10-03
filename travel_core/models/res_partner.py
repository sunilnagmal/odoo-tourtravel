import datetime as dt

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


class res_partner(models.Model):
    _name = "res.partner"
    _inherit = "res.partner"

    def _get_reservations(self):
        result = {}
        order_line = self.env["sale.order.line"]
        for partner in self:
            partner.reservation_ids = False
            result[partner.id] = []
            domain = [("start_date", ">=", dt.datetime.today())]
            if partner.customer_rank >= 1:
                domain.append(("order_partner_id", "=", partner.id))
            elif partner.supplier_rank >= 1:
                domain.append(("order_partner_id", "=", partner.id))
            else:
                continue
            order_line_ids = order_line.search(domain)
            if order_line_ids:
                result[partner.id] = order_line_ids
                partner.reservation_ids = result

    reservation_ids = fields.Many2many(
        "sale.order.line", "Reservations", compute=_get_reservations
    )
    pax = fields.Boolean("Pax")
    # TODO: poner el campo pax tambien en el formulario de partner

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self._context.get("supplier"):
                vals["supplier_rank"] = 1
        return super(res_partner, self).create(vals_list)
