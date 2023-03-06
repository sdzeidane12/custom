import babel
from dateutil.relativedelta import relativedelta
from odoo import fields, models, api, _, tools
from datetime import date, datetime, time


class DirectCost(models.Model):
    _name = "fishing.cost.direct"
    _rec_name = "ref"

    ref = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    name = fields.Char(string='Name', readonly=True)
    date_from = fields.Date("Date from", default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date("Date to", default=lambda self: fields.Date.to_string(
        (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    reception_ids = fields.Many2many(comodel_name='fishing.reception', string='Reception')
    consumable = fields.Float("Consumable", help="Consumable supply")
    workforce = fields.Float("Workforce", help="direct labor cost")
    other_costs = fields.Float("Other costs")
    total = fields.Float(string="Total", compute="_compute_total")
    unit_charge = fields.Float("Unit charge", compute="_compute_unit_charge")
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )
    charge_ids = fields.One2many(
        comodel_name='fishing.cost.direct.charge',
        inverse_name='cost_id',
        string='Direct chrges',
        readonly=True,
        required=True)

    @api.onchange("date_from")
    def onchange_date_to(self):
        self.date_from = self.date_from.replace(day=1)
        self.date_to = self.date_from + relativedelta(months=+1, day=1, days=-1)

    @api.onchange("consumable", "workforce", "other_costs")
    def _onchange_fields(self):
        if self.consumable:
            self.consumable = abs(self.consumable)
        if self.workforce:
            self.workforce = abs(self.workforce)
        if self.other_costs:
            self.other_costs = abs(self.other_costs)

    def _compute_unit_charge(self):
        for record in self:
            unit_charge = 0
            for reception in record.reception_ids:
                for line in reception.reception_ids:
                    line_total = line.qte1 + line.scum_qty1
                    unit_charge += line_total
            record.unit_charge = record.total / unit_charge if unit_charge > 0 else 0

    def _compute_total(self):
        for record in self:
            record.total = record.consumable + record.workforce + record.other_costs

    @api.model
    def create(self, vals):
        if vals.get('ref', _('New')) == _('New'):
            vals['ref'] = self.env['ir.sequence'].next_by_code('fishing.cost.direct') or _('New')
        if vals.get('date_from') and vals.get('date_to'):
            date_from, date_to = vals.get('date_from'), vals.get('date_to')
            ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
            locale = self.env.context.get('lang') or 'en_US'

            name = _('Direct charges for %s') % (
                tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))
            vals['name'] = name

        charge = super(DirectCost, self).create(vals)
        for reception in charge.reception_ids:
            for line in reception.reception_ids:
                self.env["fishing.cost.direct.charge"].create({
                    'cost_id': charge.id,
                    'reception_line_id': line.id,
                    'quantity': line.qte1 + line.scum_qty1
                })
        return charge


class DirectCostCharges(models.Model):
    _name = "fishing.cost.direct.charge"

    cost_id = fields.Many2one(comodel_name='fishing.cost.direct', string='Cost')
    reception_line_id = fields.Many2one(comodel_name='reception.fish.detail', string='Reception line')
    product = fields.Char(string='Product', related='reception_line_id.article1.display_name')
    quantity = fields.Float("Quantity")
    charge = fields.Float("Charge", compute="_compute_charge")
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )

    def _compute_charge(self):
        for record in self:
            record.charge = record.cost_id.unit_charge * record.quantity


class IndirectCost(models.Model):
    _name = "fishing.cost.indirect"
    _rec_name = "ref"

    ref = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    name = fields.Char(string='Name', readonly=True)
    date_from = fields.Date("Date from", default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date("Date to", default=lambda self: fields.Date.to_string(
        (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    salary = fields.Float("Salary")
    electricity = fields.Float("Electricity")
    water = fields.Float("Water")
    other_charges = fields.Float("Other costs")
    total = fields.Float("Total", compute="_compute_total")
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )

    @api.onchange("date_from")
    def onchange_date_to(self):
        self.date_from = self.date_from.replace(day=1)
        self.date_to = self.date_from + relativedelta(months=+1, day=1, days=-1)

    @api.onchange("salary", "electricity", "water", "other_charges")
    def _onchange_fields(self):
        if self.salary:
            self.salary = abs(self.salary)
        if self.electricity:
            self.electricity = abs(self.electricity)
        if self.water:
            self.water = abs(self.water)
        if self.other_charges:
            self.other_charges = abs(self.other_charges)

    def _compute_total(self):
        for record in self:
            record.total = record.salary + record.electricity + record.water + record.other_charges

    @api.model
    def default_get(self, flist=[]):
        res = super(IndirectCost, self).default_get(flist)
        total_sal = 0
        try:
            payslips = self.env['hr.payslip'].search([])
            month_payslips = payslips.filtered(
                lambda rec: rec.date_from >= res['date_from'] and rec.date_to <= res['date_to']
            )

            for slip in month_payslips:
                total_sal += slip.get_salary_line_total('NET')
            res.update({'salary': total_sal})
        except:
            res.update({'salary': 0})
        return res

    @api.model
    def create(self, vals):
        if vals.get('ref', _('New')) == _('New'):
            vals['ref'] = self.env['ir.sequence'].next_by_code('fishing.cost.indirect') or _('New')

        if vals.get('date_from') and vals.get('date_to'):
            date_from, date_to = vals.get('date_from'), vals.get('date_to')
            ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
            locale = self.env.context.get('lang') or 'en_US'

            name = _('Fix charges for %s') % (
                tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))
            vals['name'] = name
        return super(IndirectCost, self).create(vals)


class CostReport(models.Model):
    _name = "fishing.cost.report"
    _rec_name = "ref"

    ref = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'))
    name = fields.Char(string='Name', readonly=True)
    date_from = fields.Date("Date from", default=lambda self: fields.Date.to_string(date.today().replace(day=1)))
    date_to = fields.Date("Date to", default=lambda self: fields.Date.to_string(
        (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date()))
    total_purchase = fields.Float("Purchase", compute="_compute_account_moves")
    total_sale = fields.Float("Sale", compute="_compute_account_moves")
    total_direct_costs = fields.Float("Direct costs", compute="_compute_costs")
    total_indirect_costs = fields.Float("Indirect costs", compute="_compute_costs")
    total_quantity = fields.Float("Total quantity", compute="_compute_total_quantity")

    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )
    report_lines = fields.One2many(
        comodel_name='fishing.cost.report.line',
        inverse_name='report_id',
        string='Details',
        readonly=True,
        required=True)

    def _compute_total(self):
        for record in self:
            record.total = record.salary + record.electricity + record.water + record.other_charges

    def _compute_total_quantity(self):
        for record in self:
            record.total_quantity = sum(record.report_lines.mapped("quantity"))

    def _compute_costs(self):

        for record in self:
            total_directs = 0
            total_indirects = 0

            record.total_direct_costs = 0
            record.total_indirect_costs = 0

            directs = self.env["fishing.cost.direct"].search([
                ('date_from', '>=', record.date_from),
                ('date_to', '<=', record.date_to),
            ])
            indirects = self.env["fishing.cost.indirect"].search([
                ('date_from', '>=', record.date_from),
                ('date_to', '<=', record.date_to),
            ])

            for cost in directs:
                total_directs += cost.total
            for cost in indirects:
                total_indirects += cost.total

            record.total_direct_costs = total_directs
            record.total_indirect_costs = total_indirects

    def _compute_account_moves(self):

        for record in self:
            total_purchase = 0
            total_sale = 0

            record.total_purchase = 0
            record.total_sale = 0

            purchases = self.env["account.move"].search([
                ('invoice_date', '>=', record.date_from),
                ('invoice_date', '<=', record.date_to),
                ('move_type', '=', 'in_invoice'),

            ])
            sales = self.env["account.move"].search([
                ('invoice_date', '>=', record.date_from),
                ('invoice_date', '<=', record.date_to),
                ('move_type', '=', 'out_invoice'),
            ])

            for line in purchases:
                total_purchase += line.amount_residual
            for line in sales:
                total_sale += line.amount_residual

            record.total_purchase = total_purchase
            record.total_sale = total_sale

    @api.model
    def create(self, vals):
        if vals.get('ref', _('New')) == _('New'):
            vals['ref'] = self.env['ir.sequence'].next_by_code('fishing.cost.report') or _('New')

        if vals.get('date_from') and vals.get('date_to'):
            date_from, date_to = vals.get('date_from'), vals.get('date_to')
            ttyme = datetime.combine(fields.Date.from_string(date_from), time.min)
            locale = self.env.context.get('lang') or 'en_US'

            name = _('Costs report for %s') % (
                tools.ustr(babel.dates.format_date(date=ttyme, format='MMMM-y', locale=locale)))
            vals['name'] = name
        report = super(CostReport, self).create(vals)
        period_receptions = self.env["fishing.reception"].search(
            [('create_date', '>=', report.date_from), ('create_date', '<=', report.date_to)])
        # raise ValidationError(len(period_receptions))
        for reception in period_receptions:
            for reception_line in reception.reception_ids:
                reception_line_already_added = False
                for report_line in report.report_lines:
                    if reception_line.article1.id == report_line.reception_line_id.article1.id:
                        reception_line_already_added = True
                        report_line.update({'quantity': report_line.quantity + reception_line.qte1})
                        break
                if not reception_line_already_added:
                    self.env["fishing.cost.report.line"].create({
                        'report_id': report.id,
                        'reception_line_id': reception_line.id,
                        'quantity': reception_line.qte1 + reception_line.scum_qty1
                    })
        return report


class CostReportLine(models.Model):
    _name = "fishing.cost.report.line"

    report_id = fields.Many2one(comodel_name='fishing.cost.report', string='Report')
    reception_line_id = fields.Many2one(comodel_name='reception.fish.detail', string='Reception line')
    product = fields.Char(string='Product', related='reception_line_id.article1.display_name')
    quantity = fields.Float("Quantity")
    sale_price = fields.Float("Sale Price", help="History sale price", compute="_compute_moves")
    purchase_price = fields.Float("Purchase Price", help="History purchase price", compute="_compute_moves")
    month_sale_price = fields.Float("Month Price", help="Month sale price", compute="_compute_month_sale_price")
    direct_charge = fields.Float("Charge direct", compute="_compute_charges")
    indirect_charge = fields.Float("Charge indirect", compute="_compute_charges")
    cost = fields.Float("Cost", compute="_compute_cost")
    marge = fields.Float("Marge", compute="_compute_marge")
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )

    def _compute_charges(self):
        for record in self:
            record.direct_charge = (
                                       record.report_id.total_direct_costs / record.report_id.total_quantity if record.report_id.total_quantity else 1) * record.quantity
            record.indirect_charge = (
                                         record.report_id.total_indirect_costs / record.report_id.total_quantity if record.report_id.total_quantity else 1) * record.quantity

    def _compute_moves(self):
        for record in self:
            record.sale_price = 0
            # period_moves = self.env["account.move"].search([('invoice_date', '>=', record.report_id.date_from),
            # ('invoice_date', '<=', record.report_id.date_to)])
            period_moves = self.env["account.move"].search([])
            product_sold_qnty = 0
            product_sale_prices = 0
            product_purchased_qnty = 0
            product_purchase_prices = 0
            # raise ValidationError(len(period_moves))
            for move in period_moves:
                for line in move.invoice_line_ids:
                    if line.product_id.product_tmpl_id.id == record.reception_line_id.article1.id:
                        if move.move_type == 'in_invoice':
                            product_purchased_qnty += line.quantity
                            product_purchase_prices += line.price_subtotal
                        if move.move_type == 'out_invoice':
                            product_sold_qnty += line.quantity
                            product_sale_prices += line.price_subtotal

            record.sale_price = product_sale_prices / product_sold_qnty if product_sold_qnty > 0 else 0.0
            record.purchase_price = product_purchase_prices / product_purchased_qnty if product_purchased_qnty > 0 else 0.0

    def _compute_month_sale_price(self):
        for record in self:
            record.month_sale_price = 0
            month_start = fields.Date.to_string(date.today().replace(day=1))
            month_end = fields.Date.to_string(
                (datetime.now() + relativedelta(months=+1, day=1, days=-1)).date())
            period_moves = self.env["account.move"].search(
                [('invoice_date', '>=', month_start),
                 ('invoice_date', '<=', month_end)])
            product_sold_qnty = 0
            product_sale_prices = 0
            for move in period_moves:
                for line in move.invoice_line_ids:
                    if line.product_id.product_tmpl_id.id == record.reception_line_id.article1.id:
                        if move.move_type == 'out_invoice':
                            product_sold_qnty += 1
                            product_sale_prices += line.price_unit
            record.month_sale_price = product_sale_prices / product_sold_qnty if product_sold_qnty > 0 else 0.0

    def _compute_cost(self):
        for record in self:
            record.cost = (record.purchase_price + (
                (record.direct_charge + record.indirect_charge)) / record.quantity) if record.quantity > 0 else (
                    record.purchase_price + (record.direct_charge + record.indirect_charge))

    def _compute_marge(self):
        for record in self:
            record.marge = record.month_sale_price - record.cost
