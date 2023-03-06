from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class ServiceStock(models.Model):
    _name = "fish.service.stock"
    _rec_name = 'ref'

    ref = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    customer_id = fields.Many2one('res.partner', 'Customer', required=True)
    stock_id = fields.Many2one('stock.warehouse', 'Stock',
                               default=lambda self: self.env.ref("fishing_v2.main_stock_id"))
    location_id = fields.Many2one('stock.location', 'Location',
                                  default=lambda self: self.env.ref("fishing_v2.temporary_id"))
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=False)
    category_id = fields.Many2one(comodel_name='product.template', string='Category', required=False,
                                  domain=[('type', '!=', 'service')])
    qte = fields.Float(string='Quantity')
    total = fields.Float(string='Total Quantity', compute="_compute_stock_quantity")
    nbr_pallets = fields.Integer(string="Number of pallets", readonly=True, compute="_compute_numbers")
    nbr_packages = fields.Integer(string="Number of packages", readonly=True, compute="_compute_numbers")
    receive_date = fields.Datetime(string='Receive date', required=False, default=datetime.now())
    expected_exit_date = fields.Datetime(string='Expected exit date', required=False)
    exit_date = fields.Datetime(string='Exit date', required=False)
    is_out = fields.Boolean(string='Exit', default=False)
    is_ready_out = fields.Boolean(string='Ready', default=False)
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)

    pallet_ids = fields.One2many(comodel_name='stock.service.pallet', inverse_name='stock_service_id', string='Pallets')
    box_ids = fields.One2many(comodel_name='fish.service.stock.caisse', inverse_name='stock_service_id',
                              string='Packages')

    # @api.onchange("qte")
    def _onchange_fields(self):
        if self.qte:
            self.qte = abs(self.qte)

    @api.onchange("pallet_ids", "box_ids")
    def _onchange_qte_fields(self):
        self.qte = sum(self.pallet_ids.mapped('quantity')) + sum(self.box_ids.mapped('quantity'))

    @api.model
    def create(self, vals):
        global occupied_unit
        if vals.get('ref', _('New')) == _('New'):
            vals['ref'] = self.env['ir.sequence'].next_by_code('fish.service.stock') or _('New')
        location = self.env.ref('fishing_v2.temporary_id')
        if not vals.get('location_id'):
            vals['location_id'] = location.id
        serv_location = self.env['stock.location'].browse(vals.get('location_id'))
        production_quants = self.env['stock.quant'].sudo().search([('location_id', 'child_of', serv_location.id)])
        service_quants = self.env['fish.service.stock'].sudo().search(
            [('location_id', 'child_of', serv_location.id), ('is_out', "=", False), ('is_ready_out', "=", False)])
        occupied_unit = sum(production_quants.mapped('quantity')) + sum(service_quants.mapped('qte'))

        if (location.capacity_unit - occupied_unit) < vals.get('qte'):
            raise ValidationError("Stock capacity insufficient\nThis location has " + str(
                location.capacity_unit - occupied_unit) + " units free capacity  and you are trying to add " + str(
                vals.get('qte')))
        result = super(ServiceStock, self).create(vals)

        return result

    def _compute_stock_quantity(self):
        for line in self:
            line.total = sum(line.box_ids.mapped('quantity'))

    def _compute_numbers(self):
        for line in self:
            line.nbr_pallets = len(line.pallet_ids)
            line.nbr_packages = len(line.box_ids)

    def exit_stock(self):
        self.is_out = True
        self.exit_date = datetime.now()
        for pack in self.pallet_ids:
            pack.write({'is_out': True, 'exit_date': datetime.now()})
        for pack in self.box_ids:
            pack.write({'is_out': True, 'exit_date': datetime.now()})

    def exit_stock_ready(self):
        view_id = self.env.ref('fishing_v2.stock_exit_form_view')
        return {
            'name': _('Stock exit'),
            'res_model': 'fishing.service.stock.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'type': 'ir.actions.act_window',
            'context': {
                'active_model': 'fish.service.stock',
                'active_ids': self.ids,
                'start': self.receive_date,
                'end': datetime.now()
            }
        }

    def exit_stock_content_ready(self):
        view_id = self.env.ref('fishing_v2.stock_content_exit_form_view')
        return {
            'name': _('Stock exit'),
            'res_model': 'stock.content.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'type': 'ir.actions.act_window',
            'context': {
                'active_model': 'fish.service.stock',
                'active_ids': self.ids,
                'start': self.receive_date
            }
        }


