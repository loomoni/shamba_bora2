# -*- coding: utf-8 -*-
{
    'name': "Custom Budget Management",

    'summary': """
        Budget Management""",

    'description': """
        Budget groups,department budgets,annual budget,budget reallocation and supplimentary
    """,

    'author': "Xero1 LTD",
    'website': "http://www.xero1.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'accounts',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'account', 'analytic', 'om_account_accountant', 'om_account_budget', 'hr', 'mail', 'custom_company'],

    # always loaded
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/templates.xml',
        'views/annual_budget.xml',
        'views/budget_groups.xml',
        'views/budget_versions.xml',
        'views/views.xml',
        'views/budget_reallocation.xml',
        'views/budget_supplimentary.xml',
        'views/consolidated_monthly_budget.xml',
        'views/monthly_budget_request.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}