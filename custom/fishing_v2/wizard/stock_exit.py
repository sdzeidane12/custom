from odoo import fields, models, api, _
from datetime import date, datetime, timedelta
from odoo.exceptions import UserError, ValidationError


class ExitServiceStockWizard(models.TransientModel):
    _name = 'fishing.service.stock.wizard'

    will_invoice = fields.Boolean(string="Invoice", default=False)
    invoice_per = fields.Selection([('week', 'Week'), ('day', 'Day'), ('hour', 'Hour')], default='week',
                                   string="Invoice per", required=True)
    custom_invoice_per = fields.Selection(related="invoice_per",store=True)
    show_pallets = fields.Boolean(string="Pallets", default=False)
    show_boxes = fields.Boolean(string="Packages", default=False)
    start = fields.Datetime(string="Start", default=lambda self: self._context.get('start'))
    end = fields.Datetime(string="End", default=datetime.now())
    total_duration = fields.Float(string="Duration", readonly=True)
    unit_price = fields.Float(string="Unit price")

    @api.onchange('start', 'end', 'invoice_per')
    def onchange_duration(self):
        if self.start and self.end:
            if self.invoice_per == 'hour':
                self.total_duration = (self.end - self.start).total_seconds() // 3600
            if self.invoice_per == 'day':
                self.total_duration = (self.end - self.start).days
            if self.invoice_per == 'week':
                self.total_duration = (self.end - self.start).days / 7

    def action_exit(self):
        act_id = self._context.get('active_id')
        act_model = self._context.get('active_model')
        value = self.env[act_model]
        quantity_data = value.browse(act_id)
        stock_service = self.env.ref('fishing_v2.product_service_stock')
        for pack in quantity_data.pallet_ids:
            pack.write({'is_ready_out': True})
        for pack in quantity_data.box_ids:
            pack.write({'is_ready_out': True})
        exit_vals = {
            "stock_service_id": quantity_data.id,
            "location_id": quantity_data.location_id.id,
            "pallet_id": False,
            "box_id": False,
        }
        #Set Total duration ZERO
        total_duration=0
        #calculate Duration on bases start and end time
        if self.start and self.end:
            if self.invoice_per == 'hour':
                total_duration = (self.end - self.start).total_seconds() // 3600
            if self.invoice_per == 'day':
                total_duration = (self.end - self.start).days
            if self.invoice_per == 'week':
                total_duration = (self.end - self.start).days / 7
        #calculate Totla price On bases of duration and price per unit
        total_price = total_duration*self.unit_price
        #Distribute Total price bases of quantity of palet that pass to invoice
        per_unit_price = (total_duration*self.unit_price)/quantity_data.qte

        self.env["fish.service.stock.exit"].create(exit_vals)
        if not self.will_invoice:
            quantity_data.write({'is_ready_out': True})
            return
        if not stock_service.property_account_income_id:
            raise ValidationError(_("Please set an income account for " + stock_service.name))
        inv_vals = {
            'partner_id': quantity_data.customer_id.id,
            'payment_reference': quantity_data.ref,
            'invoice_date': datetime.today(),
            'move_type': 'out_invoice',
            'state': 'draft',
            'stock_service_id': quantity_data.id
        }

        inv = self.env['account.move'].create(inv_vals)
        context = {'check_move_validity': False}
        inv_line_vals = {
            'product_id': stock_service.id,
            'account_id': stock_service.property_account_income_id.id,
            'quantity': quantity_data.qte,
            'move_id': inv.id,
            'price_unit': per_unit_price,
            #Remove Because there is no need to update subtotal because it's computed fields
            # 'price_subtotal': total_duration*self.unit_price,
            # 'price_total': total_duration*self.unit_price,
        }
        self.with_context(context).env['account.move.line'].create(inv_line_vals)
        stock_debit_line_vals = {
            'account_id': inv.partner_id.property_account_receivable_id.id if inv.partner_id.property_account_receivable_id else False,
            'product_id': stock_service.id,
            'quantity': quantity_data.qte,
            'name': quantity_data.category_id.display_name,
            'move_id': inv.id,
            'price_unit': 0-per_unit_price,
            #Remove Because there is no need to update subtotal because it's computed fields
            # 'price_subtotal': total_duration*self.unit_price,
            # 'price_total': total_duration*self.unit_price,
            'exclude_from_invoice_tab': True,
        }
        self.with_context(context).env['account.move.line'].create(stock_debit_line_vals)
        quantity_data.write({'is_ready_out': True})


class ExitServiceStockContentWizard(models.TransientModel):
    _name = 'stock.content.wizard'

    will_invoice = fields.Boolean(string="Invoice", default=False)
    invoice_per = fields.Selection([('week', 'Week'), ('day', 'Day'), ('hour', 'Hour')], default='week',
                                   string="Invoice per", required=True)
    show_pallets = fields.Boolean(string="Pallets", default=False)
    show_boxes = fields.Boolean(string="Packages", default=False)
    start = fields.Datetime(string="Start", default=lambda self: self._context.get('start'))
    end = fields.Datetime(string="End", default=datetime.now())
    total_duration = fields.Float(string="Duration", compute="_compute_duration")
    unit_price = fields.Float(string="Unit price")
    pallet_ids = fields.Many2many(comodel_name='stock.service.pallet', string='Pallets')
    box_ids = fields.Many2many(comodel_name='fish.service.stock.caisse', string='Packages')
    active_id = fields.Integer(default=lambda self: self._context.get('active_id'))

    @api.onchange('start', 'end', 'invoice_per')
    def _compute_duration(self):
        if self.start and self.end:
            if self.invoice_per == 'hour':
                self.total_duration = (self.end - self.start).total_seconds() // 3600
            if self.invoice_per == 'day':
                self.total_duration = (self.end - self.start).days
            if self.invoice_per == 'week':
                self.total_duration = (self.end - self.start).days / 7

    def action_exit(self):
        act_id = self._context.get('active_id')
        act_model = self._context.get('active_model')
        value = self.env[act_model]
        quantity_data = value.browse(act_id)
        stock_service = self.env.ref('fishing_v2.product_service_stock')
        inv = False

        # raise ValidationError(self.total_duration * self.unit_price)

        if self.will_invoice:
            if not stock_service.property_account_income_id:
                raise ValidationError(_("Please set an income account for " + stock_service.name))
            inv_vals = {
                'partner_id': quantity_data.customer_id.id,
                'payment_reference': quantity_data.ref,
                'invoice_date': datetime.today(),
                'move_type': 'out_invoice',
                'state': 'draft',
                'stock_service_id': quantity_data.id
            }
            inv = self.env['account.move'].create(inv_vals)
        if self.show_pallets:
            for pal in self.pallet_ids:
                pal.prepare_exit_stock(inv, self.unit_price * self.total_duration)
        else:
            if self.show_boxes:
                for pack in self.box_ids:
                    pack.prepare_exit_stock(inv, self.unit_price * self.total_duration)
