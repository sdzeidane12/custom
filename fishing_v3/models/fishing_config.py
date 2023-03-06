from odoo import fields, models, api, _


class Quality(models.Model):
    _name = 'fishing.quality'
    _rec_name = 'code'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description', help="description of the organoleptic criteria")
    product_ids =  fields.Many2many(comodel_name='product.template', string='Products')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )


class OperationTime(models.Model):
    _name = 'fishing.time'
    _rec_name = 'operation'
    operation_choices = [('treatment', 'Treatment'), ('tunnel', 'Freezing'), ('packaging', 'Packaging')]
    operation = fields.Selection(operation_choices, string='Operation', required=True)
    quantity = fields.Float(string='Quantity (Kg)', required=True, default=100.0)
    time = fields.Float(string='Required time (min)', required=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )


class Tunnel(models.Model):
    _name = 'fishing.tunnel'
    _rec_name = 'code'

    type_choices = [('intern', 'Intern'), ('extern', 'Extern')]

    type = fields.Selection(type_choices, string="Type")

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)
    capacity = fields.Float(string='Capacity', required=True)
    free_capacity = fields.Float(string='Available capacity', compute="_compute_free_capacity")
    min_temp = fields.Float(string='Min temperature', required=True)
    max_temp = fields.Float(string='Max temperature', required=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )

    def _compute_free_capacity(self):
        """Calculate the total available capacity."""
        for tunnel in self:
            taken = 0
            all_active_line = self.env["fishing.reception.detail"].search(
                [
                    ("tunnel_id", "=", tunnel.id),
                    ("status", "=", "3"),
                ]
            )
            for line in all_active_line:
                taken += line.qte
            tunnel.free_capacity = tunnel.capacity - taken


class Letter(models.Model):
    _name = 'fishing.letter'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True)
    dir = fields.Char(string='Direction', required=True)
    title = fields.Char(string='Title', required=True)
    body = fields.Text(string='Body', required=True)
    formula = fields.Text(string='Formula', required=True)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )
