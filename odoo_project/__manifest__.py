# -*- coding: utf-8 -*-
{
    'name': "Odoo研发项目管理",
    'summary': """Odoo研发项目管理""",
    'description': """Odoo研发项目管理""",
    'author': "SuXueFeng",
    'website': "https://www.sxfblog.com",
    'category': 'project',
    'version': '13.0',
    'depends': ['base', 'mail'],
    'installable': True,
    'application': True,
    'auto_install': False,
    'data': [
        'security/project_security.xml',
        'security/ir.model.access.csv',
        'data/default_data.xml',
        'data/ir_sequence.xml',

        'wizard/pms_project_product.xml',

        'views/assets.xml',
        'views/pms_project_product.xml',
    ],
}
