# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductLine(models.Model):
    _name = 'pms.project.product.line'
    _description = '产品线'

    name = fields.Char(string='名称', required=True)
    code = fields.Char(string='代码', required=True, index=True)
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company, required=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', "产品线代码已存在!"),
    ]


class SourceOfDemand(models.Model):
    _name = 'pms.source.of.demand'
    _description = '需求来源'

    name = fields.Char(string='来源名称', required=True, index=True)
    code = fields.Char(string='助记码', required=True, index=True)
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company, required=True)

    _sql_constraints = [
        ('code_uniq', 'unique (code)', "助记码已存在!"),
    ]


class ProductDemandStage(models.Model):
    _name = 'pms.product.demand.stage'
    _description = '需求阶段'

    def _get_default_product_ids(self):
        product_ids = self.env.context.get('active_id')
        return [product_ids] if product_ids else None

    sequence = fields.Integer(string=u'序号')
    name = fields.Char(string='阶段名称', required=True, index=True)
    mail_template_id = fields.Many2one('mail.template', string='Email模板')
    product_ids = fields.Many2many('pms.project.product', string=u'用于产品', default=_get_default_product_ids)
    description = fields.Text(string=u'说明')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company, required=True)


class ProductDemandTag(models.Model):
    _name = 'pms.product.demand.tags'
    _description = '需求标签'

    name = fields.Char(string='标签名', required=True, index=True)
    color = fields.Integer(string='颜色')


class ProductModule(models.Model):
    _name = 'pms.project.product.module'
    _description = '产品模块'

    sequence = fields.Integer(string=u'序号')
    name = fields.Char(string='模块名称', required=True)
    code = fields.Char(string='代码', required=True, index=True)
    product_id = fields.Many2one(comodel_name='pms.project.product', string=u'项目产品', ondelete='set null')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company, required=True)

    def name_get(self):
        return [(record.id, "%s/%s" % (record.product_id.name, record.name)) for record in self]


class ProjectProduct(models.Model):
    _description = '项目产品'
    _name = 'pms.project.product'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    PRODUCTTYPE = [
        ('normal', '正常'),
        ('branch', '多分支(客户定制场景)'),
        ('platform', '多平台(跨平台应用开发)')
    ]

    name = fields.Char(string='产品名称', track_visibility='onchange', required=True, index=True)
    code = fields.Char(string='产品代号', track_visibility='onchange', required=True, index=True)
    color = fields.Integer(string='颜色')
    product_line_id = fields.Many2one(comodel_name='pms.project.product.line', string=u'产品线', track_visibility='onchange')
    product_principal = fields.Many2one(comodel_name='res.users', string=u'产品负责人', track_visibility='onchange')
    test_principal = fields.Many2one(comodel_name='res.users', string=u'测试负责人', track_visibility='onchange')
    release_principal = fields.Many2one(comodel_name='res.users', string=u'发布负责人', track_visibility='onchange')
    product_type = fields.Selection(string=u'产品类型', selection=PRODUCTTYPE, default='normal', track_visibility='onchange', index=True)
    description = fields.Text(string=u'产品描述')
    module_ids = fields.One2many(comodel_name='pms.project.product.module', inverse_name='product_id', string=u'产品模块')
    module_count = fields.Integer(compute='_compute_module_count', string="产品模块数量")
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company, required=True)
    user_ids = fields.Many2many(comodel_name='res.users', string=u'团队成员')
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='文档')

    def _compute_module_count(self):
        for rec in self:
            rec.module_count = len(rec.module_ids)

    @api.onchange('product_principal', 'test_principal', 'release_principal')
    def _onchange_users(self):
        if self.product_principal:
            user_list = self.user_ids.ids
            user_list.append(self.product_principal.id)
            self.user_ids = [(6, 0, user_list)]
        if self.test_principal:
            user_list = self.user_ids.ids
            user_list.append(self.test_principal.id)
            self.user_ids = [(6, 0, user_list)]
        if self.release_principal:
            user_list = self.user_ids.ids
            user_list.append(self.release_principal.id)
            self.user_ids = [(6, 0, user_list)]

    def open_demand(self):
        """
        跳转至需求
        :return:
        """
        ctx = dict(self._context)
        ctx.update({'search_default_product_id': self.id})
        action = self.env['ir.actions.act_window'].for_xml_id('odoo_project', 'pms_product_demand_action')
        action['domain'] = [('product_id', '=', self.id)]
        return dict(action, context=ctx)

    def attachment_image_preview(self):
        self.ensure_one()
        domain = [('res_model', '=', self._name), ('res_id', '=', self.id)]
        return {
            'domain': domain,
            'res_model': 'ir.attachment',
            'name': u'附件管理',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'limit': 20,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)


