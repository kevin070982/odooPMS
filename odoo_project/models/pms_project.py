# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PmsProjectStage(models.Model):
    _name = 'pms.project.stage'
    _description = '任务阶段'

    def _get_default_project_ids(self):
        project_ids = self.env.context.get('active_id')
        return [project_ids] if project_ids else None

    sequence = fields.Integer(string=u'序号')
    color = fields.Integer(string='颜色')
    name = fields.Char(string='阶段名称', required=True, index=True)
    mail_template_id = fields.Many2one('mail.template', string='Email模板')
    project_ids = fields.Many2many('pms.project.project', string=u'用于项目', default=_get_default_project_ids)
    description = fields.Text(string=u'说明')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company)


class ProjectTeam(models.Model):
    _name = 'pms.project.team'
    _description = "项目团队"

    name = fields.Char(string='团队名称', required=True, index=True)
    color = fields.Integer(string='颜色')
    sequence = fields.Integer(string=u'序号')
    user_ids = fields.Many2many(comodel_name='res.users', string=u'团队成员', required=True, index=True)
    description = fields.Text(string=u'说明')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company)


class ProjectTaskTag(models.Model):
    _name = 'pms.product.task.tags'
    _description = '需求标签'

    name = fields.Char(string='标签名', required=True, index=True)
    color = fields.Integer(string='颜色')


class ProjectModule(models.Model):
    _name = 'pms.project.project.module'
    _description = '项目模块'

    sequence = fields.Integer(string=u'序号')
    name = fields.Char(string='模块名称', required=True)
    code = fields.Char(string='代码', required=True, index=True)
    project_id = fields.Many2one(comodel_name='pms.project.project', string=u'项目产品', ondelete='set null')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company, required=True)


class ProjectTaskType(models.Model):
    _name = 'pms.project.task.type'
    _description = '任务类型'

    sequence = fields.Integer(string=u'序号')
    name = fields.Char(string='类型名称', required=True)
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company, required=True)


class PmsProjectProject(models.Model):
    _name = 'pms.project.project'
    _description = u"项目"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    ProjectType = [
        ('short', '短期项目'),
        ('long', '长期项目'),
        ('oam', '运维项目'),
    ]
    ProjectState = [
        ('started', '未开始'),
        ('processing', '进行中'),
        ('suspended', '已挂起'),
        ('closed', '已关闭'),
    ]

    name = fields.Char(string='项目名称', track_visibility='onchange', required=True, index=True)
    code = fields.Char(string='项目代码', track_visibility='onchange', required=True, index=True)
    start_date = fields.Date(string=u'开始日期', default=fields.date.today(), track_visibility='onchange')
    end_date = fields.Date(string=u'结束日期', default=fields.date.today(), track_visibility='onchange')
    color = fields.Integer(string='颜色')
    work_days = fields.Integer(string=u'可用工作日', track_visibility='onchange')
    team_id = fields.Many2one(comodel_name='pms.project.team', string=u'项目团队', track_visibility='onchange')
    module_ids = fields.One2many(comodel_name='pms.project.project.module', inverse_name='project_id', string=u'项目模块')
    product_ids = fields.Many2many(comodel_name='pms.project.product', string=u'所属产品', track_visibility='onchange')
    description = fields.Text(string=u'项目描述')
    project_type = fields.Selection(string=u'项目类型', selection=ProjectType, default='short', track_visibility='onchange')
    state = fields.Selection(string=u'项目状态', selection=ProjectState, default='started', track_visibility='onchange')
    product_principal = fields.Many2one(comodel_name='res.users', string=u'产品负责人', track_visibility='onchange')
    project_principal = fields.Many2one(comodel_name='res.users', string=u'项目负责人', track_visibility='onchange')
    test_principal = fields.Many2one(comodel_name='res.users', string=u'测试负责人', track_visibility='onchange')
    release_principal = fields.Many2one(comodel_name='res.users', string=u'发布负责人', track_visibility='onchange')
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company, track_visibility='onchange')
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='文档')

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

    @api.onchange('product_ids')
    def _onchange_product_ids(self):
        self.module_ids = False
        model_list = list()
        for product_id in self.product_ids:
            for model in product_id.module_ids:
                model_list.append((0, 0, {
                    'sequence': model.sequence,
                    'name': model.name,
                    'code': model.code,
                    'company_id': model.company_id.id,
                }))
        self.module_ids = model_list

    def open_task(self):
        ctx = dict(self._context)
        ctx.update({'search_default_project_id': self.id, 'default_project_id': self.id})
        action = self.env['ir.actions.act_window'].for_xml_id('odoo_project', 'pms_project_task_action')
        action['domain'] = [('project_id', '=', self.id)]
        return dict(action, context=ctx)


