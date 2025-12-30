from odoo import api, fields, models, _
from odoo.exceptions import UserError

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    arabic_name = fields.Char(string="Arabic Name")
    is_storable = fields.Boolean(
        'Track Inventory', store=True, compute='compute_is_storable', readonly=False,
        default=True, precompute=True, help='A storable product is a product for which you manage stock.')

class ProductProduct(models.Model):
    _inherit = 'product.product'

    arabic_name = fields.Char(string="Arabic Name", related='product_tmpl_id.arabic_name')


class ProductCategory(models.Model):
    _inherit = "product.category"

    inventory_gain_account_id = fields.Many2one('account.account',
                                                string="Inventory Gain Account")
    inventory_loss_account_id = fields.Many2one('account.account',
                                                string="Inventory Loss Account")


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_product_accounts_new(self):
        res = self._get_asset_accounts()

        return {
            # 'income': self.property_account_income_id or self.categ_id.property_account_income_categ_id,
            # 'expense': self.property_account_expense_id or self.categ_id.property_account_expense_categ_id,
            'stock_input': res.get('stock_input') or self.categ_id.inventory_gain_account_id,
            'stock_output': res.get('stock_output') or self.categ_id.inventory_loss_account_id,
            'stock_valuation': self.categ_id.property_stock_valuation_account_id or False,
            'stock_journal': self.categ_id.property_stock_journal or False,
        }


    # def get_product_accounts_new(self, fiscal_pos=None):
    #     accounts = self._get_product_accounts_new()
    #     if not fiscal_pos:
    #         fiscal_pos = self.env['account.fiscal.position']
    #     return fiscal_pos.map_accounts(accounts)

    def get_product_accounts_new(self, fiscal_pos=None):
        return {
            key: (fiscal_pos or self.env['account.fiscal.position']).map_account(account)
            for key, account in self._get_product_accounts_new().items()
        }


class StockMove(models.Model):
    _inherit = "stock.move"

    def _get_accounting_data_for_valuation(self):
        """ Return the accounts and journal to use to post Journal Entries for
        the real-time valuation of the quant. """
        self.ensure_one()
        self = self.with_company(self.company_id)
        if self.is_inventory:
            accounts_data = self.product_id.product_tmpl_id.get_product_accounts_new()
        else:
            accounts_data = self.product_id.product_tmpl_id.get_product_accounts()

        acc_src = self._get_src_account(accounts_data)
        acc_dest = self._get_dest_account(accounts_data)

        acc_valuation = accounts_data.get('stock_valuation', False)
        if acc_valuation:
            acc_valuation = acc_valuation.id
        if not accounts_data.get('stock_journal', False):
            raise UserError(_('You don\'t have any stock journal defined on your product category, check if you have installed a chart of accounts.'))
        if not acc_src:
            raise UserError(_('Cannot find a stock input account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.display_name))
        if not acc_dest:
            raise UserError(_('Cannot find a stock output account for the product %s. You must define one on the product category, or on the location, before processing this operation.') % (self.product_id.display_name))
        if not acc_valuation:
            raise UserError(_('You don\'t have any stock valuation account defined on your product category. You must define one before processing this operation.'))
        journal_id = accounts_data['stock_journal'].id
        return journal_id, acc_src, acc_dest, acc_valuation
