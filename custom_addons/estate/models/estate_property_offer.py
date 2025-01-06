from odoo import fields, models, api
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Real Estate Property Offer"
    _order = "price desc, id"
    _sql_constraints = [
        (
            "check_price",
            "CHECK(price > 0)",
            "The price must be strictly positive",
        ),
    ]
    _rec_name = "display_name"

    price = fields.Monetary("Price", required=True)
    validity = fields.Integer(string="Validity (days)", default=7)

    state = fields.Selection(
        selection=[
            ("accepted", "Accepted"),
            ("refused", "Refused"),
        ],
        string="Status",
        readonly=True,
        copy=False,
    )
    partner_id = fields.Many2one("res.partner", string="Partner", required=True,
                                 domain=[('customer_rank', '>', 0)])
    property_id = fields.Many2one("estate.property", string="Property",
                                  domain=[('state', '=', 'approve')],
                                  required=True, ondelete='cascade')
    currency_id = fields.Many2one(
        "res.currency",
        related="property_id.currency_id",
        string="Currency",
    )

    # For state button
    property_type_id = fields.Many2one(
        comodel_name="estate.property.type",
        string="Property Type",
        related="property_id.property_type_id",
        store=True,
        ondelete='set null'
    )

    date_deadline = fields.Date(
        string="Deadline",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
    )

    @api.depends("create_date", "validity")
    def _compute_date_deadline(self):
        for offer in self:
            date = offer.create_date.date() if offer.create_date else fields.Date.today()
            offer.date_deadline = date + relativedelta(days=offer.validity)

    @api.onchange("date_deadline")
    def _inverse_date_deadline(self):
        for offer in self:
            date = (
                offer.create_date.date() if offer.create_date else fields.Date.today()
            )
            offer.validity = (offer.date_deadline - date).days

    @api.depends('partner_id', 'property_id')
    def _compute_display_name(self):
        assigned_rec = self.filtered(lambda x: x.partner_id and x.property_id)
        unassigned_rec = self - assigned_rec
        for offer in assigned_rec:
            offer.display_name = f"{offer.partner_id.name} - {offer.property_id.name}"

        super(EstatePropertyOffer, unassigned_rec)._compute_display_name()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("property_id") and vals.get("price"):
                prop = self.env["estate.property"].browse(vals["property_id"])
                usable_offers = prop.offer_ids.filtered(lambda x: x.state != 'refused')
                if usable_offers:
                    max_offer = max(usable_offers.mapped("price"))
                    if (
                            float_compare(vals["price"], max_offer, precision_rounding=0.01)
                            <= 0
                    ):
                        raise UserError("The offer must higher than %.2f" % max_offer)
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            prop_id = vals.get("property_id", rec.property_id.id)
            if prop_id and vals.get("price"):
                prop = self.env["estate.property"].browse(prop_id)
                usable_offers = prop.offer_ids.filtered(lambda x: x.state != 'refused')
                if usable_offers:
                    max_offer = max(usable_offers.mapped("price"))
                    if (
                            float_compare(vals["price"], max_offer, precision_rounding=0.01)
                            <= 0
                    ):
                        raise UserError("The offer must higher than %.2f" % max_offer)
        return super().write(vals)

    def unlink(self):
        for offer in self:
            if offer.state == 'accepted':
                raise UserError("You cannot delete an accepted offer")
            prop = self.env["estate.property"].browse(offer.property_id.id)
            if not prop.offer_ids.filtered(lambda x: x.id != offer.id):
                prop.state = 'approve'
        return super().unlink()

    def action_accept(self):
        self.ensure_one()
        if self.state == "accepted":
            raise UserError("Offer has already been accepted")
        self.property_id._handle_offer_acceptance(self)
        return self.write({"state": "accepted"})

    def action_refuse(self):
        self.ensure_one()
        if self.state == "refused":
            raise UserError("Offer has already been refused")
        self.property_id._handle_offer_refusal(self)
        return self.write({"state": "refused"})

