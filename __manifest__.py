# -*- coding: utf-8 -*-
{
    'name': "CCI International",

    'summary': """
        Management of international departement of a belgian CCI.
        """,

    'description': """
        Management of international dept of CCI.
        Management of certificates, visas, ata carnets, 
        embassy folders and translations projects
    """,

    'author': "Philippe Vandermeer",
    'website': "http://www.ccilvn.be",
    'application': True,
    'sequence': 99,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Specific Industry Applications',
    'version': '12.0.1.0',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base','sale','account_intrastat'], # account intrastat for intrastats codes used in certificates

    # always loaded
    'data': [
        'security/cci_international_security.xml',
        'security/ir.model.access.csv',
        'wizards/create_visa_from_certificate_views.xml',
        'wizards/import_digital_certificates_views.xml',
        'wizards/import_digital_visas_views.xml',
        'wizards/import_digital_atas_views.xml',
        'views/cci_international_menus.xml',
        'views/delegated_type_views.xml',
        'views/credit_line_views.xml',
        'views/sale_order_views.xml',
        'views/res_partner_views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
