from odoo import models, fields

class PersonBase(models.AbstractModel):
    _name = "person.base"
    _description = "Person Base"
    _sql_constraints = [
        ('check_positive_age', 'CHECK(age > 0)', 'Age must be a positive number!'),
    ]
    name = fields.Char(string='Name', required=True)
    age = fields.Integer(string='Age', required=True)
    gender = fields.Selection(selection=[
        ('male', 'Male'),
        ('female', 'Female'),
        ('others', 'Others'),
    ], required=True)
    address = fields.Text(string='Address')
