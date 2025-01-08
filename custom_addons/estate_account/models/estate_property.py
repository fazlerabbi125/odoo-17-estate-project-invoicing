from odoo import fields, models, api, _, Command
from odoo.exceptions import UserError, ValidationError

class EstateProperty(models.Model):
    _inherit = "estate.property"

    @api.model
    def _get_default_journal(self):
        return self.env["account.journal"].search([("type", "=", "sale"),
                                                   ("company_id", "=", self.env.company.id)
                                                   ], limit=1)

    admin_fees = fields.Monetary("Administrative fees", tracking=True)
    invoice_id = fields.Many2one(comodel_name="account.move",
                                 string="Invoice", ondelete='restrict',
                                 domain=[("move_type", "=", "out_invoice")],
                                 readonly=True, tracking=True)
    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        readonly=False,
        domain="[('id', 'in', suitable_journal_ids)]",
        default=_get_default_journal,
    )

    suitable_journal_ids = fields.Many2many(
        'account.journal',
        compute='_compute_suitable_journal_ids',
    )

    @api.depends('company_id')
    def _compute_suitable_journal_ids(self):
        for m in self:
            company = m.company_id.id or self.env.company.id
            m.suitable_journal_ids = self.env['account.journal'].search(
                [("type", "=", "sale"),
                 ("company_id", "=", company)
                 ])

    @api.constrains("admin_fees")
    def _check_admin_fees(self):
        if any(rec.admin_fees and rec.admin_fees < 0 for rec in self):
            raise ValidationError(_("Administrative fees must be positive"))

    def action_sold(self):
        res = super().action_sold()
        #  Generate invoice
        for prop in self:
            if not prop.journal_id:
                raise UserError("Please create a journal of type sale for this company")
            invoice_line_vals = [
                        Command.create(
                            {
                                "name": prop.name+' Sale',
                                "quantity": 1.0,
                                "price_unit": prop.selling_price,
                            },
                        ),
                    ]
            if prop.admin_fees:
                invoice_line_vals.append(
                    Command.create(
                        {
                            "name": "Administrative fees",
                            "quantity": 1.0,
                            "price_unit": prop.admin_fees,
                        },
                    ),
                )
            prop.invoice_id = self.env["account.move"].create(
                {
                    "partner_id": prop.buyer_id.id,
                    "move_type": "out_invoice",
                    "journal_id": prop.journal_id.id,
                    "currency_id": prop.currency_id.id,
                    "invoice_line_ids": invoice_line_vals,
                }
            )
        return res
