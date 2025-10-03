from odoo import _, api, fields, models
from odoo.exceptions import ValidationError, UserError

import base64
import datetime
import xlrd

BASE_DATE = 693594


class import_transfer(models.TransientModel):
    _name = "import.transfer"
    _description = "Transfer import wizard"

    file = fields.Binary("File")
    sheet = fields.Integer("Sheet", default=0)
    result = fields.Text("Result")

    def import_file(self):
        # obj = self.browse(ids[0])
        for obj in self:
            if obj.file:
                origin = base64.decodestring(obj.file)
                try:
                    data = self.read_from_calc(origin, obj.sheet)
                except Exception:
                    raise UserError("The file is not valid.")
                self.load_transfer(obj, data)
                msg = "The operation was successful."
                self.write(obj.id, {"result": msg})
                return {
                    "name": "Import Products",
                    "type": "ir.actions.act_window",
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "import.transfer",
                    "res_id": obj.id,
                    "target": "new",
                }
            else:
                raise UserError("You must select a file.")

    def read_from_calc(self, data, sheet):
        document = xlrd.open_workbook(file_contents=data)
        data = document.sheets()
        return data

    def get_id_by_name(self, model, name):
        obj = self.env[model]
        obj_id = obj.search([("name", "=", name)])
        if not obj_id and self._context.get("create"):
            vals = {"name": name}
            if self._context.get("values"):
                vals.update(self._context["values"])
            obj_id = [obj.create(vals)]
        return obj_id and obj_id[0] or False

    def get_categ_id(self, categ):
        product = self.env["product.product"]
        ctx = self._context.copy()
        ctx.update({"product_type": categ})
        return product._get_category(ctx)

    def get_value(self, value):
        try:
            return float(value)
        except Exception:
            return False

    def get_date(self, value):
        d = BASE_DATE + int(value)
        return datetime.fromordinal(d)

    def find_by_code(self, code, model):
        obj = self.env[model]
        val = obj.search([("code", "=", code)])[0]
        return val

    def find_by_name(self, name, model):
        obj = self.env[model]
        val = obj.search([("name", "=", name)])[0]
        return val

    def get_option_value(self, name, code):
        ot = self.env["product.attribute"]
        ov = self.env["product.attribute.value"]

        ot_id = ot.search([("code", "=", code)])[0]
        to_search = [("name", "=", name), ("attribute_id", "=", ot_id)]  # FIXME
        ov_ids = ov.search(to_search)
        if ov_ids:
            return ov_ids[0]
        else:
            raise Exception()

    """ Transfers """

    def load_transfer(self, obj, data):
        product_transfer = self.env["product.template"]
        product_supplierinfo = self.env["product.supplierinfo"]
        pricelist_partnerinfo = self.env["pricelist.partnerinfo"]
        partner = self.env["res.partner"]
        transfer_categ_id = self.env["product.category"].search(
            [("name", "=", "Transfer")]
        )[0]

        msg = ""
        sheet = data[-1]

        head = {sheet.cell_value(1, x): x for x in range(sheet.ncols)}

        date_from = sheet.cell_value(0, 0)
        date_to = sheet.cell_value(0, 1)

        for r in range(2, sheet.nrows):

            def cell(attr):
                if sheet.cell(r, head[attr]).ctype == xlrd.XL_CELL_ERROR:
                    return None
                return sheet.cell_value(r, head[attr])

            suppinfo_id = False
            transfer_obj = False
            min_paxs = False
            max_paxs = False
            vehicle_type_id = False
            guide_id = False
            confort_id = False
            price = False

            if cell("Name"):
                transfer_name = cell("Name").strip()
                transfer_ids = product_transfer.search([("name", "=", transfer_name)])
                if len(transfer_ids) == 0:
                    transfer_id = product_transfer.create(
                        {"name": transfer_name, "categ_id": transfer_categ_id}
                    )
                    transfer_obj = product_transfer.browse(transfer_id)
                elif len(transfer_ids) > 1:
                    msg += "Ambiguous name for transfer: " + transfer_name + "\n"
                    continue
                else:
                    transfer_obj = product_transfer.browse(transfer_ids[0])

            if cell("Supplier"):
                if transfer_obj:
                    suppinfo_id = None
                    supplier_name = str(cell("Supplier")).strip()
                    if supplier_name != "":
                        partner_ids = partner.search([("name", "=", supplier_name)])
                        if len(partner_ids) == 0:
                            msg += "Supplier name not found: " + supplier_name + "\n"
                            continue
                        elif len(partner_ids) > 1:
                            msg += (
                                "Ambiguous name for supplier: " + supplier_name + "\n"
                            )
                            continue
                        else:
                            partner_id = partner_ids[0]
                            suppinfo_ids = product_supplierinfo.search(
                                [
                                    "&",
                                    ("name", "=", partner_id),
                                    (
                                        "product_tmpl_id",
                                        "=",
                                        transfer_obj.product_tmpl_id.id,
                                    ),
                                ]
                            )
                            if len(suppinfo_ids) == 0:
                                svals = {
                                    "name": partner_id,
                                    "product_tmpl_id": transfer_obj.product_tmpl_id.id,
                                    "min_qty": 0,
                                }
                                suppinfo_id = product_supplierinfo.create(svals)
                            else:
                                suppinfo_id = suppinfo_ids[0]

            if cell("Min paxs"):
                try:
                    min_paxs = int(cell("Min paxs"))
                except Exception:
                    msg += "Wrong min paxs for: " + transfer_name + "\n"
                    continue
            if cell("Max paxs"):
                try:
                    max_paxs = int(cell("Max paxs"))
                except Exception:
                    msg += "Wrong max paxs for: " + transfer_name + "\n"
                    continue
            if cell("Vehicle type"):
                try:
                    vehicle_type_id = self.get_option_value(
                        cell("Vehicle type"), "vt"
                    ).upper()
                except Exception:
                    msg += "Wrong vehicle type option in " + transfer_name + "\n"
                    continue
            if cell("Guide"):
                try:
                    guide_id = self.get_option_value(cell("Guide"), "guide").upper()
                except Exception:
                    msg += "Wrong guide option in " + transfer_name + "\n"
                    continue
            if cell("Confort"):
                try:
                    confort = self.get_option_value(cell("Confort"), "vc").upper()
                except Exception:
                    msg += "Wrong confort option in " + transfer_name + "\n"
                    continue
            if cell("Price"):
                try:
                    price = float(cell("Price"))
                except Exception:
                    msg += "Wrong price for: " + transfer_name + "\n"
                    continue

            if (
                suppinfo_id
                and transfer_obj
                and min_paxs
                and max_paxs
                and vehicle_type
                and guide
                and confort
                and price
            ):
                pvals = {
                    "start_date": date_from,
                    "end_date": date_to,
                    "price": price,
                    "min_quantity": 0,
                    "suppinfo_id": suppinfo_id,
                    "min_paxs": min_paxs,
                    "max_paxs": max_paxs,
                    "vehicle_type_id": vehicle_type,
                    "guide_id": guide,
                    "confort_id": confort_id,
                }
            pricelist_partnerinfo.create(pvals)
        return True

    def prepare_load(self):
        model = "product.attribute.value"
        taxi = self.find_by_code("taxi", model)
        microbus = self.find_by_code("micro", model)
        minibus = self.find_by_code("mini", model)
        omnibus = self.find_by_code("omni", model)
        guide = self.find_by_code("guide", model)
        no_guide = self.find_by_code("no_guide", model)
        confort_s = self.find_by_code("vcs", model)
        confort_l = self.find_by_code("vcl", model)

        dict_options = {
            2: {
                "vehicle_type_id": taxi,
                "guide_id": no_guide,
                "min_paxs": 1,
                "max_paxs": 2,
                "confort_id": confort_s,
            },
            3: {
                "vehicle_type_id": taxi,
                "guide_id": guide,
                "min_paxs": 1,
                "max_paxs": 2,
                "confort_id": confort_s,
            },
            4: {
                "vehicle_type_id": taxi,
                "guide_id": no_guide,
                "min_paxs": 1,
                "max_paxs": 2,
                "confort_id": confort_l,
            },
            5: {
                "vehicle_type_id": taxi,
                "guide_id": guide,
                "min_paxs": 1,
                "max_paxs": 2,
                "confort_id": confort_l,
            },
            6: {
                "vehicle_type_id": microbus,
                "guide_id": no_guide,
                "min_paxs": 3,
                "max_paxs": 5,
                "confort_id": confort_s,
            },
            7: {
                "vehicle_type_id": microbus,
                "guide_id": no_guide,
                "min_paxs": 6,
                "max_paxs": 8,
                "confort_id": confort_s,
            },
            8: {
                "vehicle_type_id": microbus,
                "guide_id": guide,
                "min_paxs": 3,
                "max_paxs": 5,
                "confort_id": confort_s,
            },
            9: {
                "vehicle_type_id": microbus,
                "guide_id": guide,
                "min_paxs": 6,
                "max_paxs": 8,
                "confort_id": confort_s,
            },
            10: {
                "vehicle_type_id": minibus,
                "guide_id": guide,
                "min_paxs": 9,
                "max_paxs": 12,
                "confort_id": confort_s,
            },
            11: {
                "vehicle_type_id": minibus,
                "guide_id": guide,
                "min_paxs": 13,
                "max_paxs": 20,
                "confort_id": confort_s,
            },
            12: {
                "vehicle_type_id": omnibus,
                "guide_id": guide,
                "min_paxs": 21,
                "max_paxs": 30,
                "confort_id": confort_s,
            },
            13: {
                "vehicle_type_id": omnibus,
                "guide_id": guide,
                "min_paxs": 31,
                "max_paxs": 43,
                "confort_id": confort_s,
            },
        }
        return dict_options
