{
    "name": "Estate Advertisement",
    "version": "17.2.5",
    "summary": "A module for odoo-17 training purposes",
    "description": """
    This is module is for odoo-17 training purposes
    It will cover week-2 content
    """,
    "author": "Faiyaz",
    "category": "Example",
    # "website": ""
    "license":"LGPL-3",
    "depends": ["base", "web", "mail"],
    "data": [
        'security/estate_security.xml',
        'security/ir.model.access.csv',
        "views/estate_property_offer_views.xml",
        "views/estate_property_tag_views.xml",
        "views/estate_property_type_views.xml",
        "views/estate_property_views.xml",
        "views/estate_menus.xml",
    ],
    "application": True,
}