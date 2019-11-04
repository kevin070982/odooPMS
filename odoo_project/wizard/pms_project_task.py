# -*- coding: utf-8 -*-
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProjectTaskStart(models.TransientModel):
    _name = 'pms.project.task.start'
    _description = "开始任务"

    task_id = fields.Many2one(comodel_name='pms.project.task', string=u'任务')
    user_date = fields.Date(string=u'开始日期', default=fields.date.today())
    sum_hour = fields.Integer(string=u'总计消耗')
    sy_hour = fields.Integer(string=u'预计剩余')
    description = fields.Char(string='备注')

    def start_task(self):
        """
        开始项目任务
        :return:
        """
        self.ensure_one()
        if self.sy_hour <= 0:
            raise UserError(_("预计剩余不能小于或等于0！"))
        task = self.task_id
        self.env['pms.project.task.line'].create({
            'task_id': task.id,
            'user_id': self.env.user.id,
            'user_date': self.user_date,
            'sum_hour': self.sum_hour,
            'sy_hour': self.sy_hour,
            'description': self.description,
        })
        task.write({
            'state': 'active',
            'actual_start_date': self.user_date,
            'expected_hour': self.sy_hour,
        })
        if self.description:
            task.message_post(body=self.description, message_type='notification')
        return {'type': 'ir.actions.act_window_close'}



