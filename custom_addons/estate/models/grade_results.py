from odoo import models, fields

class SchoolResults(models.Model):
    _name = 'school.results'
    _description = 'School Results'
    _inherits = {'school.student': 'student_id'}
    _rec_name = "title"

    title = fields.Char(required=True)
    student_id = fields.Many2one('school.student', string='Student',
                                 required=True, ondelete='cascade')