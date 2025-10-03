from odoo import _, api, fields, models


class product_category_change(models.TransientModel):
    _name = "product.category.change"
    _description = "Category change wizard"

    category_id = fields.Many2one("product.category", "Category")

    def convert(self, ids):
        prod = self.env["product.product"]
        visa = self.env["product.visa"]
        obj = self.browse(ids[0])
        model = "product." + obj.category_id.name.lower()
        product_ids = self._context.get("active_ids")
        for p in visa.browse(product_ids):
            to_search = [("name", "=", p.name), ("categ_id", "=", obj.category_id.id)]
            p_ids = prod.search(to_search)
            if p_ids:
                pass
            to_create = {x[0]: x[2] for x in to_search}
            self.env[model].create(to_create)
        visa.unlink(product_ids)
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.visa",
            "view_type": "form",
            "view_mode": "tree,form",
        }
