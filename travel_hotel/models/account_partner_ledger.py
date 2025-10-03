import json

from odoo import models, api, _, fields
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.misc import format_date, get_lang

from datetime import timedelta
from collections import defaultdict


class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = "account.partner.ledger.report.handler"

    @api.model
    def _get_account_move_details(self, document_name, move_type):
        account_move = self.env["account.move"].search(
            [("name", "=", document_name), ("move_type", "=", move_type)]
        )
        datas = []
        if account_move.reservation_number:
            datas.append(account_move.reservation_number)

        if account_move.hotel_name:
            datas.append(account_move.hotel_name)

        if account_move.traveler_name:
            datas.append(account_move.traveler_name)

        if account_move.start_date and account_move.end_date:
            datas.append(
                "From %s till %s" % (account_move.start_date, account_move.end_date)
            )

        return " / ".join(datas)

    def _get_aml_values(self, options, partner_ids, offset=0, limit=None):
        rslt = super(PartnerLedgerCustomHandler, self)._get_aml_values(
            options, partner_ids, offset, limit
        )
        if "available_variants" in options:
            if options["available_variants"][0]["name"] == "Partner Ledger":
                for partner in partner_ids:
                    for line in rslt[partner]:
                        move_details = ""
                        if line["move_type"] == "out_invoice":
                            move_details = self._get_account_move_details(
                                line["name"], line["move_type"]
                            )
                        if line["move_type"] == "in_invoice":
                            move_details = self._get_account_move_details(
                                line["move_name"], line["move_type"]
                            )

                        line.update({"description": move_details})
        return rslt

    class AccountReport(models.Model):
        _inherit = "account.report"

        def _build_columns_from_column_group_vals(
            self, options, all_column_group_vals_in_order
        ):
            columns, columns_group = super()._build_columns_from_column_group_vals(
                options, all_column_group_vals_in_order
            )
            if "available_variants" in options:
                if options["available_variants"][0]["name"] == "Partner Ledger":
                    # Will add new columns
                    columns.insert(
                        3,
                        {
                            "name": "Description",
                            "column_group_key": columns[0]["column_group_key"],
                            "expression_label": "description",
                            "sortable": False,
                            "figure_type": "none",
                            "blank_if_zero": True,
                            "style": "text-align: center; white-space: nowrap;",
                        },
                    )
            return columns, columns_group
