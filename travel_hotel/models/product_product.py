from odoo import _, api, fields, models

class ProductProduct(models.Model):
    _inherit = 'product.product'

    allotment_ids = fields.One2many('travel_hotel.allotment',
                                    'product_id',
                                    'Allotment')
