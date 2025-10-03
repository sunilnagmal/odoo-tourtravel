import odoo
from odoo import fields, models, api, SUPERUSER_ID
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_partner_if_portal(self):
        # In portal context, default to the current user's partner. Otherwise, keep standard behavior.
        if self.env.context.get("portal"):
            return self.env.user.partner_id.id
        return False

    partner_id = fields.Many2one(default=_get_partner_if_portal)

    @api.model_create_multi
    def create(self, vals_list):
        # Ensure portal-created orders are assigned to the current partner and a salesperson, without double-creating
        if self.env.context.get("portal"):
            partner_id = self.env.user.partner_id.id
            salesperson = self.find_salesperson(partner_id)
            for vals in vals_list:
                vals.setdefault("partner_id", partner_id)
                if salesperson:
                    vals.setdefault("user_id", salesperson.id)
            orders = super(SaleOrder, self).create(vals_list)
            orders.message_subscribe([partner_id])
            return orders
        return super(SaleOrder, self).create(vals_list)

    @api.model
    def find_salesperson(self, partner_id):
        # Reuse last salesperson for this partner if any; otherwise pick a non-superuser
        order = self.search([("partner_id", "=", partner_id)], order="id desc", limit=1)
        if order and order.user_id:
            return order.user_id
        user = self.env["res.users"].sudo().search([("id", "!=", SUPERUSER_ID)], limit=1)
        return user or self.env["res.users"].browse(SUPERUSER_ID)

    def action_button_confirm(self):
        # Confirm as the assigned salesperson when invoked from the portal
        if self.env.context.get("portal"):
            res = None
            for order in self:
                res = super(SaleOrder, order.with_user(order.user_id.id)).action_button_confirm()
            return res
        return super(SaleOrder, self).action_button_confirm()
