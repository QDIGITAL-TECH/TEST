from odoo import http



class Academy(http.Controller):
    @http.route('/academy/academy/', auth='public', website=True)
    def index(self, **kw):
        Teachers = http.request.env['academy.teachers']
        return http.request.render('academy.index', {
            'teachers': Teachers.search([])
        })
    
    @http.route('/academy/<int:id>', auth='public', website=True)
    def teacher(self, id):
        return'<h1>{} ({})</h1>'.format(id, type(id).__name__)

    #@http.route('/academy/<model("academy.teachers"):teacher>/', auth='public', website=True)
    #def teacher(self, teacher):