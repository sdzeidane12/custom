# -*- coding: utf-8 -*-
from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    sale_description = fields.Char(string='sale description')
