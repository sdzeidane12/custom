from io import BytesIO
from odoo.exceptions import UserError, ValidationError
from odoo import fields, models, api, _
from datetime import datetime
import qrcode
import base64


class Da(models.Model):
    _name = 'fishing.reception'
    _rec_name = 'ref'

    def get_types(self):
        types = []
        if self.env.company.has_reception:
            types.append(('production', 'Production'))
        if self.env.company.has_service:
            types.append(('service', 'Service'))
        if not self.env.company.has_service and not self.env.company.has_reception:
            types.append(('production', 'Production'))
            types.append(('service', 'Service'))
        return types

    def get_first(self):
        first = self.get_types()
        return first[0][0]

    status_choices = [
        ('0', 'Waiting for treatment'),
        ('1', 'Treatment in progress'),
        ('2', 'Treated'),
        ('3', 'Tunnels in progress'),
        ('4', 'Tunneled'),
        ('5', 'Packaging in progress'),
        ('6', 'Packed'),

    ]
    ref = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))

    qr_code = fields.Binary("QR Code", attachment=True, readonly=True)

    type = fields.Selection(get_types, string='Type', required=True, tracking=True,
                            default=lambda self: self.get_first())

    status = fields.Selection(status_choices, required=False, default='0', tracking=True)

    mareyeur = fields.Many2one(comodel_name='res.partner', string='Fish seller')

    customer_id = fields.Many2one(comodel_name='res.partner', string='Customer')

    responsible_id = fields.Many2one(comodel_name='res.users', string='Responsible',
                                     default=lambda self: self.env.user.id)

    team_id = fields.Many2one(comodel_name='maintenance.team', string='Team')

    bateau = fields.Many2one(comodel_name='maintenance.equipment', string='Boat', required=False)

    date = fields.Datetime(string='Date', required=False, default=fields.Datetime.now)

    treatment_ordered = fields.Boolean(string='Treatment', required=False, default=False)

    tunnel_ordered = fields.Boolean(string='Tunnel', required=False, default=False)

    packaging_ordered = fields.Boolean(string='Packaging', required=False, default=False)
    ordered_temp = fields.Float(string='Temperature', required=False, default=0.0)
    exp_payment = fields.Float(string="Expected payment", compute="_compute_payment", default=0.0)
    total_received = fields.Float(string="Total", compute="_compute_total")
    act_payment = fields.Float(string="Actual payment", compute="_compute_payment", default=0.0)
    canceled = fields.Boolean(string="Canceled")
    active = fields.Boolean(string="active", default=True)
    cancelable = fields.Boolean(string="Can be canceled", compute="_compute_cancelable")
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )
    # provisional
    reception_ids = fields.One2many(
        comodel_name='reception.fish.detail',
        inverse_name='reception_id1',
        string='Details',
        required=True)

    reception_ids1 = fields.One2many(
        comodel_name='fishing.reception.detail',
        inverse_name='reception_id',
        string='Details',
        required=True)
    direct_charges = fields.Many2many(comodel_name='fishing.cost.direct', string='Direct charges')


    @api.model
    def create(self, vals):
        context = {'check_move_validity': False}

        if vals.get('ref', _('New')) == _('New'):
            vals['ref'] = self.env['ir.sequence'].next_by_code('fish.reception') or _('New')

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(vals.get('ref'))
        qr.make(fit=True)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        qr_image = base64.b64encode(temp.getvalue())
        vals['qr_code'] = qr_image

        result = super(Da, self).create(vals)

        details = self.env["fishing.reception.detail"].search([('reception_id', '=', result.id)])
        stock_location = self.env['stock.location'].search([('name', 'ilike', 'Temporary')])
        get_inventory = self.env['stock.quant']
        attribute_record = self.env.ref('fishing_v2.product_attribute_quality')
        quality_scum_attribute_record = self.env.ref('fishing_v2.product_attribute_value_quality_scum')

        for line in details:
            line.update({
                'type': result.type,
                'treatment_ordered': result.treatment_ordered if result.type == 'service' else True,
                'will_be_tunneled': result.tunnel_ordered if result.type == 'service' else True,
                'ordered_temp': result.ordered_temp,
                'packaging_ordered': result.packaging_ordered if result.type == 'service' else True
            })

            product_template = line.article

            # check if the attr 'Quality' has value = to product qlty
            val_exists = False
            for val in attribute_record.value_ids:
                if val.name == str(line.quality.code):
                    # val exists in attr values
                    val_exists = True
                    break
            # Create value for the attr Quality
            if not val_exists:
                value = [(0, 0, {'name': str(line.quality.code)})]
                attribute_record.write({'value_ids': value})

            # check if the product template has variant attr 'Quality'
            product_template_has_qty_att = False
            if product_template.attribute_line_ids:
                for attr in product_template.attribute_line_ids:
                    if attr.attribute_id.id == attribute_record.id:
                        # Product already has Quality attr
                        product_template_has_qty_att = True
                        # Now we'll Check if attribute value is available  for this product
                        val_exists_product = False
                        for attr_val in attr.value_ids:
                            if attr_val.name == str(line.quality.code):
                                # Now we know value exists in the attr values for this product
                                val_exists_product = True
                                break
                        if not val_exists_product:
                            for val in attribute_record.value_ids:
                                if val.name == str(line.quality.code):
                                    attr.value_ids += val
                                    break
            if not product_template_has_qty_att:
                varient_value = ''
                for record in attribute_record.value_ids:
                    if record.name == str(line.quality.code):
                        varient_value = record
                        break

                create_attribut_line = [(0, 0, {'attribute_id': attribute_record.id, 'value_ids': varient_value})]
                product_template.write({'attribute_line_ids': create_attribut_line})

        if vals.get('type') == 'production':

            bill_vals = {
                'reception_id': result.id,
                'partner_id': result.mareyeur.id or False,
                'payment_reference': result.ref,
                'invoice_date': datetime.today(),
                'move_type': 'in_invoice',
                'state': 'draft',
            }
            bill = self.env['account.move'].create(bill_vals)

            if bill:

                for line in details:

                    product_template = line.article
                    product_product = False
                    product_product_scum = False

                    get_product_with_attribute = self.env['product.product'].search(
                        [('product_tmpl_id', '=', line.article.id)])

                    for variant in get_product_with_attribute:
                        for attribute in variant.product_template_attribute_value_ids:
                            if attribute.name == line.quality.name:
                                product_product = variant
                                break
                    if not product_product:
                        raise ValidationError(_("Unable to get the product "))

                    bill_credit_line_vals = {
                        'product_id': product_product.id if product_product else None,
                        'account_id': product_product.property_account_expense_id.id if product_product.property_account_expense_id else False,
                        'quantity': line.qte,
                        'name': product_product.display_name,
                        'move_id': bill.id,
                        'price_unit': product_product.list_price,
                        'price_subtotal': product_product.list_price * line.qte,
                        'price_total': product_product.list_price * line.qte,
                    }
                    bill_debit_line_vals = {
                        'product_id': product_product.id,
                        'account_id': bill.partner_id.property_account_payable_id.id if bill.partner_id.property_account_payable_id else False,
                        'quantity': line.qte,
                        'name': product_product.display_name,
                        'move_id': bill.id,
                        'price_unit': product_product.list_price,
                        'price_subtotal': product_product.list_price * line.qte,
                        'credit': product_product.list_price * line.qte,
                        'exclude_from_invoice_tab': True,
                    }

                    self.with_context(context).env['account.move.line'].create(bill_credit_line_vals)
                    self.with_context(context).env['account.move.line'].create(bill_debit_line_vals)
                    if line.scum_qty > 0:
                        scum_val_exists = False
                        for val in attribute_record.value_ids:
                            if val.id == quality_scum_attribute_record.id:
                                # val exists in attr values
                                scum_val_exists = True
                                break
                        # Create value for the attr Quality
                        if not scum_val_exists:
                            value = [(0, 0, {'name': quality_scum_attribute_record.name})]
                            attribute_record.write({'value_ids': value})

                        if product_template.attribute_line_ids:
                            for attr in product_template.attribute_line_ids:
                                if attr.attribute_id.id == attribute_record.id:
                                    # Product already has Quality attr
                                    # Now we'll Check if attribute value is available  for this product
                                    val_scum_exists_product = False
                                    for attr_val in attr.value_ids:
                                        if attr_val.name == quality_scum_attribute_record.name:
                                            # Now we know value exists in the attr values for this product
                                            val_scum_exists_product = True
                                            break
                                    if not val_scum_exists_product:
                                        for val in attribute_record.value_ids:
                                            if val.name == quality_scum_attribute_record.name:
                                                attr.value_ids += val
                                                break
                        product_variants = self.env['product.product'].search(
                            [('product_tmpl_id', '=', line.article.id)])
                        for variant in product_variants:
                            for attribute in variant.product_template_attribute_value_ids:
                                if attribute.name == quality_scum_attribute_record.name:
                                    product_product_scum = variant

                                    break

                        bill_credit_scum_line_vals = {
                            'product_id': product_product_scum.id,
                            'account_id': line.article.property_account_expense_id.id if line.article.property_account_expense_id else False,
                            'quantity': line.scum_qty,
                            'name': product_product_scum.display_name,
                            'move_id': bill.id,
                            'price_unit': product_product_scum.list_price,
                            'price_subtotal': product_product_scum.list_price * line.scum_qty,
                            'price_total': product_product_scum.list_price * line.scum_qty,
                        }
                        bill_debit_scum_line_vals = {
                            'product_id': product_product_scum.id,
                            'account_id': bill.partner_id.property_account_payable_id.id if bill.partner_id.property_account_payable_id else False,
                            'quantity': line.qte,
                            'name': line.article.display_name,
                            'move_id': bill.id,
                            'price_unit': product_product_scum.list_price,
                            'price_subtotal': product_product_scum.list_price * line.scum_qty,
                            'credit': product_product_scum.list_price * line.scum_qty,
                            'exclude_from_invoice_tab': True,
                        }
                        self.with_context(context).env['account.move.line'].create(bill_credit_scum_line_vals)
                        self.with_context(context).env['account.move.line'].create(bill_debit_scum_line_vals)
        if vals.get('type') == 'service':
            inv_vals = {
                'reception_id': result.id,
                'partner_id': result.customer_id.id or False,
                'payment_reference': result.ref,
                'invoice_date': datetime.today(),
                'move_type': 'out_invoice',
                'state': 'draft',
            }
            inv = self.env['account.move'].create(inv_vals)

            for line in details:
                if result.treatment_ordered:
                    tr_ser = self.env.ref('fishing_v2.product_service_treatment')
                    if not tr_ser.property_account_income_id or not tr_ser.property_account_expense_id:
                        raise ValidationError(_("Please set an income/expense account for " + tr_ser.name))
                    tr_credit_line_vals = {
                        'product_id': tr_ser.id,
                        'account_id': tr_ser.property_account_income_id.id if tr_ser.property_account_income_id else False,
                        'quantity': line.qte,
                        'name': line.article.display_name,
                        'move_id': inv.id,
                        'price_unit': tr_ser.list_price,
                        'price_subtotal': tr_ser.list_price * line.qte,
                        'price_total': tr_ser.list_price * line.qte,
                    }
                    self.with_context(context).env['account.move.line'].create(tr_credit_line_vals)
                    tr_debit_line_vals = {
                        'account_id': inv.partner_id.property_account_receivable_id.id if inv.partner_id.property_account_receivable_id else False,
                        'product_id': tr_ser.id,
                        'quantity': line.qte,
                        'name': line.article.display_name,
                        'move_id': inv.id,
                        'price_unit': tr_ser.list_price,
                        'price_subtotal': tr_ser.list_price * line.qte,
                        'debit': tr_ser.list_price * line.qte,
                        'exclude_from_invoice_tab': True,
                    }
                    self.with_context(context).env['account.move.line'].create(tr_debit_line_vals)
                if result.tunnel_ordered:
                    # if not result.treatment_ordered:
                    # line.write({'status': '2'})
                    tn_serv = self.env.ref('fishing_v2.product_service_tunnel')
                    if not tn_serv.property_account_income_id:
                        raise ValidationError(_("Please set an income account for " + tn_serv.name))
                    tn_line_vals = {
                        'product_id': tn_serv.id,
                        'account_id': tn_serv.property_account_income_id.id if tn_serv.property_account_income_id else False,
                        'quantity': line.qte,
                        'name': line.article.display_name,
                        'move_id': inv.id,
                        'price_unit': tn_serv.list_price,
                        'price_subtotal': tn_serv.list_price * line.qte,
                        'price_total': tn_serv.list_price * line.qte,
                    }
                    self.with_context(context).env['account.move.line'].create(tn_line_vals)
                    tn_debit_line_vals = {
                        'account_id': inv.partner_id.property_account_receivable_id.id if inv.partner_id.property_account_receivable_id else False,
                        'product_id': tn_serv.id,
                        'quantity': line.qte,
                        'name': line.article.display_name,
                        'move_id': inv.id,
                        'price_unit': tn_serv.list_price,
                        'price_subtotal': tn_serv.list_price * line.qte,
                        'debit': tn_serv.list_price * line.qte,
                        'exclude_from_invoice_tab': True,
                    }
                    self.with_context(context).env['account.move.line'].create(tn_debit_line_vals)
                if result.packaging_ordered:
                    # if not result.treatment_ordered and not result.tunnel_ordered:
                    # line.write({'status': '4'})
                    pk_serv = self.env.ref('fishing_v2.product_service_packaging')
                    if not pk_serv.property_account_income_id:
                        raise ValidationError(_("Please set an income account for " + pk_serv.name))
                    pk_line_vals = {
                        'product_id': pk_serv.id,
                        'account_id': pk_serv.property_account_income_id.id if pk_serv.property_account_income_id else False,
                        'quantity': line.qte,
                        'name': line.article.display_name,
                        'move_id': inv.id,
                        'price_unit': pk_serv.list_price,
                        'price_subtotal': pk_serv.list_price * line.qte,
                        'price_total': pk_serv.list_price * line.qte,
                    }
                    self.with_context(context).env['account.move.line'].create(pk_line_vals)
                    pk_debit_line_vals = {
                        'account_id': inv.partner_id.property_account_receivable_id.id if inv.partner_id.property_account_receivable_id else False,
                        'product_id': pk_serv.id,
                        'quantity': line.qte,
                        'name': line.article.display_name,
                        'move_id': inv.id,
                        'price_unit': pk_serv.list_price,
                        'price_subtotal': pk_serv.list_price * line.qte,
                        'debit': pk_serv.list_price * line.qte,
                        'exclude_from_invoice_tab': True,
                    }
                    self.with_context(context).env['account.move.line'].create(pk_debit_line_vals)
        # self.action_print_sheet(result.id)
        return result

    def action_print_sheet(self, rec_id):
        # result = self.env["fishing.reception"].browse(rec_id)
        return self.env.ref("fishing_v2.reception_report").report_action(self, data={})

    @api.onchange("type", "treatment_ordered", "tunnel_ordered", "packaging_ordered", "ordered_temp")
    def _onchange_fields(self):
        if self.reception_ids:
            for line in self.reception_ids:
                line.type1 = self.type
                line.treatment_ordered1 = self.treatment_ordered
                line.tunnel_ordered1 = self.tunnel_ordered
                line.ordered_temp1 = self.ordered_temp
                line.packaging_ordered1 = self.packaging_ordered

    @api.onchange("type")
    def _onchange_type(self):
        if self.type == 'production':
            self.customer_id = False
        if self.type == 'service':
            self.mareyeur = False

    def _compute_payment(self):
        for recep in self:
            if recep.type == 'service':
                total_exp = 0
                total_act = 0
                for line in recep.reception_ids1:
                    if recep.treatment_ordered:
                        total_exp = total_exp + (
                                line.qte * self.env.ref('fishing_v2.product_service_treatment').list_price)
                    if recep.tunnel_ordered:
                        total_exp = total_exp + (
                                line.qte * self.env.ref('fishing_v2.product_service_tunnel').list_price)
                    if recep.packaging_ordered:
                        total_exp = total_exp + (
                                line.qte * self.env.ref('fishing_v2.product_service_packaging').list_price)

                recep.exp_payment = total_exp

                invs = self.env["account.move"].search(
                    [
                        ("reception_id", "=", recep.id),
                        ("move_type", "=", "out_invoice"),
                        ("state", "in", ["posted"]),
                    ]
                )
                recep.act_payment = sum(invs.mapped("amount_total")) or 0.0


            else:
                recep.exp_payment = 0
                recep.act_payment = 0

    def _compute_total(self):
        for record in self:
            self.total_received = sum(record.reception_ids.mapped("qte1")) + sum(
                record.reception_ids.mapped("scum_qty1"))

    def action_cancel(self):
        self.canceled = True
        self.active = False
        details = self.env["fishing.reception.detail"].search([('reception_id', '=', self.id)])
        for line in details:
            line.active = False

    def _compute_cancelable(self):
        for rec in self:
            rec.cancelable = True
            for line in rec.reception_ids1:
                if line.status != '0':
                    rec.cancelable = False
                    break
