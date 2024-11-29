# -*- coding: utf-8 -*-
{
    'name': "Wage Requests",

    'summary': """
        Custom Module For Wages""",

    'description': """
        Custom Module For Wages
    """,

    'author': "Xero LTD",
    'website': "http://www.xero.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'account',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'account', 'hr'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'data/report.xml',
        'data/report_template.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
