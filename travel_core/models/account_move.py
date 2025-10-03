import logging
import datetime

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = "account.move"

    is_travel_invoice = fields.Boolean(string="Is Travel invoice", default=False)

    start_date = fields.Date(string="Start Date")

    end_date = fields.Date(string="End Date")

    reservation_number = fields.Char("Reservation")

    traveler_name = fields.Char(string="Guest Name")

    supplier_id = fields.Many2one("res.partner", "Supplier")

    @api.model
    def _search_supplier(self, operator, values):
        pass
        return [("id", "in", False)]

    @api.model
    def _search_traveler_name(self, operator, operand):
        move_type = self.env.context.get("default_move_type")
        invoices_id = []
        # Customer invoices
        paxes = self.env["travel_core.pax"].search([("name", operator, operand)])
        if move_type == "out_invoice":
            for pax in paxes:
                invoices_id.extend(pax.order_id.invoice_ids.ids)
        elif move_type == "in_invoice":
            # Vendor bills
            for pax in paxes:
                invoices_id.extend(
                    self.env["account.move"]
                    .search(
                        [
                            ("move_type", "=", "in_invoice"),
                            ("invoice_origin", "=", pax.order_id.name),
                        ]
                    )
                    .ids
                )

        return [("id", "in", invoices_id)]

    @api.model_create_multi
    def create(self, vals_list):
        inv_ids = super(AccountMove, self).create(vals_list)

        for inv_id in inv_ids:
            if inv_id.move_type == "out_invoice" and inv_id.is_travel_invoice:
                self.generate_supplier_invoices(inv_id)
        return inv_ids

    def get_purchase_journal(self, company_id):
        journal = self.env["account.journal"]
        jids = journal.search(
            [("type", "=", "purchase"), ("company_id", "=", company_id)]
        )
        return jids and jids[0] or False

    def update_lines_by_supplier(self, lines_by_supplier, supplier, d):
        if supplier in lines_by_supplier:
            lines_by_supplier[supplier].append(d)
        else:
            lines_by_supplier[supplier] = [d]
        return lines_by_supplier

    def group_by_supplier(self):
        """
        Group invoice lines by supplier using sale_line_ids relation.
        Returns dict {supplier: [{'invoice_line': line, 'sale_line': order_line}]}
        """
        self.ensure_one()
        lines_by_supplier = {}

        for line in self.invoice_line_ids:
            # Get related sale order lines through direct relation
            sale_lines = line.sale_line_ids

            if not sale_lines:
                continue

            order_line = sale_lines[0]  # Take first related sale line
            supplier = getattr(order_line, "supplier_id", False)
            if not supplier:
                continue

            line_data = {"invoice_line": line, "sale_line": order_line}

            if supplier in lines_by_supplier:
                lines_by_supplier[supplier].append(line_data)
            else:
                lines_by_supplier[supplier] = [line_data]

        return lines_by_supplier

    def _delete_invoice_lines(self):
        for invoice in self:
            for line in invoice.line_ids:
                if line.exists():
                    line.unlink()

    def generate_supplier_invoices(self, inv_ids):
        # TODO #320
        return
        for invoice in inv_ids:
            invoice.action_post()
            company_id = invoice.company_id
            journal_id = self.get_purchase_journal(company_id.id)
            vals = {
                "move_type": "in_invoice",
                "state": "draft",
                "journal_id": journal_id.id if journal_id else None,
                "invoice_date": invoice.invoice_date,
                "user_id": invoice.user_id.id,
                "company_id": company_id.id,
                "invoice_origin": invoice.invoice_origin,
                "narration": "Generated from customer invoice "
                + str(invoice.invoice_origin),
            }

            lines_by_supplier = invoice.group_by_supplier()
            for supplier, lines in list(lines_by_supplier.items()):
                if supplier is not None:
                    reference_sale_line = lines[0]["sale_line"]
                    currency_id = reference_sale_line.currency_cost_id
                    data = vals.copy()
                    data.update(
                        {
                            "partner_id": supplier.id,
                            # 'account_id': supplier.property_account_payable.id,
                            "currency_id": currency_id.id,
                            "invoice_line_ids": [],
                        }
                    )
                    for line_info in lines:
                        sl = line_info["sale_line"]
                        invoice_line = line_info["invoice_line"]
                        cost_price = self.get_cost_price(sl, currency_id)
                        line_vals = {
                            "name": invoice_line.product_id.name,
                            "ref": invoice_line.move_id.name,
                            "product_id": invoice_line.product_id.id,
                            # 'account_id': invoice_line.product_id.categ_id.property_account_expense_categ.id,
                            "quantity": invoice_line.quantity,
                            "discount": invoice_line.discount,
                            "price_unit": cost_price,
                        }
                        data["invoice_line_ids"].append((0, 0, line_vals))
                        new_inv_id = self.create(data)
                        new_inv_id.action_post()

    def get_cost_price(self, line, currency_id):
        price = line.price_unit_cost
        order_currency = line.order_id.pricelist_id.currency_id
        if order_currency.id != currency_id.id:
            price = order_currency._convert(
                price, currency_id, line.order_id.company_id, datetime.date.today()
            )
        return price

    # FIXME #177 this code prevent from installing demo data
    # @api.constrains("state", "price_unit")
    # def _check_price_unit(self):
    #     if self.env.context.get("test_mode"):
    #         return
    #     for move in self:
    #         if move.state != "draft":
    #             for invoice_line in move.line_ids:
    #                 if invoice_line.price_unit <= 0.0:
    #                     raise ValidationError("Price unit must be over 0.")