class ProjectProductDemand(models.Model):
    _description = '产品需求'
    _name = 'pms.product.demand'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    PRIORITY = [
        ('3', '紧急'),
        ('2', '较高'),
        ('1', '一般'),
        ('0', '较低'),
    ]
    DEMANDSTATE = [
        ('draft', '草稿'),
        ('active', '激活'),
        ('closed', '关闭'),
        ('changed', '变更'),
    ]
    CloseDescription = [
        ('done', '已完成'),
        ('subdivided', '已细分'),
        ('duplicate', '重复项'),
        ('postponed', '延期'),
        ('willnotdo', '不做'),
        ('cancel', '已取消'),
        ('bydesign', '设计如此'),
    ]

    def _get_default_stage_id(self):
        """ Gives default stage_id """
        product_id = self.env.context.get('default_product_id')
        if not product_id:
            return False
        search_domain = [('product_ids', '=', product_id)]
        return self.env['pms.product.demand.stage'].sudo().search(search_domain, order='sequence', limit=1).id

    active = fields.Boolean(string=u'Active', default=True)
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company, required=True)
    product_id = fields.Many2one(comodel_name='pms.project.product', string=u'所属产品', ondelete='set null', track_visibility='onchange')
    module_id = fields.Many2one(comodel_name='pms.project.product.module', string=u'所属模块', ondelete='set null', domain="[('product_id', '=', product_id)]", track_visibility='onchange')
    from_id = fields.Many2one(comodel_name='pms.source.of.demand', string=u'需求来源', track_visibility='onchange')
    name = fields.Char(string='需求名称', required=True, track_visibility='onchange')
    code = fields.Char(string='需求编号', track_visibility='onchange')
    from_description = fields.Char(string='来源备注', track_visibility='onchange')
    is_review = fields.Boolean(string=u'需要评审', default=False)
    review_user_id = fields.Many2one(comodel_name='res.users', string=u'评审人', track_visibility='onchange')
    review_date = fields.Datetime(string=u'评审时间', track_visibility='onchange')
    review_result = fields.Selection(string=u'评审结果', selection=[('load', '未评审'), ('pass', '确认通过'), ('reject', '拒绝')],
                                     default='load', track_visibility='onchange')
    priority = fields.Selection(string=u'优先级', selection=PRIORITY, default='1', track_visibility='onchange')
    expected_hour = fields.Integer(string=u'预计小时', track_visibility='onchange')
    demand_description = fields.Text(string=u'需求描述', default="建议参考的模板：作为一名<某种类型的用户>，我希望<达成某些目的>，这样可以<开发的价值>")
    acceptance_criteria = fields.Text(string=u'验收标准')
    cc_user_ids = fields.Many2many('res.users', 'pms_product_demand_res_users_cc_rel', string=u'抄送用户', track_visibility='onchange')
    color = fields.Integer(string='颜色')
    stage_id = fields.Many2one('pms.product.demand.stage', string='阶段', ondelete='set null', tracking=True, index=True,
                               default=_get_default_stage_id, domain="[('product_ids', '=', product_id)]", copy=False, track_visibility='onchange')
    tag_ids = fields.Many2many(comodel_name='pms.product.demand.tags', string=u'标签', track_visibility='onchange')
    assign_user = fields.Many2one(comodel_name='res.users', string=u'指派给', track_visibility='onchange')
    close_user = fields.Many2one(comodel_name='res.users', string=u'关闭人', track_visibility='onchange')
    close_date = fields.Datetime(string=u'关闭时间', track_visibility='onchange')
    close_description = fields.Selection(string=u'关闭原因', selection=CloseDescription, track_visibility='onchange')
    state = fields.Selection(string=u'状态', selection=DEMANDSTATE, default='draft', track_visibility='onchange')
    parent_id = fields.Many2one('pms.product.demand', string='上级需求', index=True, track_visibility='onchange')
    child_ids = fields.One2many('pms.product.demand', 'parent_id', string="子需求", context={'active_test': False})
    subdemand_count = fields.Integer("子需求数量", compute='_compute_subdemand_count')
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='文档')

    # ---计划---
    planned_date_begin = fields.Datetime("开始时间")
    planned_date_end = fields.Datetime("结束时间")

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('pms.product.demand.sequence')
        if not values['stage_id']:
            if values['product_id']:
                search_domain = [('product_ids', '=', values['product_id'])]
                values['stage_id'] = self.env['pms.product.demand.stage'].sudo().search(search_domain, order='sequence', limit=1).id
        return super(ProjectProductDemand, self).create(values)

    @api.depends('child_ids')
    def _compute_subdemand_count(self):
        task_data = self.env['pms.product.demand'].read_group([('parent_id', 'in', self.ids)], ['parent_id'], ['parent_id'])
        mapping = dict((data['parent_id'][0], data['parent_id_count']) for data in task_data)
        for demand in self:
            demand.subdemand_count = mapping.get(demand.id, 0)

    def action_open_parent_demaned(self):
        return {
            'name': _('上级需求'),
            'view_mode': 'form',
            'res_model': 'pms.product.demand',
            'res_id': self.parent_id.id,
            'type': 'ir.actions.act_window',
            'context': dict(self._context, create=False)
        }

    def action_subdemand(self):
        action = self.env.ref('odoo_project.pms_product_demand_sub_task').read()[0]
        action['domain'] = [('id', 'child_of', self.id), ('id', '!=', self.id)]
        ctx = dict(self.env.context)
        ctx.update({
            'default_name': self.env.context.get('name', self.name) + ':',
            'default_parent_id': self.id,
            'search_default_parent_id': self.id,
            'default_company_id': self.company_id.id,
            'default_product_id': self.product_id.id,
            'default_module_id': self.module_id.id,
        })
        action['context'] = ctx
        return action

    def attachment_image_preview(self):
        self.ensure_one()
        domain = [('res_model', '=', self._name), ('res_id', '=', self.id)]
        return {
            'domain': domain,
            'res_model': 'ir.attachment',
            'name': u'附件管理',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'kanban,tree,form',
            'view_type': 'form',
            'limit': 20,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("非草稿状态需求不允许删除，应使用单据上归档功能！"))
        super(ProjectProductDemand, self).unlink()
