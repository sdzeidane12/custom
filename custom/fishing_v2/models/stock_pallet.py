from odoo import fields, models, api, _
from datetime import datetime


class QuantPackageP(models.Model):
    " Packages containing quants and/or other packages "
    _inherit = "stock.quant.package"

    pallet_id = fields.Many2one('stock.pallet', 'Pallet')
    barcode = fields.Char(string="Barcode", readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True, compute="_compute_info")
    quantity = fields.Float(string="Quantity", readonly=True, compute="_compute_info")
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )
    def _compute_info(self):
        for line in self:
            line.product_id = line.quant_ids[0].product_id.id if line.quant_ids else False
            line.quantity = line.quant_ids[0].quantity if line.quant_ids else False

    def __str__(self):
        return str(self.product_id.name)


class StockPallet(models.Model):
    """ Pallets containing packs and/or other packages """
    _name = "stock.pallet"
    _description = "Pallets containing packs and/or other packages"
    _order = 'name'

    name = fields.Char('Pallet Reference', copy=False, index=True,
                       default=lambda self: self.env['ir.sequence'].next_by_code('stock.pallet') or _('Unknown Pallet'))
    pack_ids = fields.One2many('stock.quant.package', 'pallet_id', 'Bulk Content')
    barcode = fields.Char(string="Barcode", readonly=True)
    location_id = fields.Many2one('stock.location', 'Location', readonly=True, compute='_compute_package_info')
    quantity = fields.Float(string="Quantity", readonly=True, compute="_compute_weight")
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )
    @api.depends('pack_ids.pallet_id', 'pack_ids.location_id')
    def _compute_package_info(self):
        for package in self:
            values = {'location_id': False, 'owner_id': False}
            if package.pack_ids:
                values['location_id'] = package.pack_ids[0].location_id
            package.location_id = values['location_id']

    def _compute_weight(self):
        for pallet in self:
            pallet_qty = 0
            for p in pallet.pack_ids:
                pallet_qty += p.quantity
            pallet.quantity = pallet_qty

    def _get_contained_packs(self):
        return self.env['stock.quant.package'].search([('pallet_id', 'in', self.ids)])

    def unpack(self):
        for line in self.pack_ids:
            line.write({'pallet_id': False})
        self.unlink()
        action = self.env.ref('fishing_v2.action_pallets_view').read()[0]
        return action
