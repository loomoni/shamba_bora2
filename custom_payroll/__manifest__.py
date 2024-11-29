# -*- coding: utf-8 -*-
{
    'name': "Custom Payroll",

    'summary': """
        Custom Payroll""",

    'description': """
        Custom Payroll
    """,

    'author': "OTB Africa",
    'website': "http://www.otbafrica.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'payroll',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mail','hr','hr_contract','hr_payroll','hr_payroll_account', 'custom_company'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/staff_recoveries.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/payroll_summary.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}