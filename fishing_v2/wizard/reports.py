import datetime

from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _
from datetime import date
import datetime as dt
import math
from odoo.exceptions import UserError, ValidationError, RedirectWarning


def truncate(number, decimals=0):
    """
    Returns a value truncated to a specific number of decimal places.
    """
    if decimals == 0:
        return math.trunc(number)
    if (number).is_integer():
        return int(number)

    factor = 10.0 ** decimals
    return math.trunc(number * factor) / factor


class DayReportWizard(models.TransientModel):
    _name = 'production.day.report.wizard'
    type_choices = [('all', 'All'), ('production', 'Production'), ('service', 'Service')]

    day = fields.Date(string='Day', default=date.today())
    target = fields.Selection(type_choices, string='Target', default='all')

    def action_print_report(self):
        today_start = str(self.day) + " " + "00:00:00"
        today_end = str(self.day) + " " + "23:59:59"
        records = self.env["fishing.reception.detail"].search(
            [('create_date', '>=', today_start), ('create_date', '<=', today_end)])
        stops = self.env["fishing.operation.stop"].search(
            [('create_date', '>=', today_start), ('create_date', '<=', today_end)])
        times = self.env["fishing.time"].search([])
        tr_time = 0.0
        tn_time = 0.0
        pk_time = 0.0
        if times and len(times) > 2:
            tr_time = self.env["fishing.time"].search([('operation', '=', 'treatment')])
            tn_time = self.env["fishing.time"].search([('operation', '=', 'tunnel')])
            pk_time = self.env["fishing.time"].search([('operation', '=', 'packaging')])

        if self.target == 'production':
            records = self.env["fishing.reception.detail"].search([
                ('create_date', '>=', today_start),
                ('create_date', '<=', today_end),
                ('type', '=', 'production')
            ])
        if self.target == 'service':
            records = self.env["fishing.reception.detail"].search([
                ('create_date', '>=', today_start),
                ('create_date', '<=', today_end),
                ('type', '=', 'service')
            ])

        records_data = []
        stops_data = []
        totals = {
            'treatment_scum_qty': 0,
            'treatment_films_qty': 0,
            'used_boxes': 0,
            'packed_qty': 0,
            'received_qty': 0,
        }
        working_time = datetime.timedelta(hours=8)
        quality_rates = []
        performance_rates = []

        total_stop_period = datetime.timedelta()

        for rec in records:
            rec_data = {
                'treatment_scum_qty': rec.treatment_scum_qty + rec.scum_qty,
                'treatment_films_qty': rec.treatment_films_qty,
                'used_boxes': rec.used_boxes,
                'packed_qty': 0,
                'received_qty': rec.qte + rec.process_qty,
                'type': rec.type,
                'product': rec.article.display_name,
                'create_date': rec.create_date
            }
            totals['treatment_scum_qty'] += (rec.treatment_scum_qty + rec.scum_qty)
            totals['treatment_films_qty'] += rec.treatment_films_qty
            totals['used_boxes'] += rec.used_boxes
            totals['packed_qty'] += 0
            totals['received_qty'] += (rec.qte + rec.process_qty + rec.scum_qty)

            records_data.append(rec_data)

            rec_quality_rate = ((rec.qte - (rec.treatment_scum_qty + rec.scum_qty)) * 100) / (rec.qte + rec.process_qty)
            quality_rates.append(rec_quality_rate)
            if times and len(times) > 2:
                rec_tr_performance = 100
                rec_tn_performance = 100
                rec_pk_performance = 100
                if rec.startdate and rec.end_date:
                    theory_kg_time = tr_time.time / tr_time.quantity
                    theory_rec_time = theory_kg_time * (rec.qte + rec.process_qty)
                    real_time = rec.end_date - rec.startdate
                    seconds = real_time.seconds
                    real_time = (seconds % 3600) // 60
                    rec_tr_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                if rec.tunnel_start_date and rec.tunnel_end_date:
                    theory_kg_time = tn_time.time / tn_time.quantity
                    theory_rec_time = theory_kg_time * (rec.qte + rec.process_qty)
                    real_time = rec.tunnel_end_date - rec.tunnel_start_date
                    seconds = real_time.seconds
                    real_time = (seconds % 3600) // 60
                    rec_tn_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                if rec.paking_start_date and rec.paking_end_date:
                    theory_kg_time = pk_time.time / pk_time.quantity
                    theory_rec_time = theory_kg_time * (rec.qte + rec.process_qty)
                    real_time = rec.paking_end_date - rec.paking_start_date
                    seconds = real_time.seconds
                    real_time = (seconds % 3600) // 60
                    rec_pk_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                rec_performance = (rec_tr_performance + rec_tn_performance + rec_pk_performance) / 3
                performance_rates.append(rec_performance)
        for stop in stops:
            stop_data = {
                'start': stop.start,
                'end': stop.end,
                'operation': stop.operation,
                'raison': stop.raison
            }
            if stop.end:
                total_stop_period += (stop.end - stop.start)
            stops_data.append(stop_data)

        data = {
            'day': self.day,
            'lines': records_data,
            'totals': totals,
            'stops': stops_data,
            'opening_time': working_time,
            'production_time': str(working_time - total_stop_period).split('.')[0],
            'quality_rate': 100 if len(quality_rates) == 0 else truncate(sum(quality_rates) / len(quality_rates), 2),
            'performance_rate': 100 if len(performance_rates) == 0 else truncate(
                sum(performance_rates) / len(performance_rates), 2),
        }
        return self.env.ref("fishing_v2.day_report").report_action(self, data=data)


