from odoo import fields, models, api

class EstatePropertyType(models.Model):
    _name = "estate.property.type"
    _description = "Real Estate Property Type"
    _order = "sequence, name"
    _sql_constraints = [
        (
            "check_name",
            "UNIQUE(name)",
            "The name must be unique",
        ),
    ]
    
    name = fields.Char("Name", required=True)
    sequence = fields.Integer("Sequence", default=10)
    property_ids = fields.One2many(comodel_name="estate.property",
                                   inverse_name="property_type_id",
                                   string="Properties")
    offer_ids = fields.One2many("estate.property.offer",
                                inverse_name="property_type_id",
                                string="Offers")
    offer_count = fields.Integer("Offers count", compute="_compute_offer_count")

    @api.depends('offer_ids')
    def _compute_offer_count(self):
        for record in self:
            record.offer_count = len(record.offer_ids)

    def action_view_offers(self):
        self.ensure_one()
        #  Instead of action button, an object button can return an action from a model method
        res = self.env.ref("estate.estate_property_offer_action").read()[0]
        res["domain"] = [("id", "in", self.env['estate.property.offer'].search(
            [('property_type_id', 'in', self.ids)]).ids)]
        # res["target"] = "new"
        return res