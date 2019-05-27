# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
import base64
from lxml import objectify        

class ImportDigitalVisasWizard(models.TransientModel):

    _name = 'import.digital.visas.wizard'

    input_file = fields.Binary(
        string='XML File',
        required=True,
        help='The XML file from Digichambers platform',
    )
    state = fields.Selection([('step1','try_import'),('step2','show_errors')],default='step1')
    text_errors = fields.Text(string='Errors')
    rejected = fields.Integer(string='Rejected Visas')
    imported_visas = fields.Integer(string='Imported Visas')
    new_ids = [] # list of the ID of created certificates
    
    @api.multi
    def import_digital_visas(self):
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
        self.rejected = 0
        self.imported_visas = 0
        self.text_errors = ''
        errors = []
        created_codes = []

        # objects necessary for the import
        SaleOrder = self.env['sale.order']
        DelegatedType = self.env['cci_international.delegated_type']
        ResPartner = self.env['res.partner']
        #ResCountry = self.env['res.country']
        #AccountIntrastatCode = self.env['account.intrastat.code']
        CCIZip = self.env['cci.zip']

        root = objectify.fromstring(inputdata)
        # check if there is VISA subElements
        if not hasattr(root, 'VISA'): ### the file is empty OR this is not a certificates'file
            raise UserError(_('The given file is either empty or NOT an Visa XML file.\nPlease check your parameters.'))
            
        # try import each certificate
        for visa in root.VISA:
            internal_id = int(visa.ID)
            if str(visa.ChamberNumber) == '87':
                # searching partner by VAT Number
                custVAT = str(visa.CompanyVAT).replace(' ','').replace('.','')
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
                    # extract others mandatory fields
                    accepteddatetime = str(visa.AcceptedDateTime)
                    visa_date = accepteddatetime[6:10]+'-'+accepteddatetime[3:5]+'-'+accepteddatetime[0:2]

                    digital_number = str(visa.VisaNumber).replace(' ','')
                    visas = SaleOrder.search([('section','=','visa'),('digital_ref','=',digital_number)])
                    if len(visas) > 0:
                        self.rejected += 1
                        errors.append( 'InternalID : %s - Already used digital number : %s' % (str(internal_id),digital_number) )
                    else:
                        delegated_type_id = False
                        origs = 1
                        copies = 0
                        # copies default to 1 until 2016-10-25 : decision of SH and AP to set it to 0 again
                        # try to find attachments
                        if hasattr(visa.ReviewedAttachments,'Attachment'):
                            for attach in visa.ReviewedAttachments.Attachment:
                                if 'Duplicate' in attach.Type:
                                    copies = int(attach.Number)
                                else:
                                    delegated_types = DelegatedType.search([('digital_code','=',attach.Type)])
                                    if delegated_types and len(delegated_types) == 1:
                                        delegated_type_id = delegated_types[0].id
                                    # demande de Pascale Renson du 7-6-2018 : si number > 1, mettre ce nombre en nombre d'originaux
                                    if hasattr(attach,'Number'):
                                        origs = int(attach.Number)
                        if delegated_type_id:
                            goods_desc = ''
                            goods_value = 0.01
                            customerRef = str(visa.CustomerRef) # to unicode
                            if customerRef:
                                while '  ' in customerRef:
                                    customerRef = customerRef.replace('  ',' ')
                            asker_name = partner.name
                            sender_name = partner.name
                            visa_data = {}
                            visa_data['section'] = 'visa'
                            visa_data['delegated_type_id'] = delegated_type_id
                            visa_data['date_order'] = visa_date
                            visa_data['partner_id'] = partner.id
                            visa_data['asker_name'] = asker_name
                            visa_data['sender_name'] = sender_name
                            visa_data['state'] = 'draft'
                            visa_data['goods_desc'] = goods_desc
                            visa_data['goods_value'] = goods_value
                            visa_data['copies'] = copies
                            visa_data['originals'] = origs
                            visa_data['digital_ref'] = digital_number
                            visa_data['client_order_ref'] = customerRef
                            new_visa = SaleOrder.create(visa_data)
                            self.new_ids.append(new_visa.id)
                            self.imported_visas += 1
                        else:
                            self.rejected += 1
                            errors.append( 'InternalID : %s - Unknown Type of Visa')
                else:
                    self.rejected += 1
                    errors.append( 'InternalID : %s - Unknown VAT Number : \'%s\'' % (str(internal_id),custVAT) )
            else:
                self.rejected += 1
                errors.append( 'InternalID : %s - Wrong ChamberNumber : \'%s\'' % (str(internal_id),str(cert.ChamberNumber)) )
        # give the result to the user
        self.state = 'step2'
        if self.rejected > 0:
            self.text_errors = '\n'.join(errors)
        else:
            self.text_errors = 'No ERRORS at ALL !\n\nGreat job !'
        return {
            'name': 'Imported Visas',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('cci_international.view_visa_tree').id, 'tree'),
                (self.env.ref('cci_international.view_cci_visa_form').id, 'form'),
            ],
            'domain': [('id', 'in', self.new_ids)],
        }

