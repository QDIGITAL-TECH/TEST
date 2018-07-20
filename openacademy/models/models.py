# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import models, fields, api

# class openacademy(models.Model):
#     _name = 'openacademy.openacademy'

#     name = fields.Char()

class Ticket(models.Model):
    _name = 'openacademy.ticket'

    name = fields.Char(string = 'Name', required = True)
    summary = fields.Text()
    detail_description = fields.Text(string = "Detail Description")

    #job_id = fields.One2Many('openacademy.job', string='Job')
    #created_by_id = fields.Many2one('res.users', ondelete='set null', string="Created By", index=True)

    created_by = fields.Many2one('res.users', ondelete='set null', string = 'Current User', default = lambda self: self.env.user, readonly = True)

    ticket_num = fields.Char(string = 'Ticket Number', default=lambda self: self._get_next_ref(), index=True, readonly = True)

    tempvar = fields.Char(string = 'Temp Var')
    
    @api.model
    def _get_next_ref(self):
        sequence = self.env['ir.sequence'].next_by_code('openacademy.ticket')
        #nxt = sequence.get_next_char(sequence.number_next_actual)
        return sequence

    #@api.model
    #def create(self, vals):
        #res = super(Ticket, self).create(vals)
        #vals['sequence_id'] = self.env['ir.sequence'].get('openacademy.ticket')
        #vals['ticket_num'] = self.env['ir.sequence'].next_by_code('openacademy.ticket')
        #ticket_num = vals['sequence_id']
        #return super(Ticket, self).create(vals)


class Job(models.Model):
    _name = 'openacademy.job'

    name = fields.Char(string = 'Name', required = True)
    
    #it_support_id = fields.Many2Many('res.partner', string="Worker")
    #ticket_id = fields.Many2One('openacademy.ticket', string="Ticket")
    #it_support_id = fields.Many2Many('res.partner', string="Worker")
    #it_support_ids = fields.Many2one('res.user', string="Workers", ondelete='set null', index=True)
    by_id = fields.Many2one('res.users',
        ondelete='set null', string="By", index=True)
    ticket_id = fields.Many2one('openacademy.ticket',
        ondelete='set null', string="Ticket", index=True)
    start_time = fields.Datetime()
    

