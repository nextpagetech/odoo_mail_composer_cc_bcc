# Copyright 2023 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models

from .mail_mail import format_emails


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def _message_create(self, values_list):
        context = self.env.context
        res = super()._message_create(values_list)
        partners_cc = context.get("partner_cc_ids", None)
        if partners_cc:
            res.recipient_cc_ids = partners_cc
        partners_bcc = context.get("partner_bcc_ids", None)
        if partners_bcc:
            res.recipient_bcc_ids = partners_bcc
        return res

    def _notify_by_email_get_base_mail_values(self, message, additional_values=None):
        """
        This is to add cc, bcc addresses to mail.mail objects so that email
        can be sent to those addresses.
        """
        context = self.env.context

        res = super()._notify_by_email_get_base_mail_values(
            message, additional_values=additional_values
        )
        partners_cc = context.get("partner_cc_ids", None)
        if partners_cc:
            res["email_cc"] = format_emails(partners_cc)
        partners_bcc = context.get("partner_bcc_ids", None)
        if partners_bcc:
            res["email_bcc"] = format_emails(partners_bcc)
        return res

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        ResPartner = self.env["res.partner"]
        MailFollowers = self.env["mail.followers"]
        rdata = super()._notify_get_recipients(message, msg_vals, **kwargs)
        context = self.env.context

        if not context.get("is_from_composer"):
            return rdata

        # Make all existing entries "customer"
        for pdata in rdata:
            pdata["type"] = "customer"

        # 🔧 Normalize context values to recordsets
        partners_cc = context.get("partner_cc_ids") or ResPartner
        if isinstance(partners_cc, (list, tuple)):
            partners_cc = ResPartner.browse(partners_cc)
        partners_bcc = context.get("partner_bcc_ids") or ResPartner
        if isinstance(partners_bcc, (list, tuple)):
            partners_bcc = ResPartner.browse(partners_bcc)

        partners_cc_bcc = partners_cc | partners_bcc

        msg_sudo = message.sudo()
        message_type = msg_vals.get("message_type") if msg_vals else msg_sudo.message_type
        subtype_id = msg_vals.get("subtype_id") if msg_vals else msg_sudo.subtype_id.id

        recipients_cc_bcc = MailFollowers._get_recipient_data(
            None, message_type, subtype_id, partners_cc_bcc.ids
        )

        existing = {rec["id"] for rec in rdata}
        for _, value in recipients_cc_bcc.items():
            for _, data in value.items():
                if not data.get("id"):
                    continue
                notif = data.get("notif") or "email"
                pdata = {
                    "id": data.get("id"),
                    "active": data.get("active"),
                    "share": data.get("share"),
                    "notif": notif,
                    "type": "customer",
                    "is_follower": data.get("is_follower"),
                    "uid": data.get("uid"),  # ✅ ensure key exists
                }
                if pdata["id"] in existing:
                    continue
                existing.add(pdata["id"])
                rdata.append(pdata)
        return rdata



    def _notify_by_email_get_final_mail_values(
        self, recipient_ids, base_mail_values, additional_values=None
    ):
        """
        This is to add cc, bcc recipients' ids to recipient_ids of mail.mail
        """
        res = super()._notify_by_email_get_final_mail_values(
            recipient_ids, base_mail_values, additional_values=additional_values
        )
        context = self.env.context
        r_ids = list(recipient_ids)
        partners_cc = context.get("partner_cc_ids", None)
        if partners_cc:
            r_ids += partners_cc.ids
        partners_bcc = context.get("partner_bcc_ids", None)
        if partners_bcc:
            r_ids += partners_bcc.ids
        if partners_cc or partners_bcc:
            res["recipient_ids"] = tuple(set(r_ids))
        return res

    def _notify_get_recipients_classify(self, *args, **kwargs):
        """
        Compatible override with Odoo 18 signature.
        Accepts recipient_data, model_name, msg_vals (positional), plus kwargs.
        """
        # Odoo passes: (recipient_data, model_name, msg_vals)
        recipient_data = args[0] if len(args) > 0 else None
        model_name = args[1] if len(args) > 1 else None
        msg_vals = args[2] if len(args) > 2 else kwargs.get("msg_vals")

        res = super()._notify_get_recipients_classify(*args, **kwargs)

        is_from_composer = self.env.context.get("is_from_composer", False)
        if not is_from_composer:
            return res

        ids = []
        customer_data = None
        for rcpt_data in res:
            if rcpt_data["notification_group_name"] == "customer":
                customer_data = rcpt_data
            else:
                ids += rcpt_data["recipients"]

        if not customer_data and res:
            customer_data = res[0]
            customer_data["notification_group_name"] = "customer"
            customer_data["recipients"] = ids
        elif customer_data:
            customer_data["recipients"] += ids

        return [customer_data] if customer_data else res




    # def _notify_get_recipients_classify(
    #     self, recipient_data, model_name, msg_vals=None
    # ):
    #     res = super()._notify_get_recipients_classify(
    #         recipient_data, model_name, msg_vals=msg_vals
    #     )
    #     is_from_composer = self.env.context.get("is_from_composer", False)
    #     if not is_from_composer:
    #         return res
    #     ids = []
    #     customer_data = None
    #     for rcpt_data in res:
    #         if rcpt_data["notification_group_name"] == "customer":
    #             customer_data = rcpt_data
    #         else:
    #             ids += rcpt_data["recipients"]
    #     if not customer_data:
    #         customer_data = res[0]
    #         customer_data["notification_group_name"] = "customer"
    #         customer_data["recipients"] = ids
    #     else:
    #         customer_data["recipients"] += ids
    #     return [customer_data]
