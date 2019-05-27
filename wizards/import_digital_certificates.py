# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
from lxml import objectify        

class ImportDigitalCertificatesWizard(models.TransientModel):

    _name = 'import.digital.certificates.wizard'

    delegated_type_id = fields.Many2one(
        comodel_name='cci_international.delegated_type',
        string='Certificate Type',
        required=True,
        domain=[('section', '=', 'certificate'),('digital','=',True)],
        help='Type of Certificate to Import'
    )

    input_file = fields.Binary(
        string='XML File',
        required=True,
        help='The XML file from Digichambers platform',
    )
    
    new_ids = [] # list of the ID of created certificates
    
    @api.multi
    def import_digital_certificates(self):
        self.new_ids = []
        inputdata = base64.decodestring(self.input_file)
        EEC_COUNTRIES = {
             'EUROPEAN UNION(SPAIN)':'ES',
             'EUROPEAN UNION(BELGIUM)':'BE',
             'EUROPEAN UNION(GERMANY)':'DE',
             'EUROPEAN UNION(FRANCE)':'FR',
             'EUROPEAN UNION(PORTUGAL)':'PT',
             'EUROPEAN UNION(GREECE)':'GR',
             'EUROPEAN UNION(POLAND)':'PL',
             'EUROPEAN UNION(ITALY)':'IT',
             'EUROPEAN UNION(CZECH REPUBLIC)':'CZ',
             'EUROPEAN UNION(NETHERLANDS)':'NL',
             'EUROPEAN UNION(FINLAND)':'FI',
             'EUROPEAN UNION(UNITED KINGDOM)':'GB',
             'EUROPEAN UNION(ESTONIA)':'EE',
             'EUROPEAN UNION(HUNGARY)':'HU',
             'EUROPEAN UNION(IRELAND)':'IE',
             'EUROPEAN UNION(LATVIA)':'LV',
             'EUROPEAN UNION(DENMARK)':'DK',
             'EUROPEAN UNION(CYPRUS)':'CY',
             'EUROPEAN UNION(AUSTRIA)':'AT',
             'EUROPEAN UNION(BULGARIA)':'BG',
             'EUROPEAN UNION(CROATIA)':'HR',
             'EUROPEAN UNION(SWEDEN)':'SE',
             'EUROPEAN UNION(SLOVENIA)':'SI',
             'EUROPEAN UNION(SLOVAKIA)':'SK',
             'EUROPEAN UNION(ROMANIA)':'RO',
             'EUROPEAN UNION(LITUANIA)':'LT',
             'EUROPEAN UNION(LUXEMBOURG)':'LU',
             'EUROPEAN UNION(MALTA)':'MT',
        }

        # store the results
        rejected = 0
        imported = 0
        attached_visas = 0
        errors = []
        created_codes = []

        # objects necessary for the import
        SaleOrder = self.env['sale.order']
        ResPartner = self.env['res.partner']
        ResCountry = self.env['res.country']
        AccountIntrastatCode = self.env['account.intrastat.code']
        CCIZip = self.env['cci.zip']

        root = objectify.fromstring(inputdata.replace(b' xmlns="http://schemas.fccib.be/doc/CO_10"',b''))
        # check if there is CO subElements
        if not hasattr(root, 'CO'): ### the file is empty OR this is not a certificates'file
            raise UserError(_('The given file is either empty or NOT an Certificate XML file.\nPlease check your parameters.'))
            
        # try import each certificate
        for cert in root.CO:
            internal_id = int(cert.ID)
            if str(cert.ChamberNumber) == '87':
                # searching partner by VAT Number
                custVAT = str(cert.CompanyVAT).replace(' ','').replace('.','')
                if (len(custVAT) > 2) and (custVAT[0:2] in ('SE','LU')):
                    pass
                else:
                    if len(custVAT)==9:
                        custVAT = 'BE0' + custVAT
                    elif len(custVAT)==10:
                        custVAT = 'BE' + custVAT
                partners = ResPartner.search([('vat','=',custVAT),('active','=',True),('is_company','=',True)])
                if len(partners) == 1:
                    partner = partners[0]
                    #obj_partner.read(cr,uid,partner_id,['name','membership_state','certificate_prefix'])
                    # extract others mandatory fields
                    accepteddatetime = str(cert.AcceptedDateTime)
                    cert_date = accepteddatetime[6:10]+'-'+accepteddatetime[3:5]+'-'+accepteddatetime[0:2]
                    #
                    content = cert.XML.CORequest.COForm.COFormContent
                    #
                    destination = str(content.Customs.DestinationCountry)
                    
                    if destination in EEC_COUNTRIES:
                        countries = ResCountry.search([('code','=',EEC_COUNTRIES[destination])])
                    else:
                        destination_code = destination[destination.rfind('(')+1:destination.rfind(')')]
                        countries = ResCountry.search([('code','=',destination_code)])
                    if len(countries) == 1:
                        destination_country = countries[0]
                        destination_id = destination_country.id
                        #
                        digital_number = str(cert.CONumber).replace(' ','')[1:]
                        certificates = SaleOrder.search([('section','=','certificate'),('digital_ref','=',digital_number)])
                        if len(certificates) > 0:
                            rejected += 1
                            errors.append( 'InternalID : %s - Already used digital number : %s' % (str(internal_id),digital_number) )
                        else:
                            todo_field = ''
                            goods_desc = content.Shipment.ShipmentDescription.pyval
                            goods_value = float(content.Customs.ValueInEuro)
                            if goods_value < 0.001:
                                goods_value = 0.01
                                todo_field += 'ValeurBiens:0 -'
                            goods_desc = goods_desc.replace('\n',' - ').replace('\r',' - ')
                            #
                            lRejected = False
                            origin_ids = []
                            for country_element in content.Origins.CountryOfOriginCollection.Country:
                                country_name = str(country_element)
                                if country_name == 'EUROPEAN UNION':
                                    country_code = 'EEC'
                                else:
                                    if country_name in EEC_COUNTRIES:
                                        country_code = EEC_COUNTRIES[country_name]
                                    else:
                                        country_code = country_name[country_name.rfind('(')+1:country_name.rfind(')')]
                                countries = ResCountry.search([('code','=',country_code)])
                                if len(countries) == 1:
                                    origin_ids.append(countries[0].id)
                                else:
                                    lRejected = True
                                    rejected += 1
                                    errors.append( 'InternalID : %s - Unknown Origin : %s' % (str(internal_id),country_name) )
                            if len(origin_ids) == 0 and not lRejected:
                                rejected += 1
                                errors.append( 'InternalID : %s - No Origin' % (str(internal_id)) )
                                lRejected = True
                            if not lRejected:
                                custom_code_ids = []
                                for code_element in content.Customs.CustomCodeCollection.CustomCode:
                                    #code = str(code_element).rjust(8,'0')
                                    custom_codes = AccountIntrastatCode.search([('code','=',code_element)])
                                    if len(custom_codes) == 0:
                                        new_code = AccountIntrastatCode.create({'name':code,
                                                                                'description':'NR',
                                                                                'type':'commodity'})
                                        created_codes.append(code_element)
                                        custom_codes = [new_code,]
                                    custom_code_ids.append(custom_codes[0].id)
                                if len(custom_code_ids)==0:
                                    rejected += 1
                                    errors.append( 'InternalID : %s - No Custom Codes' % (str(internal_id)) )
                                    lRejected = True
                                customerRef = ''
                                if not lRejected:
                                    # others non mandatory fields
                                    copies = int(cert.Duplicates)
                                    customerRef = str(cert.CustomerRef) # to unicode
                                    if customerRef:
                                        while '  ' in customerRef:
                                            customerRef = customerRef.replace('  ',' ')
                                    if hasattr(content,'Applicant'):
                                        asker_name = content.Applicant.AddressName
                                        asker_street = content.Applicant.AddressStreetAndNumber
                                        zip_code = ''
                                        city_name = ''
                                        if hasattr(content.Applicant,'AddressPostalCode'):
                                            if str(type(content.Applicant.AddressPostalCode)) == "<type 'lxml.objectify.IntElement'>":
                                                zip_code = str(int(content.Applicant.AddressPostalCode))
                                            else:
                                                zip_code = str(content.Applicant.AddressPostalCode)
                                        if hasattr(content.Applicant,'AddressCity'):
                                            if str(type(content.Applicant.AddressCity)) == "<type 'lxml.objectify.IntElement'>":
                                                city_name = str(int(content.Applicant.AddressCity))
                                            else:
                                                if type(content.Applicant.AddressCity)== "<type 'lxml.objectify.StringElement'>":
                                                    city_name = str(content.Applicant.AddressCity)
                                                else:
                                                    city_name = str(content.Applicant.AddressCity) ## to unicode
                                        asker_city = zip_code + ' ' + city_name
                                        if zip_code[0:3] in ('BE ','BE-'):
                                            zip_code = zip_code[3:]
                                        elif zip_code[0:2] in ('B-','B ','BE'):
                                            zip_code = zip_code[2:]
                                        elif zip_code[0:1] == 'B':
                                            zip_code = zip_code[1:]
                                        zip_id = 0
                                    else:
                                        asker_name = content.Consignor.AddressName
                                        asker_street = content.Consignor.AddressStreetAndNumber
                                        zip_code = ''
                                        city_name = ''
                                        if hasattr(content.Consignor,'AddressPostalCode'):
                                            if str(type(content.Consignor.AddressPostalCode)) == "<type 'lxml.objectify.IntElement'>":
                                                zip_code = str(int(content.Consignor.AddressPostalCode))
                                            else:
                                                zip_code = str(content.Consignor.AddressPostalCode)
                                        if hasattr(content.Consignor,'AddressCity'):
                                            if str(type(content.Consignor.AddressCity)) == "<type 'lxml.objectify.IntElement'>":
                                                city_name = str(int(content.Consignor.AddressCity))
                                            else:
                                                if type(content.Consignor.AddressCity)== "<type 'lxml.objectify.StringElement'>":
                                                    city_name = str(content.Consignor.AddressCity)
                                                else:
                                                    city_name = str(content.Consignor.AddressCity) # to unicode
                                        asker_city = zip_code + ' ' + city_name
                                        if zip_code[0:3] in ('BE ','BE-'):
                                            zip_code = zip_code[3:]
                                        elif zip_code[0:2] in ('B-','B ','BE'):
                                            zip_code = zip_code[2:]
                                        elif zip_code[0:1] == 'B':
                                            zip_code = zip_code[1:]
                                        zip_id = 0
                                    # try to find the id of the zip code
                                    # if not found, mark it in 'TO-DO' field
                                    zips = CCIZip.search([('name','=',zip_code)])
                                    if len(zips) >= 1:
                                        for czip in zips:
                                            if czip.city.upper() == city_name.upper():
                                                zip_id = czip.id
                                            else:
                                                if czip.old_name and ( city_name.upper() in czip.old_name ):
                                                    zip_id = czip.id
                                        if not zip_id:
                                            todo_field += 'CodePostal:'+zip_code+' '+city_name + ' -'
                                    else:
                                        todo_field += 'CodePostal:'+zip_code+' '+city_name + ' -'
                                    # try to add it to the certificates table
                                    certificate_data = {}
                                    certificate_data['section'] = 'certificate'
                                    certificate_data['delegated_type_id'] = self.delegated_type_id.id
                                    certificate_data['date_order'] = cert_date
                                    certificate_data['partner_id'] = partner.id
                                    certificate_data['asker_name'] = asker_name
                                    certificate_data['asker_street'] = asker_street
                                    if zip_id > 0:
                                        certificate_data['asker_city'] = zip_id
                                    certificate_data['sender_name'] = content.Consignor.AddressName
                                    certificate_data['state'] = 'draft'
                                    certificate_data['goods_desc'] = goods_desc
                                    certificate_data['goods_value'] = goods_value
                                    certificate_data['destination_id'] = destination_id
                                    certificate_data['copies'] = copies
                                    certificate_data['originals'] = 1
                                    certificate_data['custom_ids'] = [(6,0,custom_code_ids)]
                                    certificate_data['origin_ids'] = [(6,0,origin_ids)]
                                    certificate_data['digital_ref'] = digital_number
                                    certificate_data['client_order_ref'] = customerRef
                                    if todo_field:
                                        certificate_data['todo'] = todo_field[0:-2]
                                    # try to find attachments
                                    visas = []
                                    if False: ###hasattr(cert.ReviewedAttachments,'Attachment'):
                                        type_code = ''
                                        origs = 0
                                        copies = 0
                                        type_id = False
                                        for attach in cert.ReviewedAttachments.Attachment:
                                            # 2014-08-05 Philmer create associated legalization rather than todo field
                                            # let the todo field in place some days for validation purposes
                                            todo_field += attach.Type + ' (' + str(attach.Number) + ') -'
                                            type_ids = obj_type.search(cr,uid,[('digital_ref','=',attach.Type)])
                                            if type_ids and len(type_ids) == 1:
                                                type_id = type_ids[0]
                                                found_type = obj_type.read(cr,uid,type_id,['code'])
                                                type_code = found_type['code']
                                                origs = int(attach.Number)
                                                if origs <= 0:
                                                    origs = 1
                                                leg_data = {}
                                                leg_data['section'] = 'visa'
                                                leg_data['type_id'] = type_id
                                                leg_data['date_order'] = cert_date
                                                leg_data['order_partner_id'] = partner_id
                                                leg_data['asker_name'] = asker_name
                                                leg_data['sender_name'] = content.Consignor.AddressName
                                                leg_data['state'] = 'draft'
                                                leg_data['goods_value'] = goods_value
                                                leg_data['quantity_copies'] = copies
                                                leg_data['quantity_original'] = origs
                                                leg_data['digital_number'] = 'L' + digital_number
                                                leg_data['client_order_ref'] = type_code+'/'+customerRef
                                                leg_data['goods'] = goods_desc
                                                leg_data['destination_id'] = destination_id
                                                leg_data['member_price'] = ( found_partner['membership_state'] in ['free','invoiced','paid'] )
                                                visas.append(leg_data)
                                    new_certificate = SaleOrder.create(certificate_data)
                                    self.new_ids.append(new_certificate.id)
                                    # next, no more necessary, because the addition of the prefix occurs in all cases, not only in case of importing
                                    #if new_id and found_partner['certificate_prefix']:
                                    #    cert = obj_certificate.read(cr,uid,new_id,['text_on_invoice'])
                                    #    obj_certificate.write(cr,uid,[new_id,],{'text_on_invoice':found_partner['certificate_prefix'].strip()+' '+(cert['text_on_invoice'] or '')})
                                    for visa in visas:
                                        visa['certificate_id'] = int(new_id)
                                        obj_leg.create(cr,uid,visa)
                                        attached_visas += 1
                                    # after the create, we add the customerref to the text on invoice
                                    #if customerRef:
                                    #    newly_added = obj_certificate.read(cr,uid,[new_id],['id','text_on_invoice'])[0]
                                    #    obj_certificate.write(cr,uid,[new_id],{'text_on_invoice': customerRef + ' ' + (newly_added['text_on_invoice'] or '')})
                                    # TODO V 7.0 : when create if 'text_on_invoice' not empty, completing with number before already existing text
                                    # so we don't need to work on two steps, in this wizard but also manually
                                    imported += 1
                    else:
                        rejected += 1
                        errors.append( 'InternalID : %s - Unknown Destination : \'%s\'' % (str(internal_id),destination) )
                else:
                    rejected += 1
                    errors.append( 'InternalID : %s - Unknown VAT Number : \'%s\'' % (str(internal_id),custVAT) )
            else:
                rejected += 1
                errors.append( 'InternalID : %s - Wrong ChamberNumber : \'%s\'' % (str(internal_id),str(cert.ChamberNumber)) )
        if len(created_codes)>0:
            errors.append('-')
            errors.append('Created Customs Code(s) : ' + ','.join(created_codes) )
        # give the result to the user
        print('Number of imported digital certificates : %s\nAttached Visas : %s\nNumber of rejected certificates : %s\nReasons :\n%s' % (str(imported),str(attached_visas),str(rejected),'\n'.join(errors)))
        return {
            'name': 'Imported Certificates',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('cci_international.view_certificate_tree').id, 'tree'),
                (self.env.ref('cci_international.view_cci_certificate_form').id, 'form'),
            ],
            'domain': [('id', 'in', self.new_ids)],
        }
