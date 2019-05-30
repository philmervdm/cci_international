# -*- coding: utf-8 -*-

from odoo import models, fields, api

class CCICreditLine(models.Model):
    _name = 'cci_international.credit_line'
    _description = """Define two limits between two dates : 
                    one for AWEX intervention by customer, and
                    one global for all customers during this range of dates"""

    name = fields.Char('Name',required=True)
    from_date = fields.Date('From',required=True)
    to_date = fields.Date('To',required=True)
    customer_limit = fields.Float('Customer Credit',digits=(16, 2))
    global_limit = fields.Float('Global Credit',digits=(16, 2))
    
    def get_available_intervention(self,base_amount,partner):
        # the available amount depends on three criteria :
        #  - max 50% of the base_amount
        #  - the total of the interventions for this customer on this credit line can't exceed customer_limit, for each customer
        #  - the total intervention for all customers on this credit line can't exceed global_limit
        SaleOrder = self.env['sale.order']
        global_usage = 0.0
        partner_usage = 0.0
        sorders = SaleOrder.search([('credit_line_id','=',self.id),('awex_intervention','>',0.0)])
        print('sorders')
        print(len(sorders))
        for sale_order in sorders:
            global_usage += sale_order.awex_intervention
            if sale_order.partner_id.id == partner.id:
                partner_usage += sale_order.awex_intervention
        left_global = max(self.global_limit - global_usage,0.0)
        left_partner = max(self.customer_limit - partner_usage,0.0)
        print('Left Global')
        print(left_global)
        print('Left Partner')
        print(left_partner)
        return min(base_amount/2,left_global,left_partner)
        
