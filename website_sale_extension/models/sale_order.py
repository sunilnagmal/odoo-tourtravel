import odoo
from odoo import fields, models, api, SUPERUSER_ID
from odoo.http import request


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _get_partner_if_portal(self):
        uid = request.session.uid
        if self._context.get("portal"):
            return self.env["res.users"].browse(uid).partner_id.id

    partner_id = fields.Many2one(default=_get_partner_if_portal)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if self.env.context.get("portal"):
                partner_id = self.env.user.partner_id.id
                salesperson = self.sudo().find_salesperson(partner_id)
                vals["partner_id"] = partner_id
                vals["user_id"] = salesperson.id
                obj = super(SaleOrder, self.sudo().with_user(salesperson)).create(vals)
                obj.sudo().with_user(salesperson).message_subscribe([partner_id])
                # return obj
        return super(SaleOrder, self).create(vals_list)

    @api.model
    def find_salesperson(self, partner_id):
        orders = self.search([("partner_id", "=", partner_id)])
        if orders:
            return orders[0].user_id
        users = self.search([("id", "!=", SUPERUSER_ID)])
        if users:
            return users[0]
        return self.env["res.users"].browse(SUPERUSER_ID)

    def action_button_confirm(self):
        if self.env.context.get("portal"):
            for obj in self:
                res = super(
                    SaleOrder, obj.sudo().with_user(obj.user_id)
                ).action_button_confirm()
            return res
        return super(SaleOrder, self).action_button_confirm()
