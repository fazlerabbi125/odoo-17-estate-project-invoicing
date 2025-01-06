from odoo.exceptions import UserError, ValidationError
from odoo import _

def check_duplicate_rec(rec, envObj, condList: list, msg: str):
    cond = [('id', '!=', rec.id),] + condList
    found = envObj.search_count(cond, limit=2)
    if found:
        raise ValidationError(_(msg))