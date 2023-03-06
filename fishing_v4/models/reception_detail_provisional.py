from odoo import fields, models, api, _


class FishDetail(models.Model):
    _name = 'reception.fish.detail'

    status_choices1 = [
        ('0', 'Waiting for treatment'),
        ('1', 'Treatment in progress'),
        ('2', 'Treated'),
        ('3', 'Tunnels in progress'),
        ('4', 'Tunneled'),
        ('5', 'Packaging in progress'),
        ('6', 'Packed')
    ]
    type_choices = [('production', 'Production'), ('service', 'Service')]

    quality_choices1 = [('q1', 'Good quality'), ('q2', 'Bad quality')]
    article1 = fields.Many2one(comodel_name='product.template', string='Product', required=False)
    quality1 = fields.Many2one(comodel_name='fishing.quality', string='Quality',required = True)
    qte1 = fields.Float(string='Quantity', required=False)
    scum_qty1 = fields.Float(string='Scum Quantity', required=False)
    status1 = fields.Selection(status_choices1, required=False, default='0')
    reception_id1 = fields.Many2one(comodel_name='fishing.reception', string='Reception', required=False)



    type1 = fields.Selection(type_choices, string='Type', required=True, default='production', compute="_compute_type1",
                             tracking=True)

    treatment_ordered1 = fields.Boolean(string='Treatment', required=False, default=False)
    tunnel_ordered1 = fields.Boolean(string='Tunnel', required=False, default=False)
    ordered_temp1 = fields.Float(string='Temperature', required=False, default=0.0)
    packaging_ordered1 = fields.Boolean(string='Packaging', required=False, default=False)
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company
    )

    #Dynamic Domain for selecting quality on base of product
    @api.onchange('article1')
    def onchange_article(self):
        #fetch All Quality First
        quality_ids = self.env['fishing.quality'].search([])
        #Reset Already Select Quality Because product has been changed
        self.quality1=False
        quality_list=[]
        #loop For identfy Quality hold product or not in Many2Many field
        for quanlty in quality_ids:
            for product in quanlty.product_ids:
                if self.article1.id == product.id:
                    if product.id not in quality_list:
                        quality_list.append(quanlty.id)
                        break
                    else:
                        break
        #Apply Domain Through List of iDs Qualities IDS
        return {'domain': {'quality1':[('id', 'in', quality_list)]}}

    @api.model
    def create(self, values):
        result = super(FishDetail, self).create(values)
        fish_detail = self.env['fishing.reception.detail'].search([])
        all_detail = fish_detail.search([('article', '=', values.get('article1')),
                                         ('status', 'in', ['0']),
                                         ('type', '=', 'production'),
                                         ('quality', '=', values.get('quality1'))])
        if values.get('type1') == 'production':
            if all_detail:
                total_qty = values.get('qte1')
                for reception in all_detail:
                    total_qty += reception.qte
                all_detail.write({'qte': total_qty, 'quality': values.get('quality1')})

            else:
                fish_create = fish_detail.create({
                    'article': values.get('article1'),
                    'reception_id': values.get('reception_id1'),
                    'quality': values.get('quality1'),
                    'qte': values.get('qte1'),
                    'type': values.get('type1'),
                    'scum_qty': values.get('scum_qty1'),
                    'status': '0'
                })
        else:
            fish_create = fish_detail.create({
                'article': values.get('article1'),
                'reception_id': values.get('reception_id1'),
                'quality': values.get('quality1'),
                'qte': values.get('qte1'),
                'type': values.get('type1'),
                'scum_qty': values.get('scum_qty1'),
                'status': '0',
                'treatment_ordered': values.get('treatment_ordered1'),
                'will_be_tunneled': values.get('tunnel_ordered1'),
                'packaging_ordered': values.get('packaging_ordered1'),
                'ordered_temp': values.get('ordered_temp1')
            })
        return result

    def _compute_type1(self):
        for line in self:
            line.type1 = line.reception_id1.type
