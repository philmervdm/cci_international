# -*- coding: utf-8 -*-
{
    'name': "CCI International",

    'summary': """
        Management of international dept of CCI
        """,

    'description': """
        Management of international dept of CCI.
        Management of certificates, visas, ata carnets, 
	embassy folders and translations projects
    """,

    'author': "Philippe Vandermeer",
    'website': "http://www.ccilvn.be",
    'application': True,

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/12.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Specific Industry Applications',
    'version': '12.0.1.0',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