class StockServicePallet(models.Model):
    """ Pallets containing packs and/or other packages """
    _name = "stock.service.pallet"
    _description = "Pallets containing packs and/or other packages"
    _order = 'name'

    name = fields.Char('Pallet Reference', copy=False, index=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('stock.pallet') or _('Unknown Pallet'))
    customer_id = fields.Many2one('res.partner', 'Customer', required=True, related="stock_service_id.customer_id")
    box_ids = fields.One2many('fish.service.stock.caisse', 'pallet_id', 'Bulk Content')
    barcode = fields.Char(string="Barcode", readonly=True)
    location_id = fields.Many2one('stock.location', 'Location', readonly=True)
    stock_service_id = fields.Many2one('fish.service.stock', 'Service')
    linked_stock_service_id = fields.Many2one('fish.service.stock', 'Service')
    quantity = fields.Float(string="Quantity", readonly=True, compute="_compute_weight")
    nbr_packages = fields.Integer(string="Number of packages", readonly=True, compute="_compute_weight")
    receive_date = fields.Datetime(string='Receive date', required=False, default=datetime.now())
    expected_exit_date = fields.Datetime(string='Expected exit date', required=False)
    exit_date = fields.Datetime(string='Exit date', required=False)
    is_out = fields.Boolean(string='Exit', default=False)
    is_ready_out = fields.Boolean(string='Ready', default=False)
    exit_status = fields.Char("Exit status", compute="_compute_exit_status")
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )

    @api.model
    def create(self, vals):
        vals['linked_stock_service_id'] = vals['stock_service_id']
        result = super(StockServicePallet, self).create(vals)

        return result

    def _compute_weight(self):
        for pallet in self:
            pallet_qty = 0
            for p in pallet.box_ids:
                pallet_qty += p.quantity
            pallet.quantity = pallet_qty
            pallet.nbr_packages = len(pallet.box_ids)

    def unpack(self):
        for line in self.box_ids:
            line.write({'pallet_id': False})
        self.unlink()
        action = self.env.ref('fishing_v2.action_pallets_view').read()[0]
        return action

    @api.model
    def unlink(self, id):
        raise ValidationError("Can't delete pallet")

    def prepare_exit_stock(self, inv=False, price=False, duration=False):

        if inv:
            quantity_data = self
            stock_service = self.env.ref('fishing_v2.product_service_stock')
            context = {'check_move_validity': False}
            inv_line_vals = {
                'product_id': stock_service.id,
                'name': stock_service.display_name,
                'account_id': stock_service.property_account_income_id.id,
                'quantity': quantity_data.quantity,
                'move_id': inv.id,
                'price_unit': price,
                'price_subtotal': price * quantity_data.quantity,
                'price_total': price * quantity_data.quantity,
            }
            self.with_context(context).env['account.move.line'].create(inv_line_vals)
            stock_debit_line_vals = {
                'account_id': inv.partner_id.property_account_receivable_id.id if inv.partner_id.property_account_receivable_id else False,
                'product_id': stock_service.id,
                'quantity': quantity_data.quantity,
                'name': stock_service.display_name,
                'move_id': inv.id,
                'price_unit': price,
                'price_subtotal': price * quantity_data.quantity,
                'debit': price * quantity_data.quantity,
                'exclude_from_invoice_tab': True,
            }
            self.with_context(context).env['account.move.line'].create(stock_debit_line_vals)
            quantity_data.write({'is_ready_out': True})

        exit_vals = {
            "stock_service_id": self.stock_service_id.id,
            "location_id": self.location_id.id,
            "pallet_id": self.id,
        }
        self.env["fish.service.stock.exit"].create(exit_vals)
        self.is_ready_out = True

        for pack in self.box_ids:
            pack.exit_stock()

    def exit_stock(self):
        self.is_out = True
        self.linked_stock_service_id = self.stock_service_id
        self.stock_service_id = False
        self.exit_date = datetime.now()

    def _compute_exit_status(self):
        for line in self:
            line.exit_status = ""
            if line.is_ready_out:
                line.exit_status = "Ready"
            if line.is_out:
                line.exit_status = "Exit"


