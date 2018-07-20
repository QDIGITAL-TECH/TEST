# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict
from datetime import datetime
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
    _name = 'procurement.group.mod'
    _description = 'Procurement Requisition Modified'
    _order = "id desc"
    _inherit = 'procurement.group'
