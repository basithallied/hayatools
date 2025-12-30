# -- coding: utf-8 --

from odoo import models, fields
from datetime import datetime
import pytz  # Ensure pytz is imported

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    def _get_lot_sequence(self, rate):
        self.ensure_one()

        # Get current time in UTC and convert it to Saudi Arabia time
        saudi_tz = pytz.timezone("Asia/Riyadh")
        utc_now = datetime.now(pytz.utc)
        saudi_now = utc_now.astimezone(saudi_tz)

        # Format the date as '20-MAY-2025 10:48'
        formatted_date_time = saudi_now.strftime("%d-%b-%Y %H:%M").upper()

        # Return the formatted sequence
        return f"{self.product_id.default_code}/{rate}/{formatted_date_time}"