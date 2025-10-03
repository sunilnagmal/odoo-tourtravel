#
import xlrd
import datetime
import base64
import json

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError


BASE_DATE = 693594


class import_hotel(models.TransientModel):
    _name = "import.hotel"
    _description = "Hotel imports"

    file = fields.Binary("File")
    result = fields.Text("Result")

    def import_file(self):
        # obj = self.browse(ids[0])
        for obj in self:
            if obj.file:
                data = base64.b64decode(obj.file)
                msg = " "
                document = xlrd.open_workbook(file_contents=data)

                for sheet in document.sheets():
                    if sheet.nrows != 0:
                        new_msg = self.import_prices_data(sheet)
                        if new_msg != "":
                            msg += new_msg + "\n"
                        else:
                            msg += new_msg

                obj.write({"result": msg})
                return {
                    "name": "Import Prices",
                    "type": "ir.actions.act_window",
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "import.hotel",
                    "res_id": obj.id,
                    "target": "new",
                }
            else:
                raise UserError("You must select a file.")

    def import_prices_data(self, sheet):
        msg = ""

        hotel = self.env["product.hotel"]
        product_product = self.env["product.product"]
        partner = self.env["res.partner"]
        product_supplierinfo = self.env["product.supplierinfo"]
        pricelist_partnerinfo = self.env["pricelist.partnerinfo"]
        option_value = self.env["product.attribute.value"]
        category = self.env["product.category"]

        head = {sheet.cell_value(0, x): x for x in range(sheet.ncols)}
        product_hotel = False
        hotel_info = ""
        supplier = False
        suppinfo_id = False
        meal_plan_id = False
        room_type_id = False
        date_from = False
        date_to = False
        child1 = False
        child2 = False
        double_value = False
        double_option = False
        simple_value = False
        simple_option = False
        triple_value = False
        triple_option = False

        for r in range(1, sheet.nrows):

            def cell(attr):
                if sheet.cell(r, head[attr]).ctype == xlrd.XL_CELL_ERROR:
                    return None
                return sheet.cell_value(r, head[attr])

            if cell("HOTEL NAME"):
                # insert additional information (room and hotel comments) of previous hotel
                if suppinfo_id:
                    product_supplierinfo.write([suppinfo_id], {"info": hotel_info})
                    hotel_info = ""

                hotel_name = cell("HOTEL NAME").strip()
                category_id = category.search([("name", "=", "Hotel")])[0]
                product_hotel = hotel.search([("name", "=", hotel_name)])
                if len(product_hotel) == 0:
                    msg += "Hotel name not found: " + hotel_name + "\n"
                    product_hotel = False
                elif len(product_hotel) > 1:
                    msg += "Ambiguous name for hotel: " + hotel_name + "\n"
                    product_hotel = False
                else:
                    product_hotel = hotel.browse(product_hotel[0])

            if cell("SUPPLIER"):
                if product_hotel:
                    suppinfo_id = None
                    supplier_name = str(cell("SUPPLIER")).strip()
                    if supplier_name != "":
                        partner_ids = partner.search([("name", "=", supplier_name)])
                        if len(partner_ids) == 0:
                            msg += "Supplier name not found: " + supplier_name + "\n"
                        elif len(partner_ids) > 1:
                            msg += (
                                "Ambiguous name for supplier: " + supplier_name + "\n"
                            )
                        else:
                            partner_id = partner_ids[0]
                            suppinfo_ids = product_supplierinfo.search(
                                [
                                    "&",
                                    ("name", "=", partner_id),
                                    (
                                        "product_tmpl_id",
                                        "=",
                                        product_hotel.product_tmpl_id.id,
                                    ),
                                ]
                            )
                            if len(suppinfo_ids) == 0:
                                svals = {
                                    "name": partner_id,
                                    "product_tmpl_id": product_hotel.product_tmpl_id.id,
                                    "min_qty": 0,
                                }
                                suppinfo_id = product_supplierinfo.create(svals)
                            else:
                                suppinfo_id = suppinfo_ids[0]

            if cell("MEAL PLAN"):
                meal_plan_id = cell("MEAL PLAN").strip()
                mp = self.get_option_value(meal_plan_id, "mp")

            if cell("ROOM CATEGORY"):
                room_type_str = cell("ROOM CATEGORY").strip()
                room_type_id = self.get_option_value(room_type_str, "rt")

            if cell("DATEBAND FROM"):
                date_from = self.get_date(cell("DATEBAND FROM"))
                double_value = False
                double_option = False
                simple_value = False
                simple_option = False
                triple_value = False
                triple_option = False

            if cell("DATEBAND TO"):
                date_to = self.get_date(cell("DATEBAND TO"))

            if cell("ROOM TYPE"):
                if cell("ROOM TYPE") == "C1":
                    child1 = cell("NET RATE")
                elif cell("ROOM TYPE") == "C2":
                    child2 = cell("NET RATE")
                elif cell("ROOM TYPE") == "D":
                    double_value = self.get_float(cell("NET RATE"))
                    double_option = True
                elif cell("ROOM TYPE") == "S":
                    simple_value = self.get_float(cell("NET RATE"))
                    simple_option = True
                elif cell("ROOM TYPE") == "T":
                    triple_value = self.get_float(cell("NET RATE"))
                    triple_option = True

            if cell("HOTEL COMMENTS") and cell("HOTEL COMMENTS").strip() != "":
                hotel_info = cell("HOTEL COMMENTS") + "\n\n" + hotel_info

            if cell("ROOM COMMENTS") and cell("ROOM COMMENTS").strip() != "":
                # hotel_info += option_value.get_code_by_id(room_type_id) + '\n'
                hotel_info += cell("ROOM COMMENTS") + "\n\n"

            if (
                simple_option
                and double_option
                and triple_option
                and product_hotel
                and suppinfo_id
            ):
                pvals = {
                    "suppinfo_id": suppinfo_id,
                    "start_date": date_from,
                    "end_date": date_to,
                    "room_type_id": room_type_id,
                    "meal_plan_id": mp,
                    "price": double_value,
                    "simple": simple_value,
                    "triple": triple_value,
                    "child": child1,
                    "second_child": child2,
                    "min_quantity": 0,
                }

                pricelist_ids = pricelist_partnerinfo.search(
                    [
                        ("suppinfo_id", "=", suppinfo_id),
                        ("start_date", "=", date_from),
                        ("end_date", "=", date_to),
                        ("room_type_id", "=", room_type_id),
                        ("meal_plan_id", "=", mp),
                    ]
                )
                if len(pricelist_ids) > 0:
                    pricelist_partnerinfo.write(
                        [pricelist_ids[0]],
                        {
                            "price": double_value,
                            "simple": simple_value,
                            "triple": triple_value,
                            "child": child1,
                            "second_child": child2,
                        },
                    )
                else:
                    pricelist_partnerinfo.create(pvals)

        # insert additional information (room and hotel comments) of previous hotel
        # last hotel in sheet case
        if suppinfo_id:
            product_supplierinfo.write([suppinfo_id], {"info": hotel_info})
            hotel_info = ""

        return msg

    def get_option_value(self, name, code):
        ot = self.env["product.attribute"]
        ov = self.env["product.attribute.value"]

        ot_id = ot.search([("code", "=", code)])[0]
        to_search = [("name", "=", name), ("attribute_id", "=", ot_id)]  # FIXME
        ov_ids = ov.search(to_search)
        if ov_ids:
            return ov_ids[0]
        else:
            to_create = {x[0]: x[2] for x in to_search}
            return ov.create(to_create)

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
