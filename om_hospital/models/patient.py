# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HospitalPatient(models.Model):
    _name = "hospital.patient"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Hospital Patient"

    name = fields.Char(string='name', required=True, tracking=True)
    #  sequence field :
    reference = fields.Char(string='Order Reference', required=True, copy=False, readonly=True,
                            default=lambda self: _('New'))
    ref = fields.Char(string='ref')
    age = fields.Integer(string='age', tracking=True)

    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], required=True, default='Male')

    note = fields.Text(string='description')

    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirmed'),
                              ('done', 'Done'),
                              ('cancel', 'Cancelled')], default="draft", string="status", tracking=True)

    responsible_id = fields.Many2one('res.partner', string="Responsible")

    def action_confirm(self):
        self.state = 'confirm'

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    # ha4i function 3ndhe rwayteyn t3adlhm w7de t5rs kan note vid l3adt vid dir vihe "New Patient"
    # thanye t5aras kan reference vihe new pardefault wleyn t3oud vihe dir hiye vblhe le prefix (HP00)
    #
    @api.model
    def create(self, vals):
        if not vals.get('note'):
            vals['note'] = "New Patient"
        if vals.get('reference', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code('mysequence') or _('New')
        return super(HospitalPatient, self).create(vals)
