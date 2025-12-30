# -- coding: utf-8 --

from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.depends(
        "has_tracking",
        "product_id.auto_create_lot",
        "product_id.default_code",
        "picking_type_id.use_existing_lots",
        "state",
    )
    def _compute_display_assign_serial(self):
        super()._compute_display_assign_serial()
        moves_not_display = self.filtered(
            lambda m: m.picking_type_id.code == 'incoming' and m.product_id.auto_create_lot
        )
        for move in moves_not_display:
            move.display_assign_serial = False
        return

    # pylint: disable=missing-return
    def _set_quantities_to_reservation(self):
        super()._set_quantities_to_reservation()
        for move in self:
            if move.state not in ("partially_available", "assigned"):
                continue
            if (
                move.product_id.tracking == "none"
                or not move.product_id.auto_create_lot
                or not move.picking_type_id.code == 'incoming'
            ):
                continue
            for move_line in move.move_line_ids:
                if move_line.lot_id:
                    # Create-backorder wizard would open without this.
                    move_line.quantity = move_line.quantity_product_uom
