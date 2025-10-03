from odoo import _, api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    travel_type = fields.Selection(selection_add=[("package", "Package")])

    @api.depends("travel_type")
    def _compute_details_tab_visibility(self):
        """
        Compute the visibility of the details tab based on the travel type
        """
        for line in self:
            if line.travel_type != "package":
                return super(SaleOrderLine, line)._compute_details_tab_visibility()
            line.details_tab_visible = True

    @api.depends("travel_type")
    def _compute_infants_visibility(self):
        """
        Compute the visibility of the details tab based on the travel type.
        Hidden by default. Inherit in modules
        """
        for line in self:
            if line.travel_type != "package":
                return super(SaleOrderLine, self)._compute_infants_visibility()

            line.infants_visible = True
