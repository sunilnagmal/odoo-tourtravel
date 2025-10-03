import datetime as dt

from odoo import _, api, fields, models

from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF


class Allotment(models.Model):
    _name = "travel_hotel.allotment"
    _description = "Allotment"

    start_date = fields.Date("Start date")
    end_date = fields.Date("End date")

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        required=True,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Room",
        required=True,
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
    )
    supplier_id = fields.Many2one(
        comodel_name="res.partner", string="Travel Supplier", required=True
    )

    suppinfo_id = fields.Many2one("product.supplierinfo", "Supplier")

    allotment = fields.Integer("Allotment")
    release = fields.Integer("Release")

    def create(self, values):
        res = super().create(values)
        self.update_daily_allotment()
        return res

    def write(self, values):
        for allotment in self:
            res = super().write(values)
            allotment.update_daily_allotment()
        return res

    def unlink(self):
        daily_allotment = self.env["allotment.state"]
        for allotment in self:
            daily_allotment_ids = daily_allotment.search(
                [
                    ("product_id", "=", allotment.product_id.id),
                    ("supplier_id", "=", allotment.supplier_id.id),
                    ("day", ">=", allotment.start_date),
                    ("day", "<=", allotment.end_date),
                ]
            )
            daily_allotment.unlink(daily_allotment_ids)

        res = super().unlink()
        return res

    def update_daily_allotment(self):
        daily_allotment_obj = self.env["allotment.state"]
        order_line_obj = self.env["sale.order.line"]

        for allotment in self:
            vals = {
                "product_id": allotment.product_id.id,
                "supplier_id": allotment.supplier_id.id,
                "allotment": allotment.allotment,
            }
            current_date = allotment.start_date
            end_date = allotment.end_date
            delta = dt.timedelta(days=1)
            while current_date <= end_date:
                vals.update({"day": current_date})
                daily_allotment_ids = daily_allotment_obj.search(
                    [
                        ("day", "=", vals["day"]),
                        ("product_id", "=", vals["product_id"]),
                        ("supplier_id", "=", vals["supplier_id"]),
                    ]
                )
                if len(daily_allotment_ids) == 0:
                    daily_allotment_obj.create(vals)
                else:
                    daily_allotment_ids.write(vals)
                current_date += delta

            order_line_ids = order_line_obj.search(
                [("product_id", "=", allotment.product_id.id)]
            )
            order_line_ids.write({})

        return True

    _order = "start_date asc"


class allotment_state(models.Model):
    _name = "allotment.state"
    _description = "Allotment state"

    def _availability(self):
        availability = 0
        prod_allotment = self.env["travel_hotel.allotment"]
        for obj in self:
            allotment_ids = prod_allotment.search(
                [
                    ("product_id", "=", obj.product_id.id),
                    ("start_date", "<=", obj.day),
                    ("end_date", ">=", obj.day),
                ]
            )
            release = 0
            for allotment in allotment_ids:
                release += allotment.release

            difference = (
                obj.day
                - dt.datetime.today()
                .replace(hour=0, minute=0, second=0, microsecond=0)
                .date()
            ).days
            if difference <= release:
                availability = 0
            else:
                availability = max(0, obj.allotment - obj.reserved)

            obj.available = availability

    def _reservations(self):
        order_line_model = self.env["sale.order.line"]

        for allotment in self:
            total_reserved = 0
            order_line_ids = order_line_model.search(
                [
                    ("product_id", "=", allotment.product_id.id),
                    ("start_date", "<=", allotment.day),
                    ("end_date", ">", allotment.day),
                ]
            )
            for line in order_line_ids:
                if line.state == "sale":
                    total_reserved += line.number_of_rooms

            allotment.reserved = total_reserved

    def _get_allotment_from_order(self, ids):
        res = []
        order_lines = self.env["sale.order.line"].browse(ids)
        allotment_model = self.env["allotment.state"]
        hotel_model = self.env["product.hotel"]
        for ol in order_lines:
            if ol.category_id.name == "Hotel":
                hotel_ids = hotel_model.search([("product_id", "=", ol.product_id.id)])
                if len(hotel_ids) > 0:
                    allotment_ids = allotment_model.search(
                        [
                            ("hotel_id", "=", hotel_ids[0]),
                            ("day", ">=", ol.start_date),
                            ("day", "<", ol.end_date),
                        ]
                    )
                    res.extend(allotment_ids)

        return list(set(res))

    day = fields.Date("Day")
    product_id = fields.Many2one("product.product", "Room")
    product_tmpl_id = fields.Many2one(
        "product.template", "Hotel", related="product_id.product_tmpl_id"
    )
    supplier_id = fields.Many2one("res.partner", "Supplier")
    allotment = fields.Integer("Allotment")
    reserved = fields.Integer("Reserved", compute=_reservations)
    # TODO store = {'sale.order.line': (_get_allotment_from_order, [], 10)}),
    available = fields.Integer("Available", compute=_availability)

    _order = "day asc"
