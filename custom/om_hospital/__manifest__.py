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
        'wizard/create_appointment_views.xml',
        'views/patiens.xml',
        'views/kids.xml',
        'views/patient_gender_view.xml',
        'views/appointment_view.xml',
        'views/sale.xml',
        'views/inherited_account.xml'

    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
