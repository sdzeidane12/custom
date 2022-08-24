{
    'name': 'Fishing V2',
    'version': '2.1',
    'category': 'Manufacturing/Manufacturing',
    'description': "Fish manufacturing process",
    'depends': ['stock', 'maintenance', 'purchase', 'sale', 'mail', 'account'],
    'sequence': -754,
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/fishing_data.xml',
        'views/menu.xml',
        'views/dashboard.xml',
        'views/reception.xml',
        'views/traitement.xml',
        'views/tunnel.xml',
        'views/emballage.xml',
        'views/config.xml',
        'views/stock_pallet.xml',
        'views/fish_stock.xml',
        'views/service_stock_dashboard.xml',
        'wizard/get_quantity_view.xml',
        'wizard/report_wizard_views.xml',
        'wizard/pause_operation_view.xml',
        'wizard/stock_exit_view.xml',
        'wizard/manual_packing_view.xml',
        'report/report_registration.xml',
        'report/production_report.xml',
        'report/letter_report.xml',
        'report/report_pallet_barcode.xml',
        'report/reception_report.xml',
        'report/service_exit_report.xml',
        'views/report_menu.xml',
        'views/product_kanban.xml',
        'views/production_charges.xml',
        'views/maintenance_equipment.xml',
        'views/res_company.xml'
    ],
    'assets': {
        'web.assets_backend': [
            'fishing_v2/static/src/scss/style.scss',
            'fishing_v2/static/src/scss/account_asset.scss',
            'fishing_v2/static/lib/bootstrap-toggle-master/css/bootstrap-toggle.min.css',
            'fishing_v2/static/src/js/account_dashboard.js',
            'fishing_v2/static/lib/Chart.bundle.js',
            'fishing_v2/static/lib/Chart.bundle.min.js',
            'fishing_v2/static/lib/Chart.min.js',
            'fishing_v2/static/lib/Chart.js',
            'fishing_v2/static/lib/bootstrap-toggle-master/js/bootstrap-toggle.min.js',
        ],
        'web.assets_qweb': [
            'fishing_v2/static/src/xml/template.xml',
        ],
    },
    'website': 'https://onlogis.com/en/',
    'installable': True,
    'auto_install': False,
    'application': True,
}
