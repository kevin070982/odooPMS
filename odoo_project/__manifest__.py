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
        'security/ir_rule.xml',
        'data/default_data.xml',
        'data/ir_sequence.xml',

        'wizard/pms_product.xml',
        'wizard/pms_project_task.xml',

        'views/assets.xml',
        'views/pms_product.xml',
        'views/pms_project.xml',
    ],
}
