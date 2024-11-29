# -*- coding: utf-8 -*-
{
    'name': "Custom Client Management",

    'summary': """Custom Client Management""",

    'description': """
        Custom Client Management
    """,

    'author': "Xero 1 LTD",
    'website': "http://www.xero.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'company',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','hr','account', 'product'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/property.xml',
        'views/views.xml',
        'views/templates.xml',
        'data/email_template.xml',
        'data/ir_cron_data.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}