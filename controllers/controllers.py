# -*- coding: utf-8 -*-
from odoo import http

# class ./odoo-dev/odoo/addons-custom/cciInternational(http.Controller):
#     @http.route('/./odoo-dev/odoo/addons-custom/cci_international/./odoo-dev/odoo/addons-custom/cci_international/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/./odoo-dev/odoo/addons-custom/cci_international/./odoo-dev/odoo/addons-custom/cci_international/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('./odoo-dev/odoo/addons-custom/cci_international.listing', {
#             'root': '/./odoo-dev/odoo/addons-custom/cci_international/./odoo-dev/odoo/addons-custom/cci_international',
#             'objects': http.request.env['./odoo-dev/odoo/addons-custom/cci_international../odoo-dev/odoo/addons-custom/cci_international'].search([]),
#         })

#     @http.route('/./odoo-dev/odoo/addons-custom/cci_international/./odoo-dev/odoo/addons-custom/cci_international/objects/<model("./odoo-dev/odoo/addons-custom/cci_international../odoo-dev/odoo/addons-custom/cci_international"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('./odoo-dev/odoo/addons-custom/cci_international.object', {
#             'object': obj
#         })