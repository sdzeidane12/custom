from odoo import fields, models, api, _, tools


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'
    _description = 'Maintenance Equipment'
    type_choices = [('intern', 'Intern'), ('extern', 'Extern')]

    type = fields.Selection(type_choices, string="Type")
    cost_center_id = fields.Integer("Cost center")
    volume = fields.Float("Volume")
    total_reception = fields.Float("Total reception", compute="_compute_total_reception")
    total_income = fields.Float("Total income", compute="_compute_total_income")

    def _compute_total_reception(self):
        for record in self:
            boat_receptions = self.env["fishing.reception"].search([('bateau', '=', record.id)])
            record.total_reception = sum(boat_receptions.mapped('total_received'))

    def _compute_total_income(self):
        for record in self:
            boat_receptions = self.env["fishing.reception"].search([('bateau', '=', record.id)])
            product_prices = []
            for recep in boat_receptions:
                for line in recep.reception_ids:
                    product_prices.append(line.article1.list_price)
            count_prices = len(product_prices) if len(product_prices) > 0 else 1
            record.total_income = (sum(product_prices) / count_prices) * record.total_reception
