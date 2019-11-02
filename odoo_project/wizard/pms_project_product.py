# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

CloseDescription = [
    ('done', '已完成'),
    ('subdivided', '已细分'),
    ('duplicate', '重复项'),
    ('postponed', '延期'),
    ('willnotdo', '不做'),
    ('cancel', '已取消'),
    ('bydesign', '设计如此'),
]
DEMANDSTATE = [
    ('draft', '草稿'),
    ('active', '激活'),
    ('closed', '关闭'),
]


class ProductDemandReview(models.TransientModel):
    _name = 'pms.product.demand.review'
    _description = "需求评审"

    demand_id = fields.Many2one('pms.product.demand', string='需求')
    review_user_id = fields.Many2one(comodel_name='res.users', string=u'由谁评审', required=True, default=lambda self: self.env.user)
    review_date = fields.Datetime(string=u'评审时间', required=True, default=fields.datetime.now())
    review_result = fields.Selection(string=u'评审结果', selection=[('pass', '确认通过'), ('reject', '拒绝')], required=True)
    assign_user = fields.Many2one(comodel_name='res.users', string=u'指派给')
    description = fields.Text(string=u'备注')
    close_description = fields.Selection(string=u'关闭原因', selection=CloseDescription)

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_id = context.get('active_id')
        result = super(ProductDemandReview, self).default_get(fields)
        if 'demand_id' in fields:
            result['demand_id'] = active_id
        return result

    @api.onchange('review_result')
    def _onchange_review_result(self):
        if self.review_result == 'pass':
            self.assign_user = self.env.user
        elif self.review_result == 'reject':
            self.assign_user = False
        else:
            return

    def confirmation_review(self):
        """
        评审需求
        :return:
        """
        if self.review_result == 'pass':
            data = {
                'review_user_id': self.review_user_id.id,
                'review_date': self.review_date,
                'review_result': self.review_result,
                'assign_user': self.assign_user.id if self.assign_user else False,
                'state': 'active',
            }
            self.demand_id.write(data)
            self.demand_id.message_post(body="已通过需求确认!<br/>{}".format(self.description), message_type='comment', subtype='mail.mt_comment')
        elif self.review_result == 'reject':
            data = {
                'state': 'closed',
                'review_user_id': self.review_user_id.id,
                'review_date': self.review_date,
                'review_result': self.review_result,
                'assign_user': False,
                'close_user': self.env.user.id,
                'close_date': self.review_date,
                'close_description': self.close_description,
            }
            self.demand_id.write(data)
            self.demand_id.message_post(body="已拒绝需求确认!<br/>备注：{}".format(self.description), message_type='comment', subtype='mail.mt_comment')
        return {'type': 'ir.actions.act_window_close'}


class ProductDemandAssign(models.TransientModel):
    _name = 'pms.product.demand.assign'
    _description = "需求指派"

    demand_id = fields.Many2one('pms.product.demand', string='需求')
    assign_user = fields.Many2one(comodel_name='res.users', string=u'指派给', required=True)
    description = fields.Text(string=u'备注')

    def confirmation_assign(self):
        """
        立即指派
        :return:
        """
        if self.demand_id.is_review:
            if self.demand_id.review_result != 'pass':
                raise UserError(_("需求暂未评审通过，请等待审批人确认后再指派！"))
        self.demand_id.write({'assign_user': self.assign_user.id, 'state': 'active'})
        if self.description:
            self.demand_id.message_post(body=self.description, message_type='comment', subtype='mail.mt_comment')

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_id = context.get('active_id')
        result = super(ProductDemandAssign, self).default_get(fields)
        if 'demand_id' in fields:
            result['demand_id'] = active_id
        return result


class ProductDemandClosed(models.TransientModel):
    _name = 'pms.product.demand.closed'
    _description = "关闭需求"

    demand_id = fields.Many2one('pms.product.demand', string='需求')
    close_description = fields.Selection(string=u'关闭原因', selection=CloseDescription, required=True)
    description = fields.Text(string=u'备注')

    def confirmation_closed(self):
        self.demand_id.write({
            'state': 'closed',
            'assign_user': False,
            'close_user': self.env.user.id,
            'close_date': fields.datetime.now(),
            'close_description': self.close_description,
        })
        if self.description:
            self.demand_id.message_post(body=self.description, message_type='comment', subtype='mail.mt_comment')

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_id = context.get('active_id')
        result = super(ProductDemandClosed, self).default_get(fields)
        if 'demand_id' in fields:
            result['demand_id'] = active_id
        return result


class ProductDemandActivation(models.TransientModel):
    _name = 'pms.product.demand.activation'
    _description = "激活需求"

    demand_id = fields.Many2one('pms.product.demand', string='需求')
    assign_user = fields.Many2one(comodel_name='res.users', string=u'指派给', required=True, default=lambda self: self.env.user)
    state = fields.Selection(string=u'激活状态', selection=DEMANDSTATE, default='active', required=True)
    description = fields.Text(string=u'备注')

    def confirmation_activation(self):
        self.demand_id.write({
            'state': self.state,
            'assign_user': self.assign_user.id,
        })
        if self.description:
            self.demand_id.message_post(body=self.description, message_type='comment', subtype='mail.mt_comment')

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_id = context.get('active_id')
        result = super(ProductDemandActivation, self).default_get(fields)
        if 'demand_id' in fields:
            result['demand_id'] = active_id
        return result


class ProductDemandDescription(models.TransientModel):
    _name = 'pms.product.demand.description'
    _description = "添加备注"

    demand_id = fields.Many2one('pms.product.demand', string='需求')
    cc_user_ids = fields.Many2many('res.users', 'pms_product_demand_res_users_cc_rel', string=u'抄送用户')
    description = fields.Text(string=u'备注信息', required=True)

    def confirmation_description(self):
        self.demand_id.message_post(body=self.description, message_type='comment', subtype='mail.mt_comment')

    @api.model
    def default_get(self, fields):
        context = dict(self._context or {})
        active_id = context.get('active_id')
        result = super(ProductDemandDescription, self).default_get(fields)
        if 'demand_id' in fields:
            result['demand_id'] = active_id
        return result