class ServiceCaisse(models.Model):
    _name = "fish.service.stock.caisse"
    _rec_name = 'ref'

    ref = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    customer_id = fields.Many2one('res.partner', 'Customer', required=True, related="stock_service_id.customer_id")
    stock_service_id = fields.Many2one('fish.service.stock', 'Service')
    linked_stock_service_id = fields.Many2one('fish.service.stock', 'Service')
    location_id = fields.Many2one('stock.location', 'Location',
                                  default=lambda self: self.env.ref("fishing_v2.temporary_id"))
    product_id = fields.Many2one(comodel_name='product.product', string='Product', required=False)
    pallet_id = fields.Many2one('stock.service.pallet', 'Pallet', required=False)
    linked_pallet_id = fields.Many2one('stock.service.pallet', 'Pallet', required=False)
    barcode = fields.Char(string="Barcode", readonly=True)
    quantity = fields.Float(string="Quantity", readonly=False)
    exit_date = fields.Datetime(string='Exit date', required=False)
    is_out = fields.Boolean(string='Exit', default=False)
    is_ready_out = fields.Boolean(string='Ready', default=False)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )
    exit_status = fields.Char("Exit status", compute="_compute_exit_status")


    #Dynamic domain apply on pallet
    @api.onchange('pallet_id')
    def onchange_pallet_id(self):


        return {'domain': {'pallet_id':[('id', 'in', self.stock_service_id.pallet_ids.ids)]}}

    @api.model
    def create(self, vals):
        if vals.get('ref', _('New')) == _('New'):
            vals['ref'] = self.env['ir.sequence'].next_by_code('stock.quant.package') or _('New')
            vals['linked_pallet_id'] = vals['pallet_id']
            vals['linked_stock_service_id'] = vals['stock_service_id']
        result = super(ServiceCaisse, self).create(vals)

        return result

    @api.model
    def unlink(self, id):
        raise ValidationError("Can't delete package")

    def prepare_exit_stock(self, inv=False, price=False, duration=False):

        if inv:
            quantity_data = self
            stock_service = self.env.ref('fishing_v2.product_service_stock')
            context = {'check_move_validity': False}
            inv_line_vals = {
                'product_id': stock_service.id,
                'name': stock_service.display_name,
                'account_id': stock_service.property_account_income_id.id,
                'quantity': quantity_data.quantity,
                'move_id': inv.id,
                'price_unit': price,
                'price_subtotal': price * quantity_data.quantity,
                'price_total': price * quantity_data.quantity,
            }
            self.with_context(context).env['account.move.line'].create(inv_line_vals)
            stock_debit_line_vals = {
                'account_id': inv.partner_id.property_account_receivable_id.id if inv.partner_id.property_account_receivable_id else False,
                'product_id': stock_service.id,
                'quantity': quantity_data.quantity,
                'name': stock_service.display_name,
                'move_id': inv.id,
                'price_unit': price,
                'price_subtotal': price * quantity_data.quantity,
                'debit': price * quantity_data.quantity,
                'exclude_from_invoice_tab': True,
            }
            self.with_context(context).env['account.move.line'].create(stock_debit_line_vals)
            quantity_data.write({'is_ready_out': True})

        exit_vals = {
            "stock_service_id": self.stock_service_id.id,
            "location_id": self.location_id.id,
            "box_id": self.id,
        }
        self.env["fish.service.stock.exit"].create(exit_vals)
        self.is_ready_out = True

    def exit_stock(self):

        self.linked_stock_service_id = self.stock_service_id
        self.linked_pallet_id = self.pallet_id
        self.stock_service_id = False
        self.pallet_id = False

        self.is_out = True
        self.exit_date = datetime.now()

    def _compute_exit_status(self):
        for line in self:
            line.exit_status = ""
            if line.is_ready_out:
                line.exit_status = "Ready"
            if line.is_out:
                line.exit_status = "Exit"

    # @api.onchange('pallet_id')
    # def onchange_pallet(self):
    #     if self.pallet_id.stock_service_id and (self.pallet_id.stock_service_id != self.stock_service_id):
    #         raise ValidationError("Pallet doesn't belong to this service")


class ServiceStockExit(models.Model):
    _name = "fish.service.stock.exit"
    _rec_name = 'stock_service_id'

    user_id = fields.Many2one('res.users', 'User', required=True, default=lambda self: self.env.user.id)
    stock_service_id = fields.Many2one('fish.service.stock', 'Service')
    location_id = fields.Many2one('stock.location', 'Location from')
    pallet_id = fields.Many2one('stock.service.pallet', 'Pallet')
    box_id = fields.Many2one("fish.service.stock.caisse", 'Caisse')
    exit_time = fields.Datetime('Exit time', default=datetime.now())
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )
