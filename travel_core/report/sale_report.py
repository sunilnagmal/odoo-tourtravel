from odoo import tools
from odoo import _, api, fields, models


class sale_report(models.Model):
    _name = "sale.report"
    _inherit = "sale.report"

    paxs = fields.Integer("Paxs", readonly=True)
    supplier_id = fields.Many2one("res.partner", "Supplier")

    # TODO: incluir la agrupacion por el campo origin en el
    # analisis de facturas

    def _select(self):
        select_str = """
             SELECT min(l.id) as id,
                    l.product_id as product_id,
                    t.uom_id as uom_uom,
                    sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
                    sum(l.product_uom_qty * l.price_unit * (100.0-l.discount) / 100.0) as price_total,
                    count(*) as nbr,
                    s.date_order as date,
                    s.partner_id as partner_id,
                    s.user_id as user_id,
                    s.company_id as company_id,
                    extract(epoch from avg(date_trunc('day',s.date_order)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                    s.state,
                    t.categ_id as categ_id,
                    s.pricelist_id as pricelist_id,
                    s.project_id as analytic_account_id
        """
        return select_str

    def _from(self):
        from_str = """
                sale_order_line l
                      join sale_order s on (l.order_id=s.id)
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join uom_uom u on (u.id=l.product_uom)
                    left join uom_uom u2 on (u2.id=t.uom_id)
        """
        return from_str

    def _group_by(self):
        group_by_str = """
            GROUP BY l.product_id,
                    l.order_id,
                    t.uom_id,
                    t.categ_id,
                    s.date_order,
                    s.partner_id,
                    s.user_id,
                    s.company_id,
                    s.state,
                    s.pricelist_id,
                    s.project_id
        """
        return group_by_str

    def init(self):
        # self._table = sale_report
        tools.drop_view_if_exists(self._cr, self._table)
        self.env.cr.execute(
            """CREATE or REPLACE VIEW %s as (
                            %s
                            FROM ( %s )
                            %s
                            )"""
            % (self._table, self._select(), self._from(), self._group_by())
        )


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
