from odoo import models, fields, api, _
from odoo.exceptions import UserError

class InternalStockTransfer(models.Model):
    _name = 'internal.stock.transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Internal Stock Transfer'
    _order = 'id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, default=lambda self: _('New'), tracking=True)
    transfer_type = fields.Selection([
        ('send', 'Send'),
        ('receive', 'Receive')
    ], string='Transfer Type', default='send', required=True, readonly=True, tracking=True)
    
    source_location_id = fields.Many2one('stock.location', string='Source Location', required=True, tracking=True)
    dest_location_id = fields.Many2one('stock.location', string='Destination Location', required=True, tracking=True)
    transit_location_id = fields.Many2one('stock.location', string='Transit Location', required=True, tracking=True)
    
    date = fields.Date(string='Date', default=fields.Date.today(), required=True, tracking=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, readonly=True, tracking=True)
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('transit', 'In Transit'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', readonly=True, copy=False, tracking=True)
    
    line_ids = fields.One2many('internal.stock.transfer.line', 'transfer_id', string='Lines', copy=True)
    
    picking_count = fields.Integer(compute='_compute_picking_count')
    picking_ids = fields.One2many('stock.picking', 'internal_transfer_id', string='Stock Pickings')
    
    linked_transfer_id = fields.Many2one('internal.stock.transfer', string='Linked Transfer', readonly=True)

    @api.model
    def default_get(self, fields):
        res = super(InternalStockTransfer, self).default_get(fields)
        ICPSudo = self.env['ir.config_parameter'].sudo()
        if 'source_location_id' in fields and not res.get('source_location_id'):
            res['source_location_id'] = int(ICPSudo.get_param('zcl_internal_stock_transfer.source_location_id', default=0)) or False
        if 'dest_location_id' in fields and not res.get('dest_location_id'):
            res['dest_location_id'] = int(ICPSudo.get_param('zcl_internal_stock_transfer.dest_location_id', default=0)) or False
        if 'transit_location_id' in fields and not res.get('transit_location_id'):
            res['transit_location_id'] = int(ICPSudo.get_param('zcl_internal_stock_transfer.transit_location_id', default=0)) or False
        return res

    def _compute_picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('internal.stock.transfer') or _('New')
        
        transfer = super(InternalStockTransfer, self).create(vals)
        
        # Automatically create receive record for send type
        if transfer.transfer_type == 'send' and not transfer.linked_transfer_id and not self._context.get('skip_auto_receive'):
            receive_vals = vals.copy()
            receive_vals.update({
                'transfer_type': 'receive',
                'linked_transfer_id': transfer.id,
                'name': _('New'),
            })
            receive_record = self.with_context(skip_auto_receive=True).create(receive_vals)
            transfer.linked_transfer_id = receive_record.id
            
        return transfer

    def write(self, vals):
        res = super(InternalStockTransfer, self).write(vals)
        if not self._context.get('skip_sync'):
            sync_vals = {}
            # Sync key fields
            fields_to_sync = ['source_location_id', 'dest_location_id', 'transit_location_id', 'date', 'user_id']
            for field in fields_to_sync:
                if field in vals:
                    sync_vals[field] = vals[field]

            for rec in self:
                if rec.linked_transfer_id:
                    linked_rec = rec.linked_transfer_id
                    
                    # Sync simple fields
                    if sync_vals:
                        linked_rec.with_context(skip_sync=True).write(sync_vals)

                    # Sync lines if modified
                    if 'line_ids' in vals:
                        linked_rec.with_context(skip_sync=True).line_ids.unlink()
                        for line in rec.line_ids:
                            self.env['internal.stock.transfer.line'].with_context(skip_sync=True).create({
                                'transfer_id': linked_rec.id,
                                'product_id': line.product_id.id,
                                'qty': line.qty,
                            })
        return res

    def action_send(self):
        """Move stock from Source to Transit"""
        for rec in self:
            if rec.transfer_type != 'send':
                raise UserError(_("Only 'Send' transfers can be sent to transit."))
            if not rec.line_ids:
                raise UserError(_("Please add at least one line."))
            
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)
            
            if not picking_type:
                raise UserError(_("No internal picking type found."))

            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': rec.source_location_id.id,
                'location_dest_id': rec.transit_location_id.id,
                'origin': rec.name,
                'internal_transfer_id': rec.id,
            })
            
            for line in rec.line_ids:
                self.env['stock.move'].create({
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': rec.source_location_id.id,
                    'location_dest_id': rec.transit_location_id.id,
                })
            
            picking.action_confirm()
            picking.action_assign()
            if picking.state == 'assigned':
                for move in picking.move_ids:
                    move.quantity = move.product_uom_qty
                picking.button_validate()
            else:
                raise UserError(_("Stock not available in source location."))
                
            rec.state = 'transit'
            if rec.linked_transfer_id:
                rec.linked_transfer_id.state = 'transit'
            
            # Log button click
            rec.message_post(body=_("Transfer sent to transit by %s") % self.env.user.name)

    def action_receive(self):
        """Move stock from Transit to Destination"""
        for rec in self:
            if rec.transfer_type != 'receive':
                raise UserError(_("Only 'Receive' transfers can be finalized at destination."))
            if not rec.line_ids:
                raise UserError(_("Please add at least one line."))
            
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('company_id', '=', self.env.company.id)
            ], limit=1)

            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type.id,
                'location_id': rec.transit_location_id.id,
                'location_dest_id': rec.dest_location_id.id,
                'origin': rec.name,
                'internal_transfer_id': rec.id,
            })

            for line in rec.line_ids:
                self.env['stock.move'].create({
                    'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.qty,
                    'product_uom': line.product_id.uom_id.id,
                    'picking_id': picking.id,
                    'location_id': rec.transit_location_id.id,
                    'location_dest_id': rec.dest_location_id.id,
                })

            picking.action_confirm()
            picking.action_assign()
            if picking.state == 'assigned':
                for move in picking.move_ids:
                    move.quantity = move.product_uom_qty
                picking.button_validate()
            else:
                missing_products = []
                for move in picking.move_ids:
                    if move.state != 'assigned':
                        missing_products.append(move.product_id.display_name)
                raise UserError(_("Stock not available in transit location for: %s") % ", ".join(missing_products))

            rec.state = 'done'
            if rec.linked_transfer_id:
                rec.linked_transfer_id.state = 'done'
            
            # Log button click
            rec.message_post(body=_("Transfer received by %s") % self.env.user.name)

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'
            if rec.linked_transfer_id:
                rec.linked_transfer_id.state = 'cancel'

    def action_view_pickings(self):
        action = self.env.ref('stock.action_picking_tree_all').read()[0]
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action

