# -*- coding: utf-8 -*-

from odoo import models, fields, api

from collections import defaultdict
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import split_every
from psycopg2 import OperationalError

from odoo import api, fields, models, registry, _
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare, float_round

from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class ProcurementGroupMod(models.Model):
    _name = 'procurement_mod'
    _description = 'Procurement Requisition Modified'
    _order = "id desc"
    _inherit = 'procurement.group'

    """
    The procurement group class is used to group products together
    when computing procurements. (tasks, physical products, ...)

    The goal is that when you have one sales order of several products
    and the products are pulled from the same or several location(s), to keep
    having the moves grouped into pickings that represent the sales order.

    Used in: sales order (to group delivery order lines like the so), pull/push
    rules (to pack like the delivery order), on orderpoints (e.g. for wave picking
    all the similar products together).

    Grouping is made only if the source and the destination is the same.
    Suppose you have 4 lines on a picking from Output where 2 lines will need
    to come from Input (crossdock) and 2 lines coming from Stock -> Output As
    the four will have the same group ids from the SO, the move from input will
    have a stock.picking with 2 grouped lines and the move from stock will have
    2 grouped lines also.

    The name is usually the name of the original document (sales order) or a
    sequence computed if created manually.
    """

    partner_id = fields.Many2one('res.partner', 'Partner')
    name = fields.Char(
        'Reference',
        default=lambda self: self.env['ir.sequence'].next_by_code('procurement.group') or '',
        required=True)
    move_type = fields.Selection([
        ('direct', 'Partial'),
        ('one', 'All at once')], string='Delivery Type', default='direct',
        required=True)

    @api.model
    def run(self, product_id, product_qty, product_uom, location_id, name, origin, values):
        values.setdefault('company_id', self.env['res.company']._company_default_get('procurement.group'))
        values.setdefault('priority', '1')
        values.setdefault('date_planned', fields.Datetime.now())
        rule = self._get_rule(product_id, location_id, values)

        if not rule:
            raise UserError(_('No procurement rule found. Please verify the configuration of your routes'))

        getattr(rule, '_run_%s' % rule.action)(product_id, product_qty, product_uom, location_id, name, origin, values)
        return True

    @api.model
    def _search_rule(self, product_id, values, domain):
        """ First find a rule among the ones defined on the procurement
        group; then try on the routes defined for the product; finally fallback
        on the default behavior """
        if values.get('warehouse_id', False):
            domain = expression.AND([['|', ('warehouse_id', '=', values['warehouse_id'].id), ('warehouse_id', '=', False)], domain])
        Pull = self.env['procurement.rule']
        res = self.env['procurement.rule']
        if values.get('route_ids', False):
            res = Pull.search(expression.AND([[('route_id', 'in', values['route_ids'].ids)], domain]), order='route_sequence, sequence', limit=1)
        if not res:
            product_routes = product_id.route_ids | product_id.categ_id.total_route_ids
            if product_routes:
                res = Pull.search(expression.AND([[('route_id', 'in', product_routes.ids)], domain]), order='route_sequence, sequence', limit=1)
        if not res:
            warehouse_routes = values['warehouse_id'].route_ids
            if warehouse_routes:
                res = Pull.search(expression.AND([[('route_id', 'in', warehouse_routes.ids)], domain]), order='route_sequence, sequence', limit=1)
        return res

    @api.model
    def _get_rule(self, product_id, location_id, values):
        result = False
        location = location_id
        while (not result) and location:
            result = self._search_rule(product_id, values, [('location_id', '=', location.id)])
            location = location.location_id
        return result

    def _merge_domain(self, values, rule, group_id):
        return [
            ('group_id', '=', group_id), # extra logic?
            ('location_id', '=', rule.location_src_id.id),
            ('location_dest_id', '=', values['location_id'].id),
            ('picking_type_id', '=', rule.picking_type_id.id),
            ('picking_id.printed', '=', False),
            ('picking_id.state', 'in', ['draft', 'confirmed', 'waiting', 'assigned']),
            ('picking_id.backorder_id', '=', False),
            ('product_id', '=', values['product_id'].id)]

    @api.model
    def _get_exceptions_domain(self):
        return [('procure_method', '=', 'make_to_order'), ('move_orig_ids', '=', False)]

    @api.model
    def _procurement_from_orderpoint_get_order(self):
        return 'location_id'

    @api.model
    def _procurement_from_orderpoint_get_grouping_key(self, orderpoint_ids):
        orderpoints = self.env['stock.warehouse.orderpoint'].browse(orderpoint_ids)
        return orderpoints.location_id.id

    @api.model
    def _procurement_from_orderpoint_get_groups(self, orderpoint_ids):
        """ Make groups for a given orderpoint; by default schedule all operations in one without date """
        return [{'to_date': False, 'procurement_values': dict()}]

    @api.model
    def _procurement_from_orderpoint_post_process(self, orderpoint_ids):
        return True

    def _get_orderpoint_domain(self, company_id=False):
        domain = [('company_id', '=', company_id)] if company_id else []
        domain += [('product_id.active', '=', True)]
        return domain

    @api.model
    def _run_scheduler_tasks(self, _days, use_new_cursor = False, company_id = False):
        #_days = 21
        #today = datetime.datetime.combine(datetime.datetime.now(), datetime.time(00, 00, 00))
        today = datetime.now()
        fullfilment_range = (today + timedelta(days = _days)).strftime('%Y-%m-%d')

        # Minimum stock rules
        self.sudo()._procure_orderpoint_confirm(use_new_cursor=use_new_cursor, company_id=company_id)

        # Search all confirmed stock_moves and try to assign them
        #confirmed_moves = self.env['stock.move'].search([('state', '=', 'confirmed')], limit=None, order='priority desc, date_expected asc')
        ###### MODIFIED CONFIRMED MOVES.
        confirmed_moves = self.env['stock.move'].search(['&',('state', '=', 'confirmed'),('date', '<', fullfilment_range)], limit=None, order='priority desc, date_expected asc')
        for moves_chunk in split_every(100, confirmed_moves.ids):
            self.env['stock.move'].browse(moves_chunk)._action_assign()
            if use_new_cursor:
                self._cr.commit()

        exception_moves = self.env['stock.move'].search(self._get_exceptions_domain())
        for move in exception_moves:
            values = move._prepare_procurement_values()
            try:
                with self._cr.savepoint():
                    origin = (move.group_id and (move.group_id.name + ":") or "") + (move.rule_id and move.rule_id.name or move.origin or move.picking_id.name or "/")
                    self.run(move.product_id, move.product_uom_qty, move.product_uom, move.location_id, move.rule_id and move.rule_id.name or "/", origin, values)
            except UserError as error:
                self.env['procurement.rule']._log_next_activity(move.product_id, error.name)
        if use_new_cursor:
            self._cr.commit()

        # Merge duplicated quants
        self.env['stock.quant']._merge_quants()

    @api.model
    def run_scheduler(self, _days, use_new_cursor=False, company_id=False):
        """ Call the scheduler in order to check the running procurements (super method), to check the minimum stock rules
        and the availability of moves. This function is intended to be run for all the companies at the same time, so
        we run functions as SUPERUSER to avoid intercompanies and access rights issues. """
        
        #raise Warning((str)(use_new_cursor) + ' - ' + (str)(company_id))
        #raise Warning (self._procurement_from_orderpoint_get_order())
        try:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))  # TDE FIXME

            self._run_scheduler_tasks(_days, use_new_cursor=use_new_cursor, company_id=company_id)
            #self._run_scheduler_tasks(_days)
        finally:
            if use_new_cursor:
                try:
                    self._cr.close()
                except Exception:
                    pass
        return {}

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100