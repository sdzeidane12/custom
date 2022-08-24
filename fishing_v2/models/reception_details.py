from odoo import fields, models, api, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class ReceptionDetail(models.Model):
    _name = 'fishing.reception.detail'
    _rec_name = 'ref'
    _inherit = ['mail.thread', 'mail.activity.mixin', ]

    status_choices = [
        ('0', 'Waiting for treatment'),
        ('1', 'Treatment in progress'),
        ('2', 'Treated'),
        ('3', 'Tunnels in progress'),
        ('4', 'Tunneled'),
        ('5', 'Packaging in progress'),
        ('6', 'Packed'),
    ]

    type_choices = [('production', 'Production'), ('service', 'Service')]

    ref = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    reception_id = fields.Many2one(comodel_name='fishing.reception', string='Reception', required=False)
    lot_id = fields.Many2one(comodel_name='fishing.reception.detail', string='Lot', required=False)
    customer_id = fields.Many2one(comodel_name='res.partner', string='Customer', compute="_compute_type")
    mareyeur = fields.Many2one(comodel_name='res.partner', string='Fish seller', compute="_compute_type")
    type = fields.Selection(type_choices, string='Type', required=True, compute="_compute_type")
    article = fields.Many2one(comodel_name='product.template', string='Product', required=False)
    quality = fields.Many2one(comodel_name='fishing.quality', string='Quality',required=True)

    qte = fields.Float(string='Quantity', required=False)
    status = fields.Selection(status_choices, required=False, default='0', tracking=True)
    process_qty = fields.Float(string='Processed Quantity', required=False)
    scum_qty = fields.Float(string='Scum Quantity', required=False)
    is_new = fields.Boolean(default="False")
    is_paused = fields.Boolean(default=False)

    treatment_ordered = fields.Boolean(string='Treatment', required=False, default=False)
    startdate = fields.Datetime(string='Treatment start date', required=False, tracking=True)
    end_date = fields.Datetime(string='Treatment end date', required=False, tracking=True)
    treatment_responsible_id = fields.Many2one(comodel_name='res.users', string='Treatment Responsible',
                                               default=lambda self: self.env.user.id)
    treatment_team_id = fields.Many2one(comodel_name='maintenance.team', string='Treatment Team',
                                        domain="[('id','=','0')]")
    treatment_scum_qty = fields.Float(string='Treatment Scum', required=False)
    treatment_films_qty = fields.Float(string='Used films', required=False, default=0.0)

    will_be_tunneled = fields.Boolean(default=False, string="Frozen")
    tunnel_id = fields.Many2one(comodel_name='fishing.tunnel', string='Tunnel')
    tunnel_start_date = fields.Datetime(string='Tunnel start date', required=False)
    tunnel_end_date = fields.Datetime(string='Tunnel end date', required=False)
    tunnel_responsible_id = fields.Many2one(comodel_name='res.users', string='Freezing Responsible',
                                            default=lambda self: self.env.user.id)
    tunnel_team_id = fields.Many2one(comodel_name='maintenance.team', string='Freezing Team', domain="[('id','=','0')]")
    ordered_temp = fields.Float(string='Temperature', required=False, default=0.0)
    exit_temp = fields.Float(string='Exit temperature', required=False, default=0.0)
    tunnel_scum_qty = fields.Float(string='Tunnel Scum', required=False)

    packaging_ordered = fields.Boolean(string='Packaging', required=False, default=False)
    paking_start_date = fields.Datetime(string='Packaging start date', required=False)
    paking_end_date = fields.Datetime(string='Packaging end date', required=False)
    paking_responsible_id = fields.Many2one(comodel_name='res.users', string='Packaging Responsible',
                                            default=lambda self: self.env.user.id)
    paking_team_id = fields.Many2one(comodel_name='maintenance.team', string='Packaging Team')
    paking_scum_qty = fields.Float(string='Packaging Scum', required=False)
    used_boxes = fields.Float(string='Used boxes', required=False)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )
    tr_canceled = fields.Boolean(string="Canceled")
    tr_cancelable = fields.Boolean(string="Can be canceled", compute="_compute_tr_cancelable")
    tn_canceled = fields.Boolean(string="Canceled")
    tn_cancelable = fields.Boolean(string="Can be canceled", compute="_compute_tn_cancelable")
    active = fields.Boolean(string="active", default=True)

    def _compute_tr_cancelable(self):
        for rec in self:
            rec.tr_cancelable = True
            lot_lines = self.env['fishing.reception.detail'].search(
                [('reception_id', '=', rec.reception_id.id), ('lot_id', '=', rec.id)])
            for line in lot_lines:
                if line.status not in ['0', '1', '2']:
                    rec.tr_cancelable = False
                    break

    def _compute_tn_cancelable(self):
        for rec in self:
            rec.tn_cancelable = True
            lot_lines = self.env['fishing.reception.detail'].search(
                [('reception_id', '=', rec.reception_id.id), ('lot_id', '=', rec.id)])
            for line in lot_lines:
                if line.status not in ['5', '6']:
                    rec.tn_cancelable = False
                    break

    @api.model
    def create(self, vals):
        if vals.get('ref', _('New')) == _('New'):
            vals['ref'] = self.env['ir.sequence'].next_by_code('fish.reception.detail') or _('New')
        result = super(ReceptionDetail, self).create(vals)

        return result

    def _compute_type(self):
        for line in self:
            line.type = line.reception_id.type if line.reception_id else line.type
            line.customer_id = line.reception_id.customer_id
            line.mareyeur = line.reception_id.mareyeur
            line.treatment_ordered = line.reception_id.treatment_ordered if line.reception_id.type == 'service' else True

    def start_traitement(self):
        view_id = self.env.ref('fishing_v2.new_qty_form_view')

        return {
            'name': _('New treatment'),
            'res_model': 'fishing.reception.getqty',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'type': 'ir.actions.act_window',
            'context': {
                'qte': self.qte,
                'ordered_temp': self.ordered_temp,
                'remaining_quantity': self.qte,
                'default_default_categ_id': False,
                'product_id': False,
            }
        }

    def validate_treatment(self):
        view_id = self.env.ref('fishing_v2.fishing_validate_treatment_form_view')

        return {
            'name': _('Treatment validation'),
            'res_model': 'fishing.reception.validateqty',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'type': 'ir.actions.act_window',
            'context': {'treated_qty': self.qte, 'will_be_tunneled': self.will_be_tunneled}
        }

    def start_tunnel(self):
        view_id = self.env.ref('fishing_v2.new_tunnel_qty_form_view')

        return {
            'name': _('New freezing operation'),
            'res_model': 'fishing.reception.getqty',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'type': 'ir.actions.act_window',
            'context': {
                'qte': self.qte,
                'ordered_temp': self.ordered_temp,
                'remaining_quantity': self.qte,
                'default_default_categ_id': False,
                'product_id': self.article.id,

            }
        }

    def validate_tunnel(self):
        if self.type == 'service':
            if not self.packaging_ordered:
                service_stock_obj = self.env["fish.service.stock"]

                line = service_stock_obj.search(
                    [('customer_id', '=', self.customer_id.id),
                     ('category_id', '=', self.article.id)])
                if line:
                    line[0].write({'qte': line.qte + self.qte})
                else:
                    line_vals = {
                        'customer_id': self.customer_id.id,
                        'category_id': self.article.id,
                        'product_id': False,
                        'qte': self.qte,
                        'receive_date': datetime.now(),
                    }
                    line_create = service_stock_obj.create(line_vals)

        self.write({'tunnel_end_date': datetime.now(), 'status': '4'})

    def pause_operation(self):
        view_id = self.env.ref('fishing_v2.reception_pause_form_view')
        operation = ""
        if self.status == '1':
            operation = "treatment"
        elif self.status == '3':
            operation = 'tunnel'
        elif self.status == '5':
            operation = 'packaging'
        return {
            'name': _(operation.capitalize() + ' pause'),
            'res_model': 'fishing.operation.stop.wizard',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'type': 'ir.actions.act_window',
            'context': {
                'active_model': 'fishing.reception.detail',
                'active_ids': self.ids,
                'operation': operation
            }
        }

    def resume_operation(self):

        operation = ""
        if self.status == '1':
            operation = "treatment"
        elif self.status == '3':
            operation = 'tunnel'
        elif self.status == '5':
            operation = 'packaging'

        stop_object = self.env["fishing.operation.stop"].search([('operation', '=', operation)],
                                                                order='create_date desc', limit=1)
        if stop_object:
            stop_object.update({'end': datetime.now()})
        self.update({'is_paused': False})

    def start_packaging(self):
        view_id = self.env.ref('fishing_v2.reception_get_qty_form_view')

        # products = self.env['product.product'].search([
        #     ('product_tmpl_id', '=', self.article.id)])
        # product_id = False
        # if not products:
        #     raise ValidationError("Can't find variants for product")
        # for p in products:
        #     for var in p.product_template_attribute_value_ids:
        #         if var.name == self.quality.name:
        #             product_id = p.id
        #     if product_id:
        #         break

        return {
            'name': _('Product creation'),
            'res_model': 'fishing.reception.getqty',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'flags': {'form': {'action_buttons': False}},
            'context': {
                'active_model': 'fishing.reception.detail',
                'active_ids': self.ids,
                'default_default_categ_id': self.article.id,
                'product_id': False,
                'qte': self.qte,
                'quality_code': self.quality.code,
                'remaining_quantity': self.qte,
                'ordered_temp': self.ordered_temp,
                'is_production': True if self.type == 'production' else False
            }
        }

    def start_manual_packaging(self):
        view_id = self.env.ref('fishing_v2.manual_packing_form_view')

        return {
            'name': _('Manual packing'),
            'res_model': 'manual.packing',
            'view_mode': 'form',
            'target': 'new',
            'view_id': view_id.id,
            'type': 'ir.actions.act_window',
            'context': {
                'active_model': 'fishing.reception.detail',
                'active_ids': self.ids,
                'product_id': self.article.id,
                'qnty': self.qte,
                'default_default_categ_id': self.article.id,
            }
        }

    def action_cancel_tr(self):
        self.status = '0'

    def action_cancel_tn(self):
        self.status = '2'


class OperationStop(models.Model):
    _name = 'fishing.operation.stop'

    operation_choices = [('treatment', 'Treatment'), ('tunnel', 'Freezing'), ('packaging', 'Packaging')]

    start = fields.Datetime(string="Start", default=datetime.now())
    end = fields.Datetime(string="End")
    operation = fields.Selection(operation_choices, string='Operation')
    raison = fields.Char(string="Raison")
