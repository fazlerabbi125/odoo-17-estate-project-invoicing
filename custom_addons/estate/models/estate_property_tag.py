from random import randint
from odoo import fields, models, api, exceptions

class EstatePropertyTag(models.Model):
    _name = "estate.property.tag"
    _description = "Real Estate Property Tag"
    _order = "name"
    _sql_constraints = [
        (
            "check_name",
            "UNIQUE(name)",
            "The name must be unique",
        ),
    ]

    name = fields.Char("Name", required=True)
    color = fields.Integer("Color index", default=0)

    @api.model
    def name_create(self, name):
        record = self.create({'name': name,
                              'color': randint(0, 11)})
        return record.id, record.display_name

    @api.constrains('color')
    def _check_color(self):
        for rec in self:
            if rec.color < 0 or rec.color > 12:
                raise exceptions.ValidationError("Color has to be a integer between 0 and 12")