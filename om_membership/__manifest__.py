{
    'name': 'Membership',
    'version': '12.0.1.0.0',
    'category': 'Extra Tool',
    'summary': 'Associate Membership Registration',
    'author': 'Loomoni Morwo',
    'company': 'TANZANIA PRIVATE SECTOR FOUNDATION',
    'website': "http://www.tpsftz.org/",
    'depends': ['account', 'base', 'sale', 'board', 'base_setup', 'product', 'analytic', 'portal', 'digest', 'contacts'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/views.xml',
        'views/contact_inherit.xml',
        'views/email_inherity.xml',
        'views/invoice_inherity_view.xml',
        'views/website_form.xml',
    ],
    'qweb': [
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}