class MonthReportWizard(models.TransientModel):
    _name = 'production.month.report.wizard'
    type_choices = [('all', 'All'), ('production', 'Production'), ('service', 'Service')]
    months = [('1', 'Jan'), ('2', 'Feb'), ('3', 'Mar'), ('4', 'Apr'), ('5', 'May'), ('6', 'Jun'), ('7', 'Jul'),
              ('8', 'Aug'), ('9', 'Sep'), ('10', 'Oct'), ('11', 'Nov'), ('12', 'Dec')]

    cur_y = dt.datetime.today().year
    cur_m = dt.datetime.today().month
    month = fields.Selection(months, string='Month', default=str(cur_m))
    year = fields.Selection([(str(num), num) for num in range(2020, cur_y + 1)], string='Year', default=str(cur_y))
    target = fields.Selection(type_choices, string='Target', default='all')

    def action_print_report(self):

        year_start = str(self.year) + "-" + str(self.month) + "-01" + " 00:00:00"
        year_end = str(self.year) + "-" + str(self.month) + "-30" + " 23:59:59"
        months_31 = ['1', '3', '5', '7', '8', '10', '12']
        if self.month in months_31:
            year_end = str(self.year) + "-" + str(self.month) + "-31" + " 23:59:59"
        if self.month == '2':
            year_end = str(self.year) + "-" + str(self.month) + "-28" + " 23:59:59"

        records = self.env["fishing.reception.detail"].search(
            [('create_date', '>=', year_start), ('create_date', '<=', year_end)])
        stops = self.env["fishing.operation.stop"].search(
            [('create_date', '>=', year_start), ('create_date', '<=', year_end)])
        times = self.env["fishing.time"].search([])
        tr_time = 0.0
        tn_time = 0.0
        pk_time = 0.0
        if times and len(times) > 2:
            tr_time = self.env["fishing.time"].search([('operation', '=', 'treatment')])
            tn_time = self.env["fishing.time"].search([('operation', '=', 'tunnel')])
            pk_time = self.env["fishing.time"].search([('operation', '=', 'packaging')])

        if self.target == 'production':
            records = self.env["fishing.reception.detail"].search([
                ('create_date', '>=', year_start),
                ('create_date', '<=', year_end),
                ('type', '=', 'production')
            ])
        if self.target == 'service':
            records = self.env["fishing.reception.detail"].search([
                ('create_date', '>=', year_start),
                ('create_date', '<=', year_end),
                ('type', '=', 'service')
            ])

        records_data = []
        stops_data = []
        totals = {
            'treatment_scum_qty': 0,
            'treatment_films_qty': 0,
            'used_boxes': 0,
            'packed_qty': 0,
            'received_qty': 0,
        }
        working_time = datetime.timedelta(hours=8)
        quality_rates = []
        performance_rates = []

        total_stop_period = datetime.timedelta()

        for rec in records:
            rec_data = {
                'treatment_scum_qty': rec.treatment_scum_qty + rec.scum_qty,
                'treatment_films_qty': rec.treatment_films_qty,
                'used_boxes': rec.used_boxes,
                'packed_qty': 0,
                'received_qty': rec.qte + rec.process_qty,
                'type': rec.type,
                'product': rec.article.display_name,
                'create_date': rec.create_date
            }
            totals['treatment_scum_qty'] += (rec.treatment_scum_qty + rec.scum_qty)
            totals['treatment_films_qty'] += rec.treatment_films_qty
            totals['used_boxes'] += rec.used_boxes
            totals['packed_qty'] += 0
            totals['received_qty'] += (rec.qte + rec.process_qty + rec.scum_qty)

            records_data.append(rec_data)

            rec_quality_rate = ((rec.qte - (rec.treatment_scum_qty + rec.scum_qty)) * 100) / (rec.qte + rec.process_qty)
            quality_rates.append(rec_quality_rate)
            if times and len(times) > 2:
                rec_tr_performance = 100
                rec_tn_performance = 100
                rec_pk_performance = 100
                if rec.startdate and rec.end_date:
                    theory_kg_time = tr_time.time / tr_time.quantity
                    theory_rec_time = theory_kg_time * rec.qte
                    real_time = rec.end_date - rec.startdate
                    seconds = real_time.seconds
                    real_time = (seconds % 3600) // 60
                    rec_tr_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                if rec.tunnel_start_date and rec.tunnel_end_date:
                    theory_kg_time = tn_time.time / tn_time.quantity
                    theory_rec_time = theory_kg_time * rec.qte
                    real_time = rec.tunnel_end_date - rec.tunnel_start_date
                    seconds = real_time.seconds
                    real_time = (seconds % 3600) // 60
                    rec_tn_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                if rec.paking_start_date and rec.paking_end_date:
                    theory_kg_time = pk_time.time / pk_time.quantity
                    theory_rec_time = theory_kg_time * rec.qte
                    real_time = rec.paking_end_date - rec.paking_start_date
                    seconds = real_time.seconds
                    real_time = (seconds % 3600) // 60
                    rec_pk_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                rec_performance = (rec_tr_performance + rec_tn_performance + rec_pk_performance) / 3
                performance_rates.append(rec_performance)
        for stop in stops:
            stop_data = {
                'start': stop.start,
                'end': stop.end,
                'operation': stop.operation,
                'raison': stop.raison
            }
            if stop.end:
                total_stop_period += (stop.end - stop.start)
            stops_data.append(stop_data)

        data = {
            'day': str(self.month) + "-" + str(self.year),
            'lines': records_data,
            'totals': totals,
            'stops': stops_data,
            'opening_time': working_time,
            'production_time': str(working_time - total_stop_period).split('.')[0],
            'quality_rate': 100 if len(quality_rates) == 0 else truncate(sum(quality_rates) / len(quality_rates), 2),
            'performance_rate': 100 if len(performance_rates) == 0 else truncate(
                sum(performance_rates) / len(performance_rates), 2),
        }
        return self.env.ref("fishing_v2.day_report").report_action(self, data=data)


