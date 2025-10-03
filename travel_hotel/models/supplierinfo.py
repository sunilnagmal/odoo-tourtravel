
from odoo import _, api, fields, models


class SupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    travel_type = fields.Selection(related='product_tmpl_id.travel_type')
