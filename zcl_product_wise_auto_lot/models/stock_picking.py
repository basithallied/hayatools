# -- coding: utf-8 --

from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _set_auto_lot(self):
        """
        Allows to be called either by button or through code
        """
        pickings = self.filtered(lambda p: p.picking_type_id.code == 'incoming')
        lines = pickings.mapped("move_line_ids").filtered(
            lambda x: (
                not x.lot_id
                and not x.lot_name
                and x.product_id.tracking != "none"
                and x.product_id.auto_create_lot
            )
        )
        for line in lines:
            rate = line.move_id.purchase_line_id.price_unit
            line.lot_name = line._get_lot_sequence(rate)

    def _action_done(self):
        if not self.return_id:
            self._set_auto_lot()
        return super()._action_done()

    def button_validate(self):
        if not self.return_id:
            self._set_auto_lot()
        return super().button_validate()