class InternalStockTransferLine(models.Model):
    _name = 'internal.stock.transfer.line'
    _description = 'Internal Stock Transfer Line'

    transfer_id = fields.Many2one('internal.stock.transfer', string='Transfer', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty = fields.Float(string='Quantity', default=1.0, required=True)
    
    source_qty_available = fields.Float(string='Source Qty', compute='_compute_qty_at_locations')
    transit_qty_available = fields.Float(string='Transit Qty', compute='_compute_qty_at_locations')
    dest_qty_available = fields.Float(string='Dest Qty', compute='_compute_qty_at_locations')

    @api.depends('product_id', 'transfer_id.source_location_id', 'transfer_id.transit_location_id', 'transfer_id.dest_location_id')
    def _compute_qty_at_locations(self):
        for line in self:
            source_qty = 0.0
            transit_qty = 0.0
            dest_qty = 0.0
            if line.product_id and line.transfer_id:
                if line.transfer_id.source_location_id:
                    source_qty = line.product_id.with_context(location=line.transfer_id.source_location_id.id).qty_available
                if line.transfer_id.transit_location_id:
                    transit_qty = line.product_id.with_context(location=line.transfer_id.transit_location_id.id).qty_available
                if line.transfer_id.dest_location_id:
                    dest_qty = line.product_id.with_context(location=line.transfer_id.dest_location_id.id).qty_available
            line.source_qty_available = source_qty
            line.transit_qty_available = transit_qty
            line.dest_qty_available = dest_qty

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    internal_transfer_id = fields.Many2one('internal.stock.transfer', string='Internal Transfer')
