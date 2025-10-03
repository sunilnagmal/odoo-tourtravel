#
import xlrd
import base64
import datetime
import timeit

from odoo import _, api, fields, models, models
from odoo.exceptions import ValidationError, UserError


BASE_DATE = 693594


class import_allotment(models.TransientModel):
    _name = "import.allotment"
    _description = "Allotment"

    file = fields.Binary("File")
    result = fields.Text("Result")

    def import_file(self):
        for obj in self:
            if obj.file:
                data = base64.decodestring(obj.file)

                msg = ""
                document = xlrd.open_workbook(file_contents=data)
                sheet = document.sheets()[0]

                hotel = self.env["product.hotel"]
                allotment_model = self.env["product.rate.allotment"]
                daily_allotment_model = self.env["allotment.state"]
                supplierinfo = self.env["product.supplierinfo"]

                head = {sheet.cell_value(0, x): x for x in range(sheet.ncols)}

                hotel_id = False
                room_type_id = False
                date_from = False
                date_to = False
                allotment = False
                release = False
                for r in range(1, sheet.nrows):

                    def cell(attr):
                        if sheet.cell(r, head[attr]).ctype == xlrd.XL_CELL_ERROR:
                            return None
                        return sheet.cell_value(r, head[attr])

                    if cell("Hotel"):
                        hotel_name = cell("Hotel").upper()
                        hotel_ids = hotel.search([("name", "=", hotel_name)])
                        if len(hotel_ids) > 1:
                            msg += "Ambiguous Hotel name: " + hotel_name + "\n"
                            hotel_id = False
                        elif len(hotel_ids) == 0:
                            msg += "Hotel not found: " + hotel_name + "\n"
                            hotel_id = False
                        else:
                            hotel_id = hotel_ids[0]
                            print("Updating " + hotel_name + " allotments\n")

                    if cell("Room type"):
                        room_type_str = cell("Room type").strip().upper()
                        room_type_ids = self.get_option_value(room_type_str, "rt")
                        if len(room_type_ids) > 1:
                            msg += "Ambiguous Room type : " + room_type_str + "\n"
                            room_type_id = False
                        elif len(room_type_ids) == 0:
                            msg += "Room type not found: " + room_type_str + "\n"
                            room_type_id = False
                        else:
                            room_type_id = room_type_ids[0]

                    if cell("From"):
                        date_from = self.get_date(cell("From"))

                    if cell("To"):
                        date_to = self.get_date(cell("To"))

                    if cell("Allotment"):
                        allotment = cell("Allotment")
                    else:
                        allotment = False

                    if cell("Release"):
                        release = cell("Release")
                    else:
                        release = False

                    if (
                        hotel_id
                        and room_type_id
                        and date_from
                        and date_to
                        and allotment is not False
                        and release is not False
                    ):
                        product_id = hotel.read(hotel_id, ["product_tmpl_id"])
                        suppinfo_ids = supplierinfo.search(
                            [("product_tmpl_id", "=", product_id["product_tmpl_id"][0])]
                        )
                        if len(suppinfo_ids) > 1:
                            msg += (
                                "More than one supplier for hotel: " + hotel_name + "\n"
                            )
                        elif len(suppinfo_ids) == 0:
                            msg += "No supplier_info found " + hotel_name + " \n"
                        else:
                            allotment_ids = allotment_model.search(
                                [
                                    ("suppinfo_id", "=", suppinfo_ids[0]),
                                    ("room_type_id", "=", room_type_id),
                                    ("start_date", "=", date_from),
                                    ("end_date", "=", date_to),
                                ]
                            )
                            vals = {
                                "start_date": date_from,
                                "end_date": date_to,
                                "suppinfo_id": suppinfo_ids[0],
                                "room_type_id": room_type_id,
                                "allotment": allotment,
                                "release": release,
                            }
                            if len(allotment_ids) > 1:
                                msg += (
                                    "Duplicated Allotments for hotel:"
                                    + hotel_name
                                    + "\n"
                                )
                            elif len(allotment_ids) == 1:
                                allotment_model.write(allotment_ids, vals)
                            else:
                                allotment_model.create(vals)

                if msg == "":
                    msg += "\n ================== \nAllotment successfully uploaded. \n"
                else:
                    msg += "\n ================== \nCheck that names are properly typed or present in the system. \n"

                msg += "Press cancel to close"

                self.write(obj.id, {"result": msg})
                return {
                    "name": "Import Allotment",
                    "type": "ir.actions.act_window",
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "import.allotment",
                    "res_id": obj.id,
                    "target": "new",
                }
            else:
                raise UserError("You must select a file.")

    def get_date(self, value):
        return datetime.strptime(value, "%d.%m.%y")

    def get_float(self, value):
        try:
            return float(value)
        except Exception:
            return 0.0

    def get_option_value(self, name, code):
        # TODO
        ot = self.env["product.attribute"]
        ov = self.env["product.attribute.value"]

        ot_id = ot.search([("code", "=", code)])[0]
        to_search = [("name", "=", name), ("attribute_id", "=", ot_id)]  # FIXME
        ov_ids = ov.search(to_search)
        return ov_ids