class YearReportWizard(models.TransientModel):
    _name = 'production.year.report.wizard'
    type_choices = [('all', 'All'), ('production', 'Production'), ('service', 'Service')]

    cur = dt.datetime.today().year
    year = fields.Selection([(str(num), num) for num in range(2020, cur + 1)], string='Year', default=str(cur))
    target = fields.Selection(type_choices, string='Target', default='all')

    def action_print_report(self):
        year_start = str(self.year) + "-01-01" + " 00:00:00"
        year_end = str(self.year) + "-12-31" + " 23:59:59"

        records = self.env["fishing.reception.detail"].search(
            [('create_date', '>=', year_start), ('create_date', '<=', year_end)])
        stops = self.env["fishing.operation.stop"].search(
            [('create_date', '>=', year_start), ('create_date', '<=', year_end)])
        times = self.env["fishing.time"].search([])
        tr_time = 0.0
        tn_time = 0.0
        pk_time = 0.0
        if times and len(times) > 2:
            tr_time = self.env["fishing.time"].search([('operation', '=', 'treatment')])
            tn_time = self.env["fishing.time"].search([('operation', '=', 'tunnel')])
            pk_time = self.env["fishing.time"].search([('operation', '=', 'packaging')])

        if self.target == 'production':
            records = self.env["fishing.reception.detail"].search([
                ('create_date', '>=', year_start),
                ('create_date', '<=', year_end),
                ('type', '=', 'production')
            ])
        if self.target == 'service':
            records = self.env["fishing.reception.detail"].search([
                ('create_date', '>=', year_start),
                ('create_date', '<=', year_end),
                ('type', '=', 'service')
            ])

        records_data = []
        stops_data = []
        totals = {
            'treatment_scum_qty': 0,
            'treatment_films_qty': 0,
            'used_boxes': 0,
            'packed_qty': 0,
            'received_qty': 0,
        }
        working_time = datetime.timedelta(hours=8)
        quality_rates = []
        performance_rates = []

        total_stop_period = datetime.timedelta()

        for rec in records:
            rec_data = {
                'treatment_scum_qty': rec.treatment_scum_qty + rec.scum_qty,
                'treatment_films_qty': rec.treatment_films_qty,
                'used_boxes': rec.used_boxes,
                'packed_qty': 0,
                'received_qty': rec.qte + rec.process_qty,
                'type': rec.type,
                'product': rec.article.display_name,
                'create_date': rec.create_date
            }
            totals['treatment_scum_qty'] += (rec.treatment_scum_qty + rec.scum_qty)
            totals['treatment_films_qty'] += rec.treatment_films_qty
            totals['used_boxes'] += rec.used_boxes
            totals['packed_qty'] += 0
            totals['received_qty'] += (rec.qte + rec.process_qty + rec.scum_qty)

            records_data.append(rec_data)

            rec_quality_rate = ((rec.qte - (rec.treatment_scum_qty + rec.scum_qty)) * 100) / (rec.qte + rec.process_qty)
            quality_rates.append(rec_quality_rate)
            if times and len(times) > 2:
                rec_tr_performance = 100
                rec_tn_performance = 100
                rec_pk_performance = 100
                if rec.startdate and rec.end_date:
                    theory_kg_time = tr_time.time / tr_time.quantity
                    theory_rec_time = theory_kg_time * (rec.qte + rec.process_qty)
                    real_time = rec.end_date - rec.startdate
                    seconds = real_time.seconds
                    real_time = (seconds % 3600) // 60
                    rec_tr_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                if rec.tunnel_start_date and rec.tunnel_end_date:
                    theory_kg_time = tn_time.time / tn_time.quantity
                    theory_rec_time = theory_kg_time * rec.qte
                    real_time = rec.tunnel_end_date - rec.tunnel_start_date
                    seconds = real_time.seconds
                    real_time = (seconds % 3600) // 60
                    rec_tn_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                if rec.paking_start_date and rec.paking_end_date:
                    theory_kg_time = pk_time.time / pk_time.quantity
                    theory_rec_time = theory_kg_time * (rec.qte + rec.process_qty)
                    real_time = rec.paking_end_date - rec.paking_start_date
                    seconds = real_time.seconds
                    real_time = (seconds % 3600) // 60
                    rec_pk_performance = ((theory_rec_time - (real_time - theory_rec_time)) * 100) / theory_rec_time
                rec_performance = (rec_tr_performance + rec_tn_performance + rec_pk_performance) / 3
                performance_rates.append(rec_performance)
        for stop in stops:
            stop_data = {
                'start': stop.start,
                'end': stop.end,
                'operation': stop.operation,
                'raison': stop.raison
            }
            if stop.end:
                total_stop_period += (stop.end - stop.start)
            stops_data.append(stop_data)

        data = {
            'day': self.year,
            'lines': records_data,
            'totals': totals,
            'stops': stops_data,
            'opening_time': working_time,
            'production_time': str(working_time - total_stop_period).split('.')[0],
            'quality_rate': 100 if len(quality_rates) == 0 else truncate(sum(quality_rates) / len(quality_rates), 2),
            'performance_rate': 100 if len(performance_rates) == 0 else truncate(
                sum(performance_rates) / len(performance_rates), 2),
        }
        return self.env.ref("fishing_v2.day_report").report_action(self, data=data)


