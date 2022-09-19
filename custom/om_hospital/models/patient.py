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
    appointment_count = fields.Integer(string="Appointment Counter", compute='_compute_appointment_count')

    # Compute Field and Function
    # ha4i fonction t3adel select 3le model hospital.appointment wt3adel search_count
    # 3an lmerid li 36ythe esmou par son id wte7ssblak 3ndou kem men appointment
    def _compute_appointment_count(self):
        for rec in self:
            rec.appointment_count = self.env['hospital.appointment'].search_count([('patient_id', '=', rec.id)])

    #     end Compute  Function

    def action_confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

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

    @api.model
    def default_get(self, fields):
        vals = super(HospitalPatient, self).default_get(fields)
        vals['age'] = 34
        return vals
