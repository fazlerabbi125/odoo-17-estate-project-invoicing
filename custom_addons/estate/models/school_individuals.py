from odoo import models, fields

class Teacher(models.Model):
    _name = 'school.teacher'
    _description = 'School Teacher'
    _inherit = 'person.base'
    # _log_access = False
    # _table = 'teacher'
    # _register = False

    subject = fields.Char(string='Subject', required=True)
    salary = fields.Float(string='Salary', required=True)


class Student(models.Model):
    _name = 'school.student'
    _description = 'School Student'
    _inherit = 'person.base'
    _sql_constraints = [
        ('unique_roll_number', 'UNIQUE(roll_number)', 'The student roll_number must be unique!'),
    ]
    _order = "roll_number desc"

    roll_number = fields.Char(string='Roll Number', required=True)
    grade = fields.Char(string='Grade', required=True)


