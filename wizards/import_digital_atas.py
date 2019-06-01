# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
from lxml import objectify        

class ImportDigitalAtasWizard(models.TransientModel):

    _name = 'import.digital.atas.wizard'

    delegated_type_id = fields.Many2one(
        comodel_name='cci_international.delegated_type',
        string='ATA Carnet Type',
        required=True,
        domain=[('section', '=', 'ata_carnet'),('digital','=',True)],
        help='Type of eATA to Import'
    )
    input_file = fields.Binary(
        string='XML File',
        required=True,
        help='The XML file from eATA platform',
    )
    state = fields.Selection([('step1','try_import'),('step2','show_errors')],default='step1')
    text_errors = fields.Text(string='Errors')
    rejected = fields.Integer(string='Rejected eATAs')
    imported_atas = fields.Integer(string='Imported eATAs')
    new_ids = [] # list of the ID of created ATA Carnets
    
    @api.multi
    def import_digital_atas(self):
        self.new_ids = []
        inputdata = base64.decodestring(self.input_file)
        inputdata = inputdata.decode('utf-8') # 2015-03-04 : no more utf-16 but utf-8 as at the beginning

        # store the results
        self.rejected = 0
        self.imported_eatas = 0
        self.text_errors = ''
        errors = []
        created_codes = []

        # objects necessary for the import
        SaleOrder = self.env['sale.order']
        DelegatedType = self.env['cci_international.delegated_type']
        ResPartner = self.env['res.partner']
        ResCountryGroup = self.env['res.country.group']
        #CCIZip = self.env['cci.zip']

        root = objectify.fromstring(inputdata)
        # check if there is CARNET subElements
        if not hasattr(root, 'CARNET'): ### the file is empty OR this is not a certificates'file
            raise UserError(_('The given file is either empty or NOT an eATA XML file.\nPlease check your parameters.'))

        for carnet in root.CARNET:
            internal_id = str(carnet.ID)
            if len(internal_id) > 0 and not (internal_id[-1:] == 'D'):
                if str(carnet.ChamberNumber) == '87':
                    full_customer_number = str(carnet.CustomerNumber)
                    if full_customer_number[0:4] == 'cci_':
                        # searching partner by CustomerNumber
                        partners = ResPartner.search([('id','=',int(full_customer_number[4:])),('active','=',True)])
                        if len(partners) == 1:
                            partner = partners[0]
                            existing_atas = SaleOrder.search([('digital_ref','=',internal_id),('section','=','ata_carnet')])
                             # the search on digital_number is not enough because we have a serie of ATA Carnet without digital_number, so search on name also
                            if not existing_atas:
                                existing_atas = SaleOrder.search([('internal_ref','=',carnet.CarnetNumber or ''),('section','=','ata_carnet')]) # so we search also on 'name'
                                if not existing_atas:
                                    # extraction of countries
                                    #country_ids = []
                                    #if hasattr(carnet.DestinationList,'Destination'):
                                    #    for destination in carnet.DestinationList.Destination:
                                    #        isocode3 = str(destination)
                                    #        if len(isocode3) == 3:
                                    #            search_country_ids = obj_country.search(cr,uid,[('isocode3','=',isocode3)])
                                    #            if len(search_country_ids) == 1:
                                    #                country_ids.append(search_country_ids[0])
                                    # search for usage
                                    if str(carnet.IntendedUseList.IntendedUse) == 'Other':
                                        usage_name = str(carnet.IntendedUseList.IntendedUseOther)
                                    else:
                                        usage_name = str(carnet.IntendedUseList.IntendedUse)
                                    customerRef = str(carnet.CustomerRef) # to unicode
                                    if customerRef:
                                        while '  ' in customerRef:
                                            customerRef = customerRef.replace('  ',' ')
                                    ata_data = {}
                                    ata_data['section'] = 'ata_carnet'
                                    ata_data['delegated_type_id'] = self.delegated_type_id.id
                                    ata_data['internal_ref'] = str(carnet.CarnetNumber or b'').replace(' ','')
                                    ata_data['date_order'] = str(carnet.AcceptedDateTime)[6:10]+"-"+str(carnet.AcceptedDateTime)[3:5]+"-"+str(carnet.AcceptedDateTime)[0:2]
                                    ata_data['ata_validity_date'] = str(carnet.ExpiryDateTime)[6:10]+'-'+str(carnet.ExpiryDateTime)[3:5]+'-'+str(carnet.ExpiryDateTime)[0:2]
                                    ata_data['partner_id'] = partner.id
                                    ata_data['asker_name'] = str(carnet.Holder.Applicant)
                                    ata_data['asker_street'] = ''
                                    ata_data['asker_city'] = ''
                                    ata_data['sender_name'] = ''
                                    ata_data['sender_street'] = ''
                                    ata_data['sender_city'] = ''
                                    ata_data['state'] = 'draft'
                                    ata_data['goods_desc'] = ''
                                    ata_data['goods_value'] = float(str(carnet.TotalValue).replace(',','.'))
                                    ata_data['copies'] = 0
                                    ata_data['originals'] = 1
                                    ata_data['digital_ref'] = internal_id
                                    ata_data['client_order_ref'] = customerRef
                                    ata_data['ata_usage'] = usage_name
                                    tous_les_pays = ResCountryGroup.search([('name','=','Tous les Pays')])
                                    if len(tous_les_pays) == 1:
                                        ata_data['ata_area_id'] = tous_les_pays.id
                                    else:
                                        tous_les_pays = ResCountryGroup.search([()])
                                        ata_data['ata_area_id'] = tous_les_pays[0].id
                                    ata_data['ata_warranty'] = 50.0
                                    if hasattr(carnet.Deposit,'DepositAmount'):
                                        if carnet.Deposit.DepositAmount:
                                            ata_data['warranty'] = 0.0
                                            ata_data['own_risk'] = True
                                            ata_data['internal_comments'] = u'Caution de %.2f euros' % float(str(carnet.Deposit.DepositAmount or '0,0').replace(',','.'))
                                    ata_data['ata_pages_initial'] = int(carnet.TotalNumberOfPages or '0')
                                    ata_data['ata_pages_additional'] = int(carnet.NumberOfExtraPages or '0')
                                    new_ata = SaleOrder.create(ata_data)
                                    self.new_ids.append(new_ata.id)
                                    self.imported_atas += 1
                                else:
                                    self.rejected += 1
                                    errors.append( 'Name : %s - Already used name-number ' % (carnet.CarnetNumber or '--none--') )
                            else:
                                self.rejected += 1
                                errors.append( 'InternalID : %s - Already used digital number ' % internal_id )
                        else:
                            self.rejected += 1
                            errors.append( 'InternalID : %s - Wrong Customer ID : \'%s\'' % (str(internal_id),full_customer_number) )
                    else:
                        self.rejected += 1
                        errors.append( 'InternalID : %s - Unknown Customer Number : \'%s\'' % (str(internal_id),full_customer_number) )
                else:
                    self.rejected += 1
                    errors.append( 'InternalID : %s - Wrong ChamberNumber : \'%s\'' % (str(internal_id),str(carnet.ChamberNumber)) )
            else:
                # duplicata of an existing ATA: nothing to DO
                errors.append( 'InternalID : %s - Duplicata => ignored' % str(internal_id))
        # give the result to the user
        self.state = 'step2'
        if self.rejected > 0:
            self.text_errors = '\n'.join(errors)
        else:
            self.text_errors = 'No ERRORS at ALL !\n\nGreat job !'
        print('\n-----------ERRORS---------------------\n')
        print(self.text_errors)
        return {
            'name': 'Imported eATAs',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('cci_international.view_ata_tree').id, 'tree'),
                (self.env.ref('cci_international.view_form_delegated').id, 'form'),
            ],
            'domain': [('id', 'in', self.new_ids)],
        }

