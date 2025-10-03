#
import xlrd
import base64
import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

BASE_DATE = 693594


class import_margins(models.TransientModel):
    _name = "import.margins"
    _description = "Import margins"

    file = fields.Binary("File")
    result = fields.Text("Result")

    def import_file(self):
        # obj = self.browse(ids[0])
        for obj in self:
            if obj.file:
                data = base64.b64decode(obj.file)
                # try:
                msg = ""
                document = xlrd.open_workbook(file_contents=data)
                sheet = document.sheets()[-1]

                season_name = sheet.name

                product = self.env["product.product"]
                pricelist = self.env["product.pricelist"]
                rule = self.env["product.pricelist.item"]
                currency = self.env["res.currency"]
                customer = self.env["res.partner"]

                pub_pricelist_id = pricelist.search(
                    [("name", "=", "Public Pricelist")]
                )[0]

                gbp_id = currency.search([("name", "=", "GBP")])[0]

                date_start = self.get_date(sheet.cell_value(0, 3))
                date_end = self.get_date(sheet.cell_value(0, 5))

                first_col = 3

                for col in range(first_col, sheet.ncols):
                    customer_name = sheet.cell_value(1, col).upper()
                    customer_ids = customer.search([("name", "=", customer_name)])
                    if customer_ids:
                        customer_obj = customer_ids[0]
                    else:
                        if first_col == col:
                            msg += (
                                "Customer: "
                                + customer_name
                                + " not found in the system \n"
                            )
                        continue

                    curr_str = sheet.cell_value(2, col)
                    if curr_str:
                        curr_id = currency.search([("name", "=", curr_str.upper())])[0]
                    else:
                        curr_id = gbp_id
                    xrate = sheet.cell_value(3, col)
                    if not xrate:
                        xrate = 1.0

                    pricelist_obj = customer_obj.property_product_pricelist
                    pricelist_id = customer_obj.property_product_pricelist.id
                    pricelist_name = customer_obj.property_product_pricelist.name
                    if pricelist_name == "Public Pricelist":
                        pricelist_rec = pricelist.create(
                            {
                                "name": customer_name + " Pricelist",
                                "currency_id": curr_id.id,
                                "type": "sale",
                            }
                        )
                        pricelist_id = pricelist_rec.id

                    customer_obj.write({"property_product_pricelist": pricelist_id})

                    for row in range(4, sheet.nrows):
                        hotel_name = sheet.cell_value(row, 1).upper()
                        product_ids = product.search([("name", "=", hotel_name)])
                        if not product_ids:
                            if first_col == col:
                                msg += (
                                    "Hotel: "
                                    + hotel_name
                                    + " not found in the system \n"
                                )
                        elif len(product_ids) > 1:
                            if first_col == col:
                                msg += (
                                    "Hotel: "
                                    + hotel_name
                                    + " not unique in the system \n"
                                )
                        else:
                            raw_margin = sheet.cell_value(row, col)
                            if isinstance(raw_margin, float):
                                try:
                                    margin = raw_margin * xrate
                                except Exception:
                                    pass
                                rule_ids = rule.search(
                                    [("product_id", "=", product_ids[0])]
                                )
                                if rule_ids:
                                    rule_ids.write({"margin_per_pax": margin})
                                else:
                                    rule.create(
                                        {
                                            "product_id": product_ids[0],
                                            "base": -2,
                                            "margin_per_pax": margin,
                                        }
                                    )

                if msg == "":
                    msg += "\n ================== \nMargins successfully uploaded. \n"
                else:
                    msg += "\n ================== \nCheck that names are properly typed or present in the system. \n"

                msg += "Press cancel to close"

                obj.write({"result": msg})
                return {
                    "name": "Import Margins",
                    "type": "ir.actions.act_window",
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "import.margins",
                    "res_id": obj.id,
                    "target": "new",
                }
            else:
                raise UserError("You must select a file.")

    def get_date(self, value):
        try:
            d = BASE_DATE + int(value)
            return datetime.date.fromordinal(d)
        except Exception:
            return datetime.date(2017, 1, 1)

    def get_float(self, value):
        try:
            return float(value)
        except Exception:
            return 0.0
