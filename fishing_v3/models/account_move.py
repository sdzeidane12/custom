from odoo import fields, models, api, _
from datetime import datetime


class AccountMove(models.Model):
    _inherit = "account.move"

    reception_id = fields.Many2one('fishing.reception', 'Reception', required=False)
    stock_service_id = fields.Many2one('fish.service.stock', 'Service', required=False)


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    lot_id = fields.Many2one('fishing.reception.detail', 'Lot', required=False)
