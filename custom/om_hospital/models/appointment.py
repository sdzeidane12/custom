# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class HospitalAppointment(models.Model):
    _name = "hospital.appointment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Hospital Aappointment"

    name = fields.Char(string='Order Reference', required=True, copy=False, readonly=True,
                       default=lambda self: _('New'))
    # Related Field In Odoo:
    patient_id = fields.Many2one('hospital.patient', string="Patient", required=True)
    # end related
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], string='Gender')
    age = fields.Integer(string='age', related='patient_id.age', tracking=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('confirm', 'Confirmed'),
                              ('done', 'Done'),
                              ('cancel', 'Cancelled')], default="draft", string="status", tracking=True)
    note = fields.Text(string='description')
    date_appointment = fields.Date(string='Date')
    date_checkup = fields.Datetime(string="Check Up Time")

    def action_confirm(self):
        self.state = 'confirm'

    def action_done(self):
        self.state = 'done'

    def action_draft(self):
        self.state = 'draft'

    def action_cancel(self):
        self.state = 'cancel'

    @api.model
    def create(self, vals):
        if not vals.get('note'):
            vals['note'] = "New Patient"
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('msequence') or _('New')
        return super(HospitalAppointment, self).create(vals)

    # 4i function t5ras kan patient_id vih chi wt5ras kan gender li v patient_id vih chi aleyn y3oud vihm chi lthneyn
    # tegba8 Gender wdir vihe 4ak li v gnder patient_id
    @api.onchange('patient_id')
    def onchange_patient_id(self):
        if self.patient_id:
            if self.patient_id.gender:
                self.gender = self.patient_id.gender
            if self.patient_id.note:
                self.note = self.patient_id.note
        else:
            self.gender = ''
            self.note = ''
