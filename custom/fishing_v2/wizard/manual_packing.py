from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class ManualPacking(models.TransientModel):
    _name = 'manual.packing'

    quantity = fields.Integer(string='Quantity', required=True, default=lambda self: self._context['qnty'],
                              readonly=True)
    num_packs = fields.Integer(string='Number of Packs', required=True)

    default_categ_id = fields.Many2one(comodel_name='product.template', string='Template', readonly=True,
                                       default=lambda self: self._context['default_default_categ_id'])
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    internal_packaging = fields.Boolean(string="Internal packaging", default=True)

    def save_product_manually(self):
        if self.num_packs <= 0:
            raise ValidationError("Cannot create 0 packs")

        act_id = self._context.get('active_id')
        act_model = self._context.get('active_model')
        value = self.env[act_model]
        get_inventory = self.env['stock.quant']
        quantity_data = value.browse(act_id)
        stock_location = self.env['stock.location'].search([('name', 'ilike', 'Temporary')])
        pack_weight = self.quantity / self.num_packs
        packaging_pr1 = self.env.ref(
            'fishing_v2.product_product_carton') if (
                quantity_data.will_be_tunneled and quantity_data.tunnel_end_date) else self.env.ref(
            'fishing_v2.product_product_poly')
        if self.internal_packaging and packaging_pr1.qty_available < self.num_packs:
            raise ValidationError(
                "Insufficient packaging boxes in stock\nStock of " + packaging_pr1.name + " is : " + str(
                    packaging_pr1.qty_available))

        package_type = self.env['stock.package.type'].search([('name', '=', 'Caisse')])
        if not package_type and quantity_data.type == 'production':
            package_type = self.env['stock.package.type'].create({
                'name': "Caisse",
            })

        for _ in range(int(self.num_packs)):
            if quantity_data.type == 'production':
                pack = self.env['stock.quant.package'].create({'package_type_id': package_type.id, })
                self.env['stock.quant'].create({
                    'package_id': pack.id,
                    'product_id': self.product_id.id,
                    'quantity': pack_weight,
                    'location_id': self.env['stock.location'].search([('name', 'ilike', 'Temporary')])[0].id
                })
            elif quantity_data.type == 'service':
                service_stock_obj = self.env["fish.service.stock"]

                line = service_stock_obj.search(
                    [('customer_id', '=', quantity_data.customer_id.id),
                     ('is_out', '=', False),
                     ('is_ready_out', '=', False),
                     ('product_id', '=', self.product_id.id)])
                if line:
                    line = line[0]
                    line.write({'qte': line.qte + self.quantity})
                else:
                    line_vals = {
                        'customer_id': quantity_data.customer_id.id,
                        'product_id': self.product_id.id,
                        'qte': self.quantity,
                        'receive_date': datetime.now(),
                    }
                    line = service_stock_obj.create(line_vals)

                new_box = {
                    'customer_id': quantity_data.customer_id.id,
                    'stock_service_id': line.id,
                    'pallet_id': False,
                    'location_id': stock_location.id,
                    'product_id': self.product_id.id,
                    'quantity': pack_weight,
                }
                box_create = self.env["fish.service.stock.caisse"].create(new_box)

        quantity_data.write({
            'paking_start_date': datetime.now(),
            'paking_end_date': datetime.now(),
            'status': '6',
            'qte': 0,
            'process_qty': self.quantity
        })
        if self.internal_packaging:
            quantity_data.update({'used_boxes': quantity_data.used_boxes + self.num_packs})
            product = self.env.ref(
                'fishing_v2.product_product_carton') if quantity_data.tunnel_end_date else self.env.ref(
                'fishing_v2.product_product_poly')

            lines = get_inventory.sudo().search(
                [('product_id', '=', product.id)])
            if lines:
                line = lines[0]
                line.update({'inventory_quantity': line.quantity - self.num_packs})

                line.action_apply_inventory()