class ProjectTask(models.Model):
    _description = "项目任务"
    _name = 'pms.project.task'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    PRIORITY = [
        ('3', '紧急'),
        ('2', '较高'),
        ('1', '一般'),
        ('0', '较低'),
    ]

    TaskSTATE = [
        ('draft', '未开始'),
        ('active', '进行中'),
        ('paused', '已暂停'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('closed', '关闭'),
    ]

    def _get_default_stage_id(self):
        project_id = self.env.context.get('default_project_id')
        if not project_id:
            return False
        search_domain = [('project_ids', '=', project_id)]
        return self.env['pms.project.stage'].sudo().search(search_domain, order='sequence', limit=1).id

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        search_domain = [('id', 'in', stages.ids)]
        if 'default_project_id' in self.env.context:
            search_domain = ['|', ('project_ids', '=', self.env.context['default_project_id'])] + search_domain
        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    active = fields.Boolean(string=u'Active', default=True)
    company_id = fields.Many2one('res.company', '公司', default=lambda self: self.env.company, required=True)
    name = fields.Char(string='名称', track_visibility='onchange', required=True, index=True)
    code = fields.Char(string='编号', track_visibility='onchange')
    color = fields.Integer(string='颜色')
    project_id = fields.Many2one('pms.project.project', string=u'关联项目', track_visibility='onchange', index=True)
    product_ids = fields.Many2many('pms.project.product', string=u'关联项目产品', compute="_compute_product_ids", store=True)
    type_id = fields.Many2one('pms.project.task.type', string=u'任务类型', track_visibility='onchange', index=True)
    module_id = fields.Many2one('pms.project.project.module', string=u'所属模块', track_visibility='onchange', index=True)
    assign_user = fields.Many2many(comodel_name='res.users', string=u'指派给', track_visibility='onchange')
    stage_id = fields.Many2one('pms.project.stage', string='任务阶段', ondelete='set null', tracking=True, index=True,
                               default=_get_default_stage_id, domain="[('project_ids', '=', project_id)]", copy=False,
                               group_expand='_read_group_stage_ids', track_visibility='onchange')
    demand_id = fields.Many2one(comodel_name='pms.product.demand', string=u'关联需求', track_visibility='onchange',
                                domain="[('product_id', 'in', product_ids)]")
    priority = fields.Selection(string=u'优先级', selection=PRIORITY, default='1', track_visibility='onchange')
    expected_hour = fields.Integer(string=u'预计工时', track_visibility='onchange')
    task_description = fields.Text(string='任务描述')
    start_date = fields.Date(string=u'预计开始', track_visibility='onchange', default=fields.date.today())
    end_date = fields.Date(string=u'截止日期', track_visibility='onchange')
    actual_start_date = fields.Date(string=u'实际开始', track_visibility='onchange')
    description = fields.Text(string='备注')
    attachment_number = fields.Integer(compute='_compute_attachment_number', string='文档')
    state = fields.Selection(string=u'任务状态', selection=TaskSTATE, default='draft', track_visibility='onchange')
    completion_user = fields.Many2one(comodel_name='res.users', string=u'完成人', track_visibility='onchange')
    actual_completion_date = fields.Date(string=u'实际完成日期', track_visibility='onchange')
    parent_id = fields.Many2one('pms.project.task', string='上级需求', index=True, track_visibility='onchange')
    child_ids = fields.One2many('pms.project.task', 'parent_id', string="子需求", context={'active_test': False})
    subtask_count = fields.Integer("子需求数量", compute='_compute_subtask_count')
    line_ids = fields.One2many(comodel_name='pms.project.task.line', inverse_name='task_id', string=u'工时列表')

    @api.model
    def create(self, values):
        values['code'] = self.env['ir.sequence'].sudo().next_by_code('pms.project.task.sequence')
        return super(ProjectTask, self).create(values)

    @api.depends('project_id')
    def _compute_product_ids(self):
        for rec in self:
            if rec.project_id:
                rec.product_ids = rec.project_id.product_ids

    @api.depends('child_ids')
    def _compute_subtask_count(self):
        task_data = self.env['pms.project.task'].read_group([('parent_id', 'in', self.ids)], ['parent_id'], ['parent_id'])
        mapping = dict((data['parent_id'][0], data['parent_id_count']) for data in task_data)
        for task in self:
            task.subtask_count = mapping.get(task.id, 0)

    def action_subtask(self):
        action = self.env.ref('odoo_project.pms_project_task_action').read()[0]
        action['domain'] = [('id', 'child_of', self.id), ('id', '!=', self.id)]
        ctx = dict(self.env.context)
        ctx.update({
            'default_name': self.env.context.get('name', self.name) + '/',
            'default_parent_id': self.id,
            'search_default_parent_id': self.id,
            'default_company_id': self.company_id.id,
            'default_project_id': self.project_id.id,
            'default_module_id': self.module_id.id,
        })
        action['context'] = ctx
        return action

    def action_open_parent_task(self):
        return {
            'name': _('上级需求'),
            'view_mode': 'form',
            'res_model': 'pms.project.task',
            'res_id': self.parent_id.id,
            'type': 'ir.actions.act_window',
            'context': dict(self._context, create=False)
        }

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
            'limit': 50,
            'context': "{'default_res_model': '%s','default_res_id': %d}" % (self._name, self.id)
        }

    def _compute_attachment_number(self):
        attachment_data = self.env['ir.attachment'].read_group(
            [('res_model', '=', self._name), ('res_id', 'in', self.ids)], ['res_id'], ['res_id'])
        attachment = dict((data['res_id'], data['res_id_count']) for data in attachment_data)
        for expense in self:
            expense.attachment_number = attachment.get(expense.id, 0)


class ProjectTaskLine(models.Model):
    _description = "任务工时"
    _name = 'pms.project.task.line'
    _rec_name = 'task_id'

    sequence = fields.Integer(string=u'sequence')
    task_id = fields.Many2one(comodel_name='pms.project.task', string=u'任务', ondelete='set null')
    user_id = fields.Many2one(comodel_name='res.users', string=u'用户', ondelete='set null')
    user_date = fields.Date(string=u'操作日期')
    sum_hour = fields.Integer(string=u'总计消耗')
    sy_hour = fields.Integer(string=u'预计剩余')
    description = fields.Char(string='备注')



    

