from odoo import fields, models, api, _
from datetime import date, datetime, timedelta


class OperationStopWizard(models.TransientModel):
    _name = 'fishing.operation.stop.wizard'
    operation_choices = [('treatment', 'Treatment'), ('tunnel', 'Freezing'), ('packaging', 'Packaging')]

    start = fields.Datetime(string="Start", default=datetime.now())
    end = fields.Datetime(string="End")
    operation = fields.Selection(operation_choices, string='Operation')
    raison = fields.Char(string="Raison")

    def action_pause(self):
        act_id = self._context.get('active_id')
        act_model = self._context.get('active_model')
        value = self.env[act_model]
        quantity_data = value.browse(act_id)
        stop = {
            'start': datetime.now(),
            'operation': self._context.get('operation'),
            'raison': self.raison
        }
        self.env["fishing.operation.stop"].create(stop)
        quantity_data.update({'is_paused': True})
