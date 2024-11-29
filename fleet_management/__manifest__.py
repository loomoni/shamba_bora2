# -*- coding: utf-8 -*-
{
    'name': "Fleet Management",

    'summary': """
        Fleet Management""",

    'description': """
        Fleet Management
    """,

    'author': "Xero1 LTD",
    'website': "http://www.xero1.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'assets',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','hr'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/vehicle_gatepass.xml',
        'views/vehicle_assignment.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}