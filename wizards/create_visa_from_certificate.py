# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CreateVisaFromCertificateWizard(models.TransientModel):

    _name = 'create.visa.from.certificate.wizard'

    delegated_type_id = fields.Many2one(
        comodel_name='cci_international.delegated_type',
        string='Visa Type',
        required=True,
        domain=[('section', '=', 'visa')],
        help='Type of Visa created from this Certificate'
    )

    @api.multi
    def create_visa_from_certificate(self):

        self.ensure_one()

        SaleOrder = self.env['sale.order']
        origin = SaleOrder.browse(self._context.get('active_id', []))
        
        # Data to initiate on the new sale.order of section visa
        data = {'section': 'visa',
                'delegated_type_id': self.delegated_type_id.id,
                'partner_id': origin.partner_id.id,
                'goods_desc': origin.goods_desc,
                'goods_value': origin.goods_value,
                'originals': 1,
                'copies': 0,
                'pricelist_id': origin.pricelist_id.id,
                'destination_id': origin.destination_id.id,
                'client_order_ref': origin.client_order_ref,
                'certificate_id': origin.id,
                'asker_name': origin.asker_name,
                'sender_name': origin.sender_name,
               }
        new_visa = SaleOrder.create(data)
        #if new_visa:
        #    new_visa.onchange_partner_id_delegated()
        #    new_visa.write({'asker_name': origin.asker_name,
        #                    'sender_name': origin.sender_name,
        #                   })
        return {
            'name': 'Created Visa',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('cci_international.view_visa_tree').id, 'tree'),
                (self.env.ref('cci_international.view_cci_visa_form').id, 'form'),
            ],
            'domain': [('id', 'in', [new_visa.id,])],
        }

