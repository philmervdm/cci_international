# -*- coding: utf-8 -*-

from odoo import models, fields, api

class DelegatedType(models.Model):
    _name = 'cci_international.delegated_type'

    name = fields.Char('Name',required=True)
    code = fields.Char('Code')
    sequence_id = fields.Many2one('ir.sequence','Sequence',required=True)
    section = fields.Selection([('certificate','Origin Certificate'),
                                ('visa','Visa'),
                                ('embassy','Embassy Folder'),
                                ('atacarnet','ATA Carnet'),
                                ('translation','Translation Folder')]
                               ,'Section',required=True,default='visa')
    accept_null_value = fields.Boolean('Accept Null Value',default=False)
    digital = fields.Boolean('Only Digital Type',default=True)
    digital_code = fields.Char('Name in Digital File')
    federation_identification = fields.Char('Federation ID')
    original_product_id = fields.Many2one('product.product','Product for Originals')
    copy_product_id = fields.Many2one('product.product','Product for Copies')
    warranty_product_id = fields.Many2one('product.product','Product for Standard Warranty')
    ownrisk_warranty_product_id = fields.Many2one('product.product','Product for Own Risk Warranty')
    cba_product_id = fields.Many2one('product.product','Product for C.B.A.')
    ministry_product_id = fields.Many2one('product.product','Product for Ministry')
    embcons_product_id = fields.Many2one('product.product','Product for Embassy/Consulate')
    translation_product_id = fields.Many2one('product.product','Product for Translation')
    administrative_product_id = fields.Many2one('product.product','Product for Administrative Costs')
    courier_product_id = fields.Many2one('product.product','Product for Courier Costs')
    postal_product_id = fields.Many2one('product.product','Product for Postal Costs')

