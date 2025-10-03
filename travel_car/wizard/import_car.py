#
import xlrd
import base64
import datetime
import timeit

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

BASE_DATE = 693594


class import_car(models.TransientModel):
    _name = "import.car"
    _description = "Import car"

    file = fields.Binary("File")
    result = fields.Text("Result")

    def import_file(self):
        # obj = self.browse(ids[0])
        for obj in self:
            if obj.file:
                data = base64.b64decode(obj.file)

                msg = ""
                document = xlrd.open_workbook(file_contents=data)
                sheet = document.sheets()[0]

                car = self.env["product.car"]
                supplier = self.env["res.partner"]
                supplierinfo = self.env["product.supplierinfo"]
                partnerinfo = self.env["pricelist.partnerinfo"]

                head = {sheet.cell_value(0, x): x for x in range(sheet.ncols)}

                suppinfo_id = False
                car_name = ""
                car_id = False
                car_class_id = False
                transmission_id = False
                passengers = False
                price = False
                create = False
                for r in range(1, sheet.nrows):

                    def cell(attr):
                        if sheet.cell(r, head[attr]).ctype == xlrd.XL_CELL_ERROR:
                            return None
                        return sheet.cell_value(r, head[attr])

                    if cell("Supplier"):
                        supplier_name = cell("Supplier").upper()
                        supplier_ids = supplier.search([("name", "=", supplier_name)])
                        if len(supplier_ids) > 1:
                            msg += "Ambiguous Supplier name: " + supplier_name + "\n"
                            supplier_id = False
                        elif len(supplier_ids) == 0:
                            msg += "Supplier not found: " + supplier_name + "\n"
                            supplier_id = False
                        else:
                            supplier_id = supplier_ids[0]

                    if cell("Car"):
                        car_name = cell("Car").upper()
                        car_ids = car.search([("name", "=", car_name)])
                        if len(car_ids) > 1:
                            msg += "Ambiguous car name: " + car_name + "\n"
                            car_id = False
                        elif len(car_ids) == 0:
                            create = True
                            car_id = False
                        else:
                            car_id = car_ids[0]

                    if cell("Class"):
                        car_class = cell("Class").upper()
                        car_class_id = self.get_option_value(car_class, "cl", {})

                    if cell("Transmission"):
                        transmission = cell("Transmission").upper()
                        transmission_id = self.get_option_value(transmission, "tm", {})

                    if cell("Passengers"):
                        passengers = cell("Passengers")

                    if cell("From"):
                        date_from = self.get_date(cell("From"))

                    if cell("To"):
                        date_to = self.get_date(cell("To"))

                    if cell("Price"):
                        price = cell("Price")
                    else:
                        price = False

                    if create:
                        car_id = car.create(
                            {
                                "name": car_name,
                                "class_id": car_class_id,
                                "categ_id": 4,
                                "transmission_id": transmission_id,
                                "passengers": passengers,
                            }
                        )
                        create = False

                    if supplier_id and car_id:
                        suppinfo_id = None
                        product_tmpl_id = car.read(car_id, ["product_tmpl_id"])[
                            "product_tmpl_id"
                        ][0]
                        suppinfo_ids = supplierinfo.search(
                            [
                                "&",
                                ("name", "=", supplier_id),
                                ("product_tmpl_id", "=", product_tmpl_id),
                            ]
                        )
                        if len(suppinfo_ids) == 0:
                            svals = {
                                "name": supplier_id,
                                "product_tmpl_id": product_tmpl_id,
                                "min_qty": 0,
                            }
                            suppinfo_id = supplierinfo.create(svals)
                        else:
                            suppinfo_id = suppinfo_ids[0]

                        pvals = {
                            "suppinfo_id": suppinfo_id,
                            "start_date": date_from,
                            "end_date": date_to,
                            "price": price,
                            "min_quantity": 0,
                        }

                        pricelist_ids = partnerinfo.search(
                            [
                                ("suppinfo_id", "=", suppinfo_id),
                                ("start_date", "=", date_from),
                                ("end_date", "=", date_to),
                            ]
                        )
                        if len(pricelist_ids) > 0:
                            partnerinfo.write([pricelist_ids[0]], {"price": price})
                        else:
                            partnerinfo.create(pvals)

                if msg == "":
                    msg += "\n ================== \nRental information successfully uploaded. \n"
                else:
                    msg += "\n ================== \nCheck that names are properly typed or present in the system. \n"

                msg += "Press cancel to close"

                obj.write({"result": msg})
                return {
                    "name": "Import Rental Prices",
                    "type": "ir.actions.act_window",
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "import.car",
                    "res_id": obj.id,
                    "target": "new",
                }
            else:
                raise UserError("Error!", "You must select a file.")

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

    def get_option_value(self, name, code):
        ot = self.env["product.attribute"]
        ov = self.env["product.attribute.value"]

        ot_id = ot.search([("code", "=", code)])[0]
        to_search = [("name", "=", name), ("attribute_id", "=", ot_id)]  # FIXME
        ov_ids = ov.search(to_search)[0]
        return ov_ids
