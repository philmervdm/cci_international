# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class resParner(models.Model):
    _inherit = 'res.partner'

    insurer_id = fields.Char('Insurer ID') # for ATA Carnet
    certificate_prefix = fields.Char('Certificate Line Prefix') # to prefix the line of invoicing of certificate of origin
    awex_eligible = fields.Selection([('unknown','Unknown'),('yes','Eligible'),('no','NOT ELIGIBLE')],string='AWEX Eligible',default='unknown')
