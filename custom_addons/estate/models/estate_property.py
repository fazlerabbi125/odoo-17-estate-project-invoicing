from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError
from odoo.addons.helpers.validators import check_duplicate_rec
from odoo.tools import float_compare, float_is_zero

class EstateProperty(models.Model):
    _name = 'estate.property'
    _inherit = ['mail.thread', 'mail.activity.mixin',]
    _description = 'Real Estate Property'
    _order = 'id desc'

    name = fields.Char(string="Title", required=True, tracking=True)
    postcode = fields.Char("Postcode")
    description = fields.Text(string="Property description", copy=False)
    date_availability = fields.Date(string="Available from", required=True,
                                    tracking=True,
                                    default=fields.Date.today)
    expected_price = fields.Monetary(string="Expected Price", required=True,
                                     tracking=True,
                                     currency_field="currency_id")
    selling_price = fields.Monetary("Selling Price", copy=False,
                                    tracking=True,
                                    currency_field="currency_id")
    bedrooms = fields.Integer(string="Bedrooms", default=2)
    living_area = fields.Integer(string="Living Area (sqm)")
    facades = fields.Integer(string="Facades")
    garage = fields.Boolean(string="Garage")
    garden = fields.Boolean(string="Garden")
    garden_area = fields.Integer(string="Garden Area (sqm)")
    garden_orientation = fields.Selection(
        selection=[
            ("N", "North"),
            ("S", "South"),
            ("E", "East"),
            ("W", "West"),
        ],
        string="Garden Orientation",
    )
    image = fields.Image(string="Property Image")
    # accepted_offer = fields.Integer(string="Accepted Offer", readonly=True, copy=False)

    # Special
    state = fields.Selection(
        selection=[
            ("draft", "Draft"),
            ('confirm', 'Waiting for Approval'),
            ('refuse', 'Refused'),
            ('approve', 'Available'),
            ("offer_accepted", "Offer Accepted"),
            ("sold", "Sold"),
            ('cancel', 'Cancelled')
        ],
        string="Status",
        required=True,
        copy=False,
        default="draft",
        readonly=True,
        tracking=True,
    )
    active = fields.Boolean("Active", default=True,
                            # groups="account.group_account_manager"
                            )

    # built-in models
    currency_id = fields.Many2one(comodel_name='res.currency',
                                  string='Currency', tracking=True,
                                  help="Forces all journal items in this account to have a specific currency (i.e. bank journals). If no currency is set, entries can use any currency.",
                                  default=lambda self: self.env.company.currency_id)

    # Relational with built-in models
    user_id = fields.Many2one(
        "res.users", string="Salesman", default=lambda self: self.env.user
    )
    buyer_id = fields.Many2one("res.partner", string="Buyer", copy=False,
                               tracking=True,
                               domain=[('customer_rank', '>', 0)], readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, readonly=False,
                                 default=lambda self: self.env.company)
    approved_by = fields.Many2one('res.users', string='Approved By',
                                  tracking=True,
                                  domain=lambda self: self._get_approver_domain())

    # Relational with custom models
    property_type_id = fields.Many2one("estate.property.type",
                                       string="Property Type",
                                       tracking=True,
                                       ondelete='set null')
    tag_ids = fields.Many2many(comodel_name="estate.property.tag", string="Tags")
    offer_ids = fields.One2many(comodel_name="estate.property.offer", inverse_name="property_id", string="Offers")

    # Computed
    total_area = fields.Integer(
        "Total Area (sqm)",
        compute="_compute_total_area",
        help="Total area computed by summing the living area and the garden area",
        store=True,
    )
    best_price = fields.Monetary("Best Offer", compute="_compute_best_price", help="Best offer received")

    @api.depends("living_area", "garden_area")
    def _compute_total_area(self):
        for prop in self:
            prop.total_area = prop.living_area + prop.garden_area

    @api.onchange('garden')
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = 'N'
        else:
            self.update({
                'garden_area': 0,
                'garden_orientation': ''
            })

    @api.model
    def _get_approver_domain(self):
        return [("groups_id", "in", [self.env.ref('base.group_erp_manager').id,
                                     self.env.ref('estate.group_estate_manager').id,
                                     ])]
    # @api.onchange("buyer_id")
    # def _onchange_partner_id(self):
    #     self.name = "Document for %s" % (self.buyer_id.name)
    #     # if not self.description:
    #     #     return {'warning':{'title': "Warning",
    #     #                        'message': 'You should add a description with buyer'}}
    #     self.description = "Default description for %s" % (self.buyer_id.name)

    def _remove_offers(self):
        for prop in self:
            if prop.state in ('sold', 'offer_accepted'):
                raise UserError("The property has an accepted offer")
            prop.offer_ids.unlink()

    def action_cancel(self):
        self.ensure_one()
        self._remove_offers()
        return self.write({"state": "cancel"})

    def action_draft(self):
        self.ensure_one()
        self._remove_offers()
        return self.write({"state": "draft",
                           "approved_by": False,
                           })

    def action_confirm(self):
        self.ensure_one()
        return self.write({"state": "confirm"})

    def action_refuse(self):
        if not self.env.user.has_group('estate.group_estate_manager'):
            raise UserError("Only estate managers can rejected properties")
        return self.write({"state": "refuse"})

    def action_approve(self):
        if not self.env.user.has_group('estate.group_estate_manager'):
            raise UserError("Only estate managers can approve properties")
        return self.write({"state": "approve",
                           "approved_by": self.env.user.id
                           })

    def action_sold(self):
        if self.filtered(lambda x: x.state in ('cancel', 'refused')):
            raise UserError("Canceled/refused properties cannot be sold")
        return self.write({"state": "sold"})

    def _check_accepted_offer(self, offer):
        accepted_offer = self.offer_ids.filtered(lambda x: x.state == 'accepted')
        if len(accepted_offer) > 1:
            raise UserError("An estate cannot have more than 1 accepted offer")
        return accepted_offer and accepted_offer.id == offer

    def _handle_offer_acceptance(self, offer):
        self.ensure_one()
        if self.state in ("offer_accepted", "sold"):
            raise UserError("The given estate has already accepted an offer")
        if self._check_accepted_offer(offer.id):
            raise UserError("The given offer has already been accepted")
        remaining_offers = self.offer_ids.filtered(lambda x: x.id != offer.id)
        self.write(
            {
                "state": "offer_accepted",
                "selling_price": offer.price,
                "buyer_id": offer.partner_id.id,
            }
        )
        remaining_offers.write({"state": "refused"})

    def _handle_offer_refusal(self, offer):
        self.ensure_one()
        if self._check_accepted_offer(offer.id):
            vals_to_update = {
                "selling_price": 0,
                "buyer_id": False,
                "state": "approve",
            }
            remaining_offers = self.offer_ids.filtered(lambda x: x.id != offer.id)
            self.write(vals_to_update)
            remaining_offers.write({"state": False})

    @api.constrains("active", "state")
    def _check_active_state(self):
        if self.filtered(lambda x: not x.active and x.state in
                                   ('offer_accepted', 'sold')):
            raise ValidationError("Properties with accepted offers cannot be archived.")

    @api.constrains("expected_price", "selling_price")
    def _check_price_difference(self):
        for prop in self:
            if (
                    not float_is_zero(prop.selling_price, precision_rounding=0.01)
                    and float_compare(
                prop.selling_price,
                prop.expected_price * 90.0 / 100,
                precision_rounding=0.01,
            )
                    < 0
            ):
                raise ValidationError(
                    "The selling price must be at least 90% of the expected price "
                    + " You must reduce expected price if you want to accept this offer."
                )

    @api.constrains('name')
    def _check_unique_name(self):
        for rec in self:
            # found = self.search([('id', '!=', rec.id), ('name', '=ilike', rec.name)], limit=5, order="id desc")
            check_duplicate_rec(rec, envObj=self, condList=[('name', '=ilike', rec.name)], msg="Title must be unique regardless of case")

    @api.ondelete(at_uninstall=False) #at uninstall determines if method triggers at on uninstall
    def _unlink_estate_if_inactive(self):
        if any(rec.state == 'sold' for rec in self):
            raise UserError("Cannot delete sold estate properties")

    @api.depends("offer_ids.price")
    def _compute_best_price(self):
        for prop in self:
            usable_offers = prop.offer_ids.filtered(lambda x: x.state != 'refused')
            prop.best_price = max(usable_offers.mapped("price")) if usable_offers else 0

    def unlink(self):
        user = self.env.user
        if not (user.has_group('estate.group_estate_manager') or self.env.is_admin()) and self.filtered(lambda x: x.state not in ("draft", "cancel")):
            raise UserError("Only new and canceled properties can be deleted by agent")

        return super().unlink()