# -*- coding: utf-8 -*-

{
    'name': 'Hospital',
    'version': '4',
    'summary': 'Hospital Management',
    'sequence': -799,
    'description': """"Hospital management software""",
    'category': 'Productivity',
    'website': 'https://www.odoomates.tech',
    'images': [],
    'depends': [
        'sale',
        'mail',
        'account'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/data.xml',
        'views/patiens.xml',
        'views/sale.xml',
        'views/inherited_account.xml'

    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
