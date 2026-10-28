# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, api, fields, models, tools

CC_BCC_FIELDS = {
    "email_cc": "partner_cc_ids",
    "email_bcc": "partner_bcc_ids",
}


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    @api.model
    def default_get(self, fields_list):
        company = self.env.company
        res = super().default_get(fields_list)
        partner_cc = company.default_partner_cc_ids
        if partner_cc:
            res["partner_cc_ids"] = [Command.set(partner_cc.ids)]
        partner_bcc = company.default_partner_bcc_ids
        if partner_bcc:
            res["partner_bcc_ids"] = [Command.set(partner_bcc.ids)]
        return res

    partner_cc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_cc_rel",
        "wizard_id",
        "partner_id",
        string="Cc",
    )
    partner_bcc_ids = fields.Many2many(
        "res.partner",
        "mail_compose_message_res_partner_bcc_rel",
        "wizard_id",
        "partner_id",
        string="Bcc",
    )

    def _onchange_template_id(self, template_id, composition_mode, model, res_id):
        if not template_id:
            return {"value": {}}
        ctx = {"is_from_composer": True}
        ctx.update(self.env.context)
        self_ctx = self.with_context(**ctx)
        res = super(MailComposeMessage, self_ctx)._onchange_template_id(
            template_id, composition_mode, model, res_id
        )
        res_ids = [res_id]
        # tpl_partners_only need to be False for email_cc value
        tmpl_ctx = self.env["mail.template"].with_context(tpl_partners_only=False)
        mail_tmpl = tmpl_ctx.browse(template_id)
        template_values = mail_tmpl.generate_email(res_ids, CC_BCC_FIELDS)
        values = template_values[res_id]
        for fname in CC_BCC_FIELDS:
            value = values.get(fname, None)
            if not value:
                continue
            self._set_partner_field(CC_BCC_FIELDS[fname], value)
        return res

    def _set_partner_field(self, field_name, email):
        if field_name not in CC_BCC_FIELDS.values():
            return
        for_email = [("email", "in", tools.email_split(email))]
        partner = self.env["res.partner"].search(for_email)
        current_partners = getattr(self, field_name)
        setattr(self, field_name, current_partners + partner)

    def _action_send_mail(self, auto_commit=False):
        # Work on a single wizard record (usual case); loop if needed
        self.ensure_one()

        follower_partners = self.env['res.partner']

        # ✅ res_ids is a STRING in this build → parse it properly
        res_ids = self._evaluate_res_ids() or []
        if self.model and res_ids:
            followers = self.env['mail.followers'].search([
                ('res_model', '=', self.model),
                ('res_id', 'in', res_ids),
            ])
            follower_partners = followers.mapped('partner_id')

        # (optional) reflect followers into CC widget in the UI
        if follower_partners:
            # If your wizard view shows a partner M2M for CC (usual with this module):
            self.partner_cc_ids = (self.partner_cc_ids | follower_partners)
            # If you ALSO have an `email_cc` Char on the wizard, keep it in sync:
            if 'email_cc' in self._fields:
                self.email_cc = ",".join(p.email for p in follower_partners if p.email)

        # Don’t impact mass mailing
        if self.composition_mode == "mass_mail":
            return super()._action_send_mail(auto_commit)

        # ✅ Pass RECORDSETS in context (not lists), to match your mail_thread override
        ctx = dict(self.env.context)
        ctx.update({
            "is_from_composer": True,
            "partner_cc_ids": (self.partner_cc_ids | follower_partners),  # recordset
            "partner_bcc_ids": self.partner_bcc_ids,                      # recordset
        })

        # If you want an empty “To” by default, clear the wizard’s partner_ids:
        # Keep existing "To" recipients unless a context flag asks to clear them.
        if ctx.get('mail_clear_default_to') and 'partner_ids' in self._fields:
            self.partner_ids = [(6, 0, [])]

        return super(MailComposeMessage, self.with_context(**ctx))._action_send_mail(auto_commit)



