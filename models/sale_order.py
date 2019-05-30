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
    #goods_value = fields.Float('Goods Value',digits=(16, 2))
    goods_value = fields.Monetary('Goods Value')
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
    ata_warranty = fields.Monetary('Standard Warranty')
    ata_pages_initial = fields.Integer('Initial Pages')
    ata_pages_additional = fields.Integer('Additional Pages')
    ata_validity_date = fields.Date('End of Validity')
    ata_return_date = fields.Date('Date of Return')
    partner_awex_eligible = fields.Selection([('unknown','Unknown'),('yes','Eligible'),('no','NOT ELIGIBLE')],string='Partner Awex Eligible', store=False, related='partner_id.awex_eligible')
    awex_eligible = fields.Boolean('Awex Eligible', default=False)
    translation_amount = fields.Monetary('Translation Amount')
    cci_fee = fields.Integer('Fee (%)',default=10)
    awex_intervention = fields.Monetary('Awex Intervention')
    credit_line_id = fields.Many2one('cci_international.credit_line',string='Credit Line')
    
    #@api.model
    #def create_order_line_from_product_obj(self,prod,qty):
    #    new_order_line_values = {'display_type': False,
    #                             'sequence': 1,
    #                             'qty_delivered_manual': qty,
    #                             'price_unit': prod.list_price,
    #                             'product_id': prod.id,
    #                             'name': prod.name or 'certificate',
    #                             'order_id': self.id}
    #    self.env['sale.order.line'].create(new_order_line_values)
    #    return True

    @api.multi
    def set_awex_intervention(self):
        CreditLine = self.env['cci_international.credit_line']
        if self.section in ['embassy','translation']:
            if self.awex_eligible and self.translation_amount > 0.0 and self.awex_intervention == 0.00:
                clines = CreditLine.search([('from_date','<=',self.date_order.strftime('%Y-%m-%d')),('to_date','>=',self.date_order.strftime('%Y-%m-%d'))])
                if len(clines) == 1:
                    self.credit_line_id = clines.id
                    intervention = self.credit_line_id.get_available_intervention(self.translation_amount,self.partner_id)
                    if intervention > 0.001:
                        self.awex_intervention = intervention
        return True
                        
    @api.model
    def get_order_line_from_product_managed(self,prod,qty,final_name):

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
              
        sale_order_line = SaleOrderLine.new({
            'order_id': self.id,
            'product_id': product.id,
            'product_uom_qty': qty,
            'event_ticket_id': False,
            'price_unit': price
        })
        sale_order_line_values = sale_order_line._convert_to_write({name: sale_order_line[name] for name in sale_order_line._cache})
        sale_order_line_values['name'] = final_name
        return sale_order_line_values

    @api.model
    def get_certificate_name(self,prefix,customer_ref,internal_ref,destination_name):
        return ('%s %s %s %s' % (prefix or '',
                                 customer_ref or '',
                                 internal_ref or '',
                                 destination_name or ''
                                )).strip().replace('  ',' ')

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
                'awex_eligible': False,
            })
            return

        values = {
            'asker_name': self.partner_id.name or False,
            'asker_street': self.partner_id.street or False,
            'asker_city': (self.partner_id.zip or '') + ' ' + (self.partner_id.city or ''),
            'sender_name': self.partner_id.name or False,
            'sender_street': self.partner_id.street or False,
            'sender_city': (self.partner_id.zip or '') + ' ' + (self.partner_id.city or ''),
            'awex_eligible': (self.partner_id.awex_eligible == 'yes')
        }
        self.update(values)

    @api.model
    def get_line_by_product_id(self,product):
        id_result = False
        if self.order_line:
            for soline in self.order_line:
                if soline.product_id and soline.product_id.id == product.id:
                    id_result = soline.id
                    break
        return id_result

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
            vals['internal_ref'] = delegated_type.sequence_id.next_by_id()
            vals['originals'] = 1
        elif section == 'visa':
            originals = vals.get('originals',0)
            if originals < 1:
                raise UserError(_('You MUST give the number of originals !'))
            vals['internal_ref'] = delegated_type.sequence_id.next_by_id()
        elif section == 'embassy':
            vals['internal_ref'] = delegated_type.sequence_id.next_by_id()
        elif section == 'ata_carnet':
            if not vals.get('ata_usage',''):
                raise UserError(_('You MUST give the usage of the ATA Carnet !'))
            if not vals.get('ata_area_id',False):
                raise UserError(_('You MUST give the area of usage of the ATA Carnet !\nThis can be \'ALL COUNTRIES\'...'))
            vals['internal_ref'] = delegated_type.sequence_id.next_by_id()
        elif section == 'translation':
            vals['internal_ref'] = delegated_type.sequence_id.next_by_id()
                
        result = super(SaleOrder, self).create(vals)
        
        SaleOrderLine = self.env['sale.order.line']
        if section == 'certificate':
            final_name = self.get_certificate_name(result.partner_id.certificate_prefix,
                                                   result.client_order_ref,
                                                   result.internal_ref,
                                                   result.destination_id.name)
            line_data = result.get_order_line_from_product_managed(result.delegated_type_id.original_product_id,result.originals,final_name)
            line_data['name'] += _(' - Originals')
            line_data['sequence'] = 1
            SaleOrderLine.create(line_data)
            if result.copies:
                line_data = result.get_order_line_from_product_managed(result.delegated_type_id.copy_product_id,result.copies,final_name)
                line_data['name'] += _(' - Copies')
                line_data['sequence'] = 5
                SaleOrderLine.create(line_data)
        elif section == 'visa':
            customer_ref = result.client_order_ref or ''
            if customer_ref:
                final_name = '%s [%s]' % (customer_ref, result.internal_ref)
            else:
                final_name = '%s %s' % (result.internal_ref,result.destination_id.name or '')
            line_data = result.get_order_line_from_product_managed(result.delegated_type_id.original_product_id,result.originals,final_name)
            line_data['name'] += _(' - Originals')
            line_data['sequence'] = 1
            SaleOrderLine.create(line_data)
            if result.copies:
                line_data = result.get_order_line_from_product_managed(result.delegated_type_id.copy_product_id,result.copies,final_name)
                line_data['name'] += _(' - Copies')
                line_data['sequence'] = 5
                SaleOrderLine.create(line_data)
        elif section == 'ata_carnet':
            # calculation of additional price based on covered value of the goods
            base_value = result.goods_value or 0.0
            if base_value < 25000.0:
                add_price = base_value * 0.00839
            elif (base_value >= 25000.0) and (base_value < 75000.0):
                add_price = base_value * 0.00655
            elif (base_value >= 75000.0) and (base_value < 250000.0):
                add_price = base_value * 0.00419
            elif base_value >= 250000.0:
                add_price = base_value * 0.00276
            final_name = result.internal_ref
            line_data = result.get_order_line_from_product_managed(result.delegated_type_id.original_product_id,1,final_name)
            line_data['name'] += _(' - Base Price')
            line_data['sequence'] = 1
            line_data['price_unit'] += add_price
            SaleOrderLine.create(line_data)
            if result.ata_pages_initial:
                line_data = result.get_order_line_from_product_managed(result.delegated_type_id.copy_product_id,result.ata_pages_initial,final_name)
                line_data['name'] += _(' - Pages')
                line_data['sequence'] = 5
                SaleOrderLine.create(line_data)
            if result.ata_warranty > 0.001:
                line_data = result.get_order_line_from_product_managed(result.delegated_type_id.warranty_product_id,1,final_name)
                line_data['name'] += _(' - Warranty')
                line_data['price_unit'] = result.ata_warranty
                line_data['sequence'] = 9
                SaleOrderLine.create(line_data)
        elif section == 'translation':
            final_name = ('%s %s' % (result.internal_ref or '',
                                     result.client_order_ref or '',
                                    )).strip().replace('  ',' ')
            line_data = result.get_order_line_from_product_managed(result.delegated_type_id.translation_product_id,1,final_name)
            line_data['name'] += _(' - Translation Costs')
            line_data['sequence'] = 1
            line_data['price_unit'] = result.translation_amount
            SaleOrderLine.create(line_data)
            if result.cci_fee > 0:
                line_data = result.get_order_line_from_product_managed(result.delegated_type_id.administrative_product_id,1,final_name)
                line_data['name'] += _(' - Administrative Costs')
                line_data['price_unit'] = round(result.translation_amount * result.cci_fee / 100, 2)
                line_data['sequence'] = 5
                SaleOrderLine.create(line_data)
        return result

    @api.multi
    def write(self, values):
        SaleOrderLine = self.env['sale.order.line']
        if self.section == 'certificate':
            # change in originals line
            if 'client_order_ref' in values or 'destination_id' in values:
                if 'destination_id' in values:
                    final_destination_name = self.env['res.country'].browse(values['destination_id']).name
                else:
                    final_destination_name = self.destination_id.name
                final_name = self.get_certificate_name(self.partner_id.certificate_prefix,
                                              values.get('client_order_ref',self.client_order_ref or ''),
                                              self.internal_ref,
                                              final_destination_name or '')
                orig_line_id = self.get_line_by_product_id(self.delegated_type_id.original_product_id)
                if orig_line_id:
                    line_data = SaleOrderLine.browse(orig_line_id)
                    line_data.name = final_name + _(' - Originals')
                else:
                    line_data = self.get_order_line_from_product_managed(self.delegated_type_id.original_product_id,1,final_name)
                    line_data['name'] += _(' - Originals')
                    line_data['sequence'] = 1
                    SaleOrderLine.create(line_data)
            # change in copies line
            if 'client_order_ref' in values or 'destination_id' in values or \
               'copies' in values:
                final_number_of_copies = values.get('copies',self.copies or 0)
                copies_line_id = self.get_line_by_product_id(self.delegated_type_id.copy_product_id)
                
                if final_number_of_copies == 0:
                    if copies_line_id > 0:
                        # insert into values the deleting of the copies line
                        if 'order_line' in values:
                            values['order_line'] = values['order_line'].append([2,[copies_line_id,]])
                        else:
                            values['order_line'] = ([2,[copies_line_id,]],)
                else:
                    if 'destination_id' in values:
                        final_destination_name = self.env['res.country'].browse(values['destination_id']).name
                    else:
                        final_destination_name = self.destination_id.name
                    final_name = self.get_certificate_name(self.partner_id.certificate_prefix,
                                                  values.get('client_order_ref',self.client_order_ref or ''),
                                                  self.internal_ref,
                                                  final_destination_name or '')
                    if copies_line_id:
                        line_data = SaleOrderLine.browse(copies_line_id)
                        line_data.product_uom_qty = final_number_of_copies
                        line_data.name = final_name + _(' - Copies')
                    else:
                        line_data = self.get_order_line_from_product_managed(self.delegated_type_id.copy_product_id,final_number_of_copies,final_name)
                        line_data['name'] += _(' - Copies')
                        line_data['sequence'] = 5
                        SaleOrderLine.create(line_data)
            result = super(SaleOrder, self).write(values)
        elif self.section == 'visa':
            # change in originals line
            if 'client_order_ref' in values or 'destination_id' in values or \
                'originals' in values:
                if 'destination_id' in values:
                    final_destination_name = self.env['res.country'].browse(values['destination_id']).name
                else:
                    final_destination_name = self.destination_id.name
                customer_ref = values.get('client_order_ref',self.client_order_ref or '')
                if customer_ref:
                    final_name = '%s [%s]' % (customer_ref, self.internal_ref)
                else:
                    final_name = '%s %s' % (self.internal_ref,final_destination_name or '')
                orig_line_id = self.get_line_by_product_id(self.delegated_type_id.original_product_id)
                if orig_line_id:
                    line_data = SaleOrderLine.browse(orig_line_id)
                    line_data.name = final_name + _(' - Copies')
                    line_data.product_uom_qty = values.get('originals',self.originals or 1)
                else:
                    line_data = self.get_order_line_from_product_managed(self.delegated_type_id.original_product_id,values.get('originals',self.originals or 1),final_name)
                    line_data['name'] += _(' - Copies')
                    line_data['sequence'] = 5
                    SaleOrderLine.create(line_data)
            # change in copies line
            if 'client_order_ref' in values or 'destination_id' in values or \
               'copies' in values:
                final_number_of_copies = values.get('copies',self.copies or 0)
                copies_line_id = self.get_line_by_product_id(self.delegated_type_id.copy_product_id)
                if final_number_of_copies == 0:
                    if copies_line_id > 0:
                        # insert into values the deleting of the copies line
                        if 'order_line' in values:
                            values['order_line'] = values['order_line'].append([2,[copies_line_id,]])
                        else:
                            values['order_line'] = ([2,[copies_line_id,]],)
                else:
                    if 'destination_id' in values:
                        final_destination_name = self.env['res.country'].browse(values['destination_id']).name
                    else:
                        final_destination_name = self.destination_id.name
                    customer_ref = values.get('client_order_ref',self.client_order_ref or '')
                    if customer_ref:
                        final_name = '%s [%s]' % (customer_ref, self.internal_ref)
                    else:
                        final_name = '%s %s' % (self.internal_ref,final_destination_name or '')
                    if copies_line_id:
                        line_data = SaleOrderLine.browse(copies_line_id)
                        line_data.product_uom_qty = final_number_of_copies
                        line_data.name = final_name + _(' - Copies')
                    else:
                        line_data = self.get_order_line_from_product_managed(self.delegated_type_id.copy_product_id,final_number_of_copies,final_name)
                        line_data['name'] += _(' - Copies')
                        line_data['sequence'] = 5
                        SaleOrderLine.create(line_data)
            result = super(SaleOrder, self).write(values)
        elif self.section == 'embassy':
            # nothing special to do
            result = super(SaleOrder, self).write(values)
        elif self.section == 'ata_carnet':
            # change in originals line
            if 'goods_value' in values:
                # calculation of additional price based on covered value of the goods
                base_value = values.get('goods_value',0.0)
                if base_value < 25000.0:
                    add_price = base_value * 0.00839
                elif (base_value >= 25000.0) and (base_value < 75000.0):
                    add_price = base_value * 0.00655
                elif (base_value >= 75000.0) and (base_value < 250000.0):
                    add_price = base_value * 0.00419
                elif base_value >= 250000.0:
                    add_price = base_value * 0.00276
                final_name = self.internal_ref
                orig_line_id = self.get_line_by_product_id(self.delegated_type_id.original_product_id)
                if orig_line_id:
                    # just to have the base price
                    new_line_data = self.get_order_line_from_product_managed(self.delegated_type_id.original_product_id,1,final_name)
                    line_data = SaleOrderLine.browse(orig_line_id)
                    line_data.price_unit = new_line_data['price_unit'] + add_price
                else:
                    line_data = self.get_order_line_from_product_managed(self.delegated_type_id.original_product_id,1,final_name)
                    line_data['name'] += _(' - Base Price')
                    line_data['price_unit'] += add_price
                    line_data['sequence'] = 1
                    SaleOrderLine.create(line_data)
            # changes in copies line
            if 'ata_pages_initial' in values:
                final_number_of_copies = values.get('ata_pages_initial',self.ata_pages_initial or 0)
                copies_line_id = self.get_line_by_product_id(self.delegated_type_id.copy_product_id)
                if final_number_of_copies == 0:
                    if copies_line_id > 0:
                        # insert into values the deleting of the copies line
                        if 'order_line' in values:
                            values['order_line'] = values['order_line'].append([2,[copies_line_id,]])
                        else:
                            values['order_line'] = ([2,[copies_line_id,]],)
                else:
                    if copies_line_id:
                        line_data = SaleOrderLine.browse(copies_line_id)
                        line_data.product_uom_qty = final_number_of_copies
                    else:
                        final_name = self.internal_ref or ''
                        line_data = self.get_order_line_from_product_managed(self.delegated_type_id.copy_product_id,final_number_of_copies,final_name)
                        line_data['name'] += _(' - Copies')
                        line_data['sequence'] = 5
                        SaleOrderLine.create(line_data)
            # changes in warranty line
            if 'ata_warranty' in values:
                final_warranty = values.get('ata_warranty',self.ata_warranty or 0.0)
                warranty_line_id = self.get_line_by_product_id(self.delegated_type_id.warranty_product_id)
                if final_warranty == 0.0:
                    if warranty_line_id > 0:
                        # insert into values the deleting of the warranty line
                        if 'order_line' in values:
                            values['order_line'] = values['order_line'].append([2,[warranty_line_id,]])
                        else:
                            values['order_line'] = ([2,[warranty_line_id,]],)
                else:
                    if warranty_line_id:
                        line_data = SaleOrderLine.browse(warranty_line_id)
                        line_data.price_unit = final_warranty
                    else:
                        final_name = self.internal_ref or ''
                        line_data = self.get_order_line_from_product_managed(self.delegated_type_id.warranty_product_id,final_number_of_copies,final_name)
                        line_data['name'] += _(' - Warranty')
                        line_data['sequence'] = 9
                        line_data['price_unit'] = final_warranty
                        SaleOrderLine.create(line_data)
            result = super(SaleOrder, self).write(values)
        elif self.section == 'translation':
            # change in translation line
            if 'client_order_ref' in values or 'translation_amount' in values:
                final_name = ('%s %s' % (self.internal_ref or '',
                                         values.get('client_order_ref',self.client_order_ref or ''),
                                        )).strip().replace('  ',' ')
                translation_line_id = self.get_line_by_product_id(self.delegated_type_id.translation_product_id)
                if translation_line_id:
                    line_data = SaleOrderLine.browse(translation_line_id)
                    line_data.name = final_name + _(' - Translation Costs')
                    line_data.price_unit = values.get('translation_amount',self.translation_amount or 0.0)
                else:
                    line_data = self.get_order_line_from_product_managed(self.delegated_type_id.translation_product_id,1,final_name)
                    line_data['name'] += _(' - Translation Costs')
                    line_data['price_unit'] = values.get('translation_amount',self.translation_amount or 0.0)
                    line_data['sequence'] = 1
                    SaleOrderLine.create(line_data)
            # change in admin line
            if 'client_order_ref' in values or 'translation_amount' in values or \
               'cci_fee' in values:
                final_fee = values.get('cci_fee',self.cci_fee or 0)
                final_amount = values.get('translation_amount',self.translation_amount or 0.0)
                final_fee_amount = round(final_fee * final_amount / 100, 2)
                final_name = ('%s %s' % (self.internal_ref or '',
                                         values.get('client_order_ref',self.client_order_ref or ''),
                                        )).strip().replace('  ',' ')
                admin_line_id = self.get_line_by_product_id(self.delegated_type_id.administrative_product_id)
                if final_fee_amount <= 0.001:
                    if admin_line_id > 0:
                        # insert into values the deleting of the copies line
                        if 'order_line' in values:
                            values['order_line'] = values['order_line'].append([2,[admin_line_id,]])
                        else:
                            values['order_line'] = ([2,[admin_line_id,]],)
                else:
                    if admin_line_id:
                        line_data = SaleOrderLine.browse(admin_line_id)
                        line_data.price_unit = final_fee_amount
                        line_data.name = final_name + _(' - Administratives Costs')
                    else:
                        line_data = self.get_order_line_from_product_managed(self.delegated_type_id.administrative_product_id,1,final_name)
                        line_data['name'] += _(' - Administrative Costs')
                        line_data['price_unit'] = final_fee_amount
                        line_data['sequence'] = 5
                        SaleOrderLine.create(line_data)
            result = super(SaleOrder, self).write(values)
        else: #  self.section == 'embassy' or 'sale_order'
            # nothing special to do
            result = super(SaleOrder, self).write(values)
        return result


