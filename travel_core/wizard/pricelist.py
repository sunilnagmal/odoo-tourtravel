from odoo import _, api, fields, models


import time
import xlwt
import base64

FIELD_TYPES = {"date": 1, "Many2one": 2, "float": 3, "integer": 4}
CORE_FIELDS = [
    (1, "start_date", "Start Date"),
    (1, "end_date", "End Date"),
    (3, "price", "Price"),
    (3, "child", "Child"),
]


class customer_price(models.TransientModel):
    _name = "customer.price"
    _description = "Customer price"

    start_date = fields.Date("Start date")
    end_date = fields.Date("End date")
    file_price = fields.Binary("File")

    def export_prices(self, ids):
        wb = xlwt.Workbook()

        partner_obj = self.env["res.partner"]
        partner = partner_obj.browse(self._context["active_id"])
        pricelist = partner.property_product_pricelist

        category_obj = self.env["product.category"]
        category_ids = category_obj.search([])
        for categ in category_obj.browse(category_ids):
            name = categ.name
            fields = self.get_category_price_fields(name.lower())
            if fields:
                ws = wb.add_sheet(name, cell_overwrite_ok=True)
                self.write_prices(ws, fields, categ, pricelist)
        wb.save("/tmp/prices.xls")
        f = open("/tmp/prices.xls", "rb")
        obj = self.browse(ids[0])
        obj.write({"file_price": base64.b64encode(f.read())})
        return {
            "name": "Export Prices",
            "type": "ir.actions.act_window",
            "view_type": "form",
            "view_mode": "form",
            "res_model": "customer.price",
            "res_id": obj.id,
            "target": "new",
        }

    # TODO: sort fields just for first index
    def get_category_price_fields(self, category):
        import importlib

        try:
            categ = importlib.import_module(
                "openerp.addons.travel_" + category + "." + category
            )
            category_fields = [x for x in CORE_FIELDS]
            if hasattr(categ, "product_rate"):
                category_fields += [
                    (FIELD_TYPES[v._type], k, v.string)
                    for k, v in list(categ.product_rate._columns.items())
                ]
                category_fields.Sort()
            return category_fields
        except Exception:
            return []

    def write_prices(self, ws, fields, categ, pricelist):
        product_obj = self.env["product.product"]
        product_ids = product_obj.search([("categ_id", "=", categ.id)])
        ws.write(0, 0, "Product")
        x, y = 0, 1
        for f in fields:
            ws.write(x, y, f[2])
            y += 1
        x = 1
        for prod in product_obj.browse(product_ids):
            y = 0
            ws.write(x, y, prod.name)
            suppinfo = prod.seller_info_id
            if suppinfo:
                for pr in suppinfo.pricelist_ids:
                    y = 1
                    for f in fields:
                        if f[0] == 2:
                            value = getattr(pr, f[1]).name
                        elif f[0] == 3:
                            value = self.get_customer_price(
                                pricelist, prod, suppinfo, getattr(pr, f[1])
                            )
                        else:
                            value = getattr(pr, f[1])
                        ws.write(x, y, value)
                        y += 1
                    x += 1

    # TODO: check currency
    def get_customer_price(self, pricelist, prod, suppinfo, value):
        for rule in pricelist.item_ids:
            if rule.categ_id and rule.categ_id.id != prod.categ_id.id:
                continue
            if rule.product_id and rule.product_id.id != prod.id:
                continue
            if rule.supplier_id and rule.supplier_id.id != suppinfo.name.id:
                continue
            value += rule.margin_per_pax or 0.0
            value = value * (1.0 + (rule.price_discount or 0.0))
            break
        return value
