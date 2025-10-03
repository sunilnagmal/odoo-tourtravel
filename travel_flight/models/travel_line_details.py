from odoo import _, api, fields, models


class TravelLineDetails(models.Model):
    _inherit = "travel.line.details"

    travel_type = fields.Selection(selection_add=[("flight", "Flight")])

    @api.depends("travel_type")
    def _compute_tl_details_fields_visibility(self):
        """
        Compute the visibility of the airline based on the travel type.
        """
        for record in self:
            if record.travel_type != "flight":
                return super(
                    TravelLineDetails, record
                )._compute_tl_details_fields_visibility()

    @api.onchange("travel_type")
    def _compute_infants_visibility(self):
        for record in self:
            if record.travel_type != "flight":
                return super(TravelLineDetails, self)._compute_infants_visibility()
            record.infants_visible = True
