from re import search

from odoo import fields, models, api, _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    qty_available = fields.Float(
        'Quantity/kg', compute='_compute_quantities', search='_search_qty_available',
        digits='Product Unit of Measure', compute_sudo=False,
        help="Current quantity of products.\n"
             "In a context with a single Stock Location, this includes "
             "goods stored at this Location, or any of its children.\n"
             "In a context with a single Warehouse, this includes "
             "goods stored in the Stock Location of this Warehouse, or any "
             "of its children.\n"
             "stored in the Stock Location of the Warehouse of this Shop, "
             "or any of its children.\n"
             "Otherwise, this includes goods stored in any Stock Location "
             "with 'internal' type.")
    count_packages = fields.Integer(string="Packages", readonly=True, compute="_compute_info")
    count_pallets = fields.Integer(string="Pallets", readonly=True, compute="_compute_info")
    is_fish_product = fields.Boolean(default=True, compute='_compute_is_fish')
    categ_display_name = fields.Char(related="categ_id.display_name", default="test")
    default_code = fields.Char(index=False)

    def _compute_info(self):

        for line in self:
            template_variants = self.env['product.product'].search([('product_tmpl_id', '=', line.id)])
            if len(template_variants) > 0:
                line_count_packages = 0
                line_count_pallets = 0
                for rec in template_variants:
                    line_count_packages += rec.count_packages
                    line_count_pallets += rec.count_pallets
                line.count_packages = line_count_packages
                line.count_pallets = line_count_pallets
            else:
                line_packs = self.env['stock.quant.package'].search([])
                line_pallets = self.env['stock.pallet'].search([])
                line_count_packages = 0
                line_count_pallets = 0
                for rec in line_packs:
                    if rec.product_id.id == line.id:
                        line_count_packages += 1
                for pal in line_pallets:
                    if pal.pack_ids and pal.pack_ids[0].product_id.id == line.id:
                        line_count_pallets += 1

    def _compute_is_fish(self):

        for record in self:
            if 'Fish' in record.categ_display_name:
                record.is_fish_product = True
            else:
                record.is_fish_product = False


class ProductProduct(models.Model):
    _inherit = "product.product"

    default_code = fields.Char(index=False)
    count_packages = fields.Integer(string="Packages", readonly=True, compute="_compute_info")
    count_pallets = fields.Integer(string="Pallets", readonly=True, compute="_compute_info")

    def _compute_info(self):

        for line in self:
            line_packs = self.env['stock.quant.package'].search([])
            line_pallets = self.env['stock.pallet'].search([])
            line_count_packages = 0
            line_count_pallets = 0
            for rec in line_packs:
                if rec.product_id.id == line.id:
                    line_count_packages += 1

            for pal in line_pallets:
                if pal.pack_ids and pal.pack_ids[0].product_id.id == line.id:
                    line_count_pallets += 1
            line.count_packages = line_count_packages
            line.count_pallets = line_count_pallets
