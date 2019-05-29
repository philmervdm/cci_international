# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    #_name = "sale.order"
    _inherit = 'sale.order'

    section = fields.Selection([('sale_order','Classic Sale Order'),
                                ('certificate','Origin Certificate'),
                                ('visa','Visa'),
                                ('ata_carnet','ATA Carnet'),
                                ('embassy','Embassy Folder'),
                                ('translation','Translation Folder')],
                               string='Section',
                               default='sale_order'
                              )
    internal_ref = fields.Char('Internal Reference')
    delegated_type_id = fields.Many2one('cci_international.delegated_type',domain="[('section','=',section)]")
    destination_id = fields.Many2one('res.country')
    digital_ref = fields.Char('Digital Reference')
    asker_name = fields.Char('Asker Name')
    asker_street = fields.Char('Asker Address')
    asker_city = fields.Char('Asker City')
    sender_name = fields.Char('Sender Name')
    sender_street = fields.Char('Sender Address')
    sender_city = fields.Char('Sender City')
    special = fields.Selection([('none','None'),
                                ('commercial_reason','Commercial Reason'),
                                ('substitution','Substitution')],
                               string='Special',
                               default='none')
    goods_desc = fields.Char('Goods Description')
    goods_value = fields.Float('Goods Value',digits=(16, 2))
    originals = fields.Integer('Originals',default=1)
    copies = fields.Integer('Copies',default=0)
    tovalidate = fields.Char('To Validate')
    embassy_id = fields.Many2one('sale.order','Linked Embassy Folder')
    certificate_id = fields.Many2one('sale.order', string='Linked Certificate')
    visa_ids = fields.One2many('sale.order', 'certificate_id', string='Linked Visas')
    linked_doc_ids = fields.One2many('sale.order','embassy_id', string='Linked Docs')
    spf_send_date = fields.Date('SPF Sending')
    origin_ids = fields.Many2many('res.country','delegated_origin_country_rel','sale_order_id','res_country_id',string='Origin Countries')
    custom_ids = fields.Many2many('account.intrastat.code','delegated_custom_rel','sale_order_id','intrastat_code_id',string='Customs Codes')
    ata_usage = fields.Char('Usage')
    ata_area_id = fields.Many2one('res.country.group',string='ATA Area')
    insurer_id = fields.Char(string='Insurer ID', store=False, related='partner_id.insurer_id')
    ata_warranty = fields.Float('Standard Warranty',digits=(16, 2))
    ata_pages_initial = fields.Integer('Initial Pages')
    ata_pages_additional = fields.Integer('Additional Pages')
    ata_validity_date = fields.Date('End of Validity')
    ata_return_date = fields.Date('Date of Return')
    
    @api.model
    def create_order_line_from_product_obj(self,prod,qty):
        new_order_line_values = {'display_type': False,
                                 'sequence': 1,
                                 'qty_delivered_manual': qty,
                                 'price_unit': prod.list_price,
                                 'product_id': prod.id,
                                 'name': prod.name or 'certificate',
                                 'order_id': self.id}
        self.env['sale.order.line'].create(new_order_line_values)
        return True

    @api.model
    def create_order_line_from_product_managed(self,prod,qty,forced_sequence,final_name,additional_forced_price=False):

        SaleOrder = self.env['sale.order']
        SaleOrderLine = self.env['sale.order.line']

        product = prod.with_context(
            lang=self.partner_id.lang,
            partner=self.partner_id,
            quantity=qty,
            date=self.date_order,
            pricelist=self.pricelist_id.id
        )

        # NOTE: Obtain suitable rule, if any, then replicate the same
        #       computation done by pricelist object...
        result = self.pricelist_id._compute_price_rule([(product, qty, self.partner_id)])

        rule_id = result[product.id][1]
        price = prod.list_price

        convert_to_price_uom = (lambda price: product.uom_id._compute_price(price, product.uom_id))

        if rule_id:

            rule = self.env['product.pricelist.item'].browse(rule_id)

            if rule.compute_price == 'fixed':
                price = convert_to_price_uom(rule.fixed_price)
            elif rule.compute_price == 'percentage':
                price = (price - (price * (rule.percent_price / 100))) or 0.0
            else:
                # complete formula
                price_limit = price
                price = (price - (price * (rule.price_discount / 100))) or 0.0
                if rule.price_round:
                    price = float_round(price, precision_rounding=rule.price_round)

                if rule.price_surcharge:
                    price_surcharge = convert_to_price_uom(rule.price_surcharge)
                    price += price_surcharge

                if rule.price_min_margin:
                    price_min_margin = convert_to_price_uom(rule.price_min_margin)
                    price = max(price, price_limit + price_min_margin)

                if rule.price_max_margin:
                    price_max_margin = convert_to_price_uom(rule.price_max_margin)
                    price = min(price, price_limit + price_max_margin)
        if additional_forced_price:
            price += additional_forced_price
              
        sale_order_line = SaleOrderLine.new({
            'order_id': self.id,
            'product_id': product.id,
            'product_uom_qty': qty,
            'event_ticket_id': False,
            'price_unit': price
        })

        sale_order_line_values = sale_order_line._convert_to_write({name: sale_order_line[name] for name in sale_order_line._cache})
        sale_order_line_values['name'] = final_name
        sale_order_line_values['sequence'] = forced_sequence
        sale_order_line = sale_order_line.create(sale_order_line_values)
        return True

    @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id_delegated(self):
        """
        Update the following fields when the partner is changed:
        - Asker name, street and city
        - Sender name, street and city
        """
        if not self.partner_id:
            self.update({
                'asker_name': False,
                'asker_street': False,
                'asker_city': False,
                'sender_name': False,
                'sender_street': False,
                'sender_city': False,
            })
            return

        values = {
            'asker_name': self.partner_id.name or False,
            'asker_street': self.partner_id.street or False,
            'asker_city': (self.partner_id.zip or '') + ' ' + (self.partner_id.city or ''),
            'sender_name': self.partner_id.name or False,
            'sender_street': self.partner_id.street or False,
            'sender_city': (self.partner_id.zip or '') + ' ' + (self.partner_id.city or ''),
        }
        self.update(values)

    @api.model
    def create(self, vals):
        section = vals.get('section','sale_order')
        if section in ['certificate','visa','embassy','ata_carnet','translation']:
            delegated_type_id = vals.get('delegated_type_id',False)
            if vals.get('delegated_type_id',False):
                delegated_type = self.env['cci_international.delegated_type'].browse(vals.get('delegated_type_id'))
                if delegated_type.section != section:
                    raise UserError(_('The type of documents doesn\'t correspond to section.'))
            else:
                raise UserError(_('You MUST give the type of document.'))
        # check for mandatory fields and give default values
        if section == 'certificate':
            if not vals.get('destination_id',False):
                raise UserError(_('You MUST give the destination country !'))
            if not vals.get('goods_desc',False):
                raise UserError(_('You MUST give the goods description !'))
            goods_value = vals.get('goods_value',0.0)
            if (goods_value >= -0.001 and goods_value <= 0.001) and not delegated_type.accept_null_value:
                raise UserError(_('You MUST give the value of the goods !'))
            if not vals.get('origin_ids',False):
                raise UserError(_('You MUST give at least one origin country.'))
            else:
                if not vals.get('origin_ids')[0][2]:
                    raise UserError(_('You MUST give at least one origin country.'))
            if not vals.get('custom_ids',False):
                raise UserError(_('You MUST give at least one Custom Code.'))
            else:
                if not vals.get('custom_ids')[0][2]:
                    raise UserError(_('You MUST give at least one Custom Code.'))
            if not vals.get('internal_ref',False):
                vals['internal_ref'] = delegated_type.sequence_id.next_by_id()
            vals['originals'] = 1
        elif section == 'visa':
            originals = vals.get('originals',0)
            if originals < 1:
                raise UserError(_('You MUST give the number of originals !'))
            if not vals.get('internal_ref',False):
                vals['internal_ref'] = delegated_type.sequence_id.next_by_id()
        elif section == 'ata_carnet':
            if not vals.get('ata_usage',''):
                raise UserError(_('You MUST give the usage of the ATA Carnet !'))
            if not vals.get('ata_area_id',False):
                raise UserError(_('You MUST give the area of usage of the ATA Carnet !\nThis can be \'ALL COUNTRIES\'...'))
            if not vals.get('internal_ref',False):
                vals['internal_ref'] = delegated_type.sequence_id.next_by_id()
        result = super(SaleOrder, self).create(vals)
        return result

    @api.multi
    def write(self, values):
        if self.section in ['certificate','visa']:
            original_product_line = False
            if self.order_line:
                for soline in self.order_line:
                    if soline.product_id and soline.product_id.id == self.delegated_type_id.original_product_id.id:
                        original_product_line = True
                        break
            if not original_product_line and values.get('order_line',False):
                for case in values.get('order_line'):
                    if case[0] in [0,1]:
                        linked_product_id = case[2].get('product_id',0)
                        if linked_product_id == self.delegated_type.original_product_id.id:
                            original_product_line = True
            copy_product_line = False
            if self.order_line:
                for soline in self.order_line:
                    if soline.product_id and soline.product_id.id == self.delegated_type_id.copy_product_id.id:
                        copy_product_line = True
                        break
            if not copy_product_line and values.get('order_line',False):
                for case in values.get('order_line'):
                    if case[0] in [0,1]:
                        linked_product_id = case[2].get('product_id',0)
                        if linked_product_id == self.delegated_type.copy_product_id.id:
                            copy_product_line = True
            if self.section == 'certificate':
                final_name = ('%s %s %s %s' % (self.partner_id.certificate_prefix or '',
                                               values.get('client_order_ref',self.client_order_ref or ''),
                                               self.internal_ref or '',
                                               self.destination_id.name or ''
                                              )).strip().replace('  ',' ')
            elif self.section == 'visa':
                customer_ref = values.get('client_order_ref',self.client_order_ref or '')
                if customer_ref:
                    final_name = '%s [%s]' % (customer_ref, self.internal_ref)
                else:
                    final_name = '%s %s' % (self.internal_ref,self.destination_id.name or '')
            if not original_product_line:
                #self.create_order_line_from_product_obj(self.delegated_type_id.original_product_id,1.0)
                number_of_originals = values.get('originals',self.originals or 1)
                self.create_order_line_from_product_managed(self.delegated_type_id.original_product_id,number_of_originals,1,final_name)
            number_of_copies = values.get('copies',self.copies or 0)
            if number_of_copies and not copy_product_line:
                self.create_order_line_from_product_managed(self.delegated_type_id.copy_product_id,number_of_copies,5,final_name)
            result = super(SaleOrder, self).write(values)
        elif self.section == 'embassy':
            # nothing special to do
            result = super(SaleOrder, self).write(values)
        elif self.section == 'ata_carnet':
            # calculation of additional prioce based on covered value of the goods
            base_value = values.get('goods_value',self.goods_value or 0.0)
            if base_value < 25000.0:
                add_price = base_value * 0.00839
            elif (base_value >= 25000.0) and (base_value < 75000.0):
                add_price = base_value * 0.00655
            elif (base_value >= 75000.0) and (base_value < 250000.0):
                add_price = base_value * 0.00419
            elif base_value >= 250000.0:
                add_price = base_value * 0.00276
            # check if lines already created
            original_product_line = False
            if self.order_line:
                for soline in self.order_line:
                    if soline.product_id and soline.product_id.id == self.delegated_type_id.original_product_id.id:
                        original_product_line = True
                        break
            if not original_product_line and values.get('order_line',False):
                for case in values.get('order_line'):
                    if case[0] in [0,1]:
                        linked_product_id = case[2].get('product_id',0)
                        if linked_product_id == self.delegated_type.original_product_id.id:
                            original_product_line = True
            copy_product_line = False
            if self.order_line:
                for soline in self.order_line:
                    if soline.product_id and soline.product_id.id == self.delegated_type_id.copy_product_id.id:
                        copy_product_line = True
                        break
            if not copy_product_line and values.get('order_line',False):
                for case in values.get('order_line'):
                    if case[0] in [0,1]:
                        linked_product_id = case[2].get('product_id',0)
                        if linked_product_id == self.delegated_type.copy_product_id.id:
                            copy_product_line = True
            warranty_value = values.get('ata_warranty',self.ata_warranty or 0.0)
            if warranty_value > 0.001:
                warranty_product_line = False
                if self.order_line:
                    for soline in self.order_line:
                        if soline.product_id and soline.product_id.id == self.delegated_type_id.warranty_product_id.id:
                            warranty_product_line = True
                            break
                if not warranty_product_line and values.get('order_line',False):
                    for case in values.get('order_line'):
                        if case[0] in [0,1]:
                            linked_product_id = case[2].get('product_id',0)
                            if linked_product_id == self.delegated_type.warranty_product_id.id:
                                warranty_product_line = True
            if not original_product_line:
                self.create_order_line_from_product_managed(self.delegated_type_id.original_product_id,1,1,(self.internal_ref or '').strip().replace('  ',' '),add_price)
            number_of_copies = values.get('ata_pages_initial',self.ata_pages_initial or 0)
            if number_of_copies and not copy_product_line:
                self.create_order_line_from_product_managed(self.delegated_type_id.copy_product_id,number_of_copies,5,(self.internal_ref or '').strip().replace('  ',' '))
            if not warranty_product_line and warranty_value > 0.001:
                self.create_order_line_from_product_managed(self.delegated_type_id.warranty_product_id,1,9,(self.internal_ref or '').strip().replace('  ',' '))
            result = super(SaleOrder, self).write(values)
        return result


