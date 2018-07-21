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

    



    @api.model
    def _run_scheduler_tasks(self, fullfilment_range, use_new_cursor = False, company_id = False):
        #_days = 21
        #today = datetime.datetime.combine(datetime.datetime.now(), datetime.time(00, 00, 00))
        #today = datetime.now()
        #fullfilment_range = (today + timedelta(days = 21)).strftime('%Y-%m-%d')

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
    def run_scheduler(self, fullfilment_range, use_new_cursor=False, company_id=False):
        """ Call the scheduler in order to check the running procurements (super method), to check the minimum stock rules
        and the availability of moves. This function is intended to be run for all the companies at the same time, so
        we run functions as SUPERUSER to avoid intercompanies and access rights issues. """

        #raise Warning(fullfilment_range)
        try:
            if use_new_cursor:
                cr = registry(self._cr.dbname).cursor()
                self = self.with_env(self.env(cr=cr))  # TDE FIXME

            #self._run_scheduler_tasks(fullfilment_range, use_new_cursor=use_new_cursor, company_id=company_id)
            self._run_scheduler_tasks(self, fullfilment_range)
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