class LetterReportWizard(models.TransientModel):
    _name = 'letter.report.wizard'
    letter_id = fields.Many2one(comodel_name='fishing.letter', string='Letter', required=True)
    date = fields.Date(string='Date', default=date.today())

    def action_print_report(self):
        letter = {
            'dir': self.letter_id.dir,
            'title': self.letter_id.title,
            'body': self.letter_id.body,
            'formula': self.letter_id.formula,
        }
        data = {
            'date': self.date,
            'letter': letter
        }
        return self.env.ref("fishing_v2.letter_report").report_action(self, data=data)


class CostReportWizard(models.TransientModel):
    _name = 'cost.report.wizard'
    date_from = fields.Date("Date from", default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date("Date to", default=lambda self: fields.Date.to_string(
        (datetime.datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))

    def action_generate_report(self):
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'total_purchase': 0,
            'total_sale': 0,
            'total_direct_costs': 0,
            'total_indirect_costs': 0,
        }
        report = self.env["fishing.cost.report"].create(data)

        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'fishing.cost.report',
            'res_id': report.id,
            'target': 'current',
        }

    @api.onchange("date_from")
    def onchange_date_to(self):
        self.date_from = self.date_from.replace(day=1)
        self.date_to = self.date_from + relativedelta(months=+1, day=1, days=-1)
