import datetime
import re
from odoo import _, api, fields, models


class ProductVariant(models.Model):
    _inherit = "product.product"

    travel_type = fields.Selection(related="product_tmpl_id.travel_type")

    def _get_travel_product_attribute(self, attribute_name):
        self.ensure_one()
        attribute_value = self.product_template_attribute_value_ids.filtered(
            lambda pav: pav.attribute_id.name == attribute_name
        )
        return (
            attribute_value.attribute_id
            and attribute_value.attribute_id.name == attribute_name
            and attribute_value
            or False
        )


class product_category(models.Model):
    _name = "product.category"
    _inherit = "product.category"

    #
    # def name_get(self, ids):
    #     if isinstance(ids, (list, tuple)) and not len(ids):
    #         return []
    #     if isinstance(ids, int):
    #         ids = [ids]
    #     reads = self.read(ids, ['name'])
    #     return [(r['id'], r['name']) for r in reads]
    #
    def _name_get_fnc(self):
        for product in self:
            res = product.name_get()
            product.complete_name = res

    complete_name = fields.Char("Complete Name")
    # compute=_name_get_fnc)
    voucher_name = fields.Char("Voucher name", default="default_travel_voucher_report")
    model_name = fields.Char("Model name")


class product_supplierinfo(models.Model):
    _name = "product.supplierinfo"
    _inherit = "product.supplierinfo"

    supplement_ids = fields.One2many(
        "product.rate.supplement", "suppinfo_id", "Supplements"
    )
    info = fields.Text("Additional Information")
    currency_cost_id = fields.Many2one("res.currency", "Currency Cost")
    min_qty = fields.Float(default=0.0)


class product_rate(models.Model):
    _name = "product.rate"
    _description = "Product rate"

    def _get_ref(self):
        result = {}
        for obj in self:
            result[obj.id] = "PR-" + str(obj.id)
            obj.reference = result

    reference = fields.Char("Ref", compute=_get_ref)
    start_date = fields.Date("Start")
    end_date = fields.Date("End")
    child = fields.Float("Child")
    per_pax = fields.Boolean("Per Pax", default=1)


# TODO Can we use default variants
class product_rate_supplement(models.Model):
    _name = "product.rate.supplement"
    _description = "Rate supplement"

    start_date = fields.Date("Start date")
    end_date = fields.Date("End date")
    price = fields.Float("Price")
    suppinfo_id = fields.Many2one("product.supplierinfo", "Supplier")
    rate_ids = fields.Many2many(
        "product.rate", "supplements_rates_rel", "supplement_id", "rate_id", "Rates"
    )


# TODO is it still needed?
# class pricelist_partnerinfo(models.Model):
#     _name = 'pricelist.partnerinfo'
#     _rec_name = 'reference'
#     _inherit = 'pricelist.partnerinfo'
#     _inherits = {'product.rate': 'product_rate_id'}

#     product_rate_id = fields.Many2one('product.rate', 'Product Rate',
#                                       ondelete="cascade", index=True)
#     rate_start_date = fields.Date(string='Start Date',
#                                   related='product_rate_id.start_date',
#                                   store=True)
#     product_id = fields.Many2one('product.template',
#                                  string='Product',
#                                  related='suppinfo_id.product_id'
#                                  )
#     sequence = fields.Integer('Sequence')
#
#     _defaults = {
#         'min_quantity': 0.0,
#         'sequence': 0
#     }
#     _order = 'rate_start_date'
