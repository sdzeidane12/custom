from odoo import fields, models, api, _, tools


class MaintenanceEquipment(models.Model):
    _inherit = 'res.company'

    has_reception = fields.Boolean("Has production")
    has_service = fields.Boolean("Hsa service")
