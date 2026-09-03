# Copyright 2023 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Email CC and BCC",
    "summary": "This module enables sending mail to CC and BCC partners in mail composer form.",
    "description": """
Adds Cc and Bcc partner fields to the mail composer, company defaults, email template Bcc, and related mail/message views.
    """,
    "version": "18.0.1.0.0",
    "category": "Productivity",
    "website": "https://nextpagetechnologies.com",
    "author": "Next Page Technologies Pvt Ltd",
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "preloadable": True,
    "depends": [
        "mail",
    ],
    "data": [
        "views/res_company_views.xml",
        "views/mail_mail_views.xml",
        "views/mail_message_views.xml",
        "views/mail_template_views.xml",
        "wizards/mail_compose_message_view.xml",
    ],
}
