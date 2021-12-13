# -*- coding: utf-8 -*-
# Copyright (c) 2020, Frappe and contributors
# For license information, please see license.txt

import frappe
import secrets
import json
import requests


@frappe.whitelist(allow_guest=True)
def email_ping():
	return "pong"


@frappe.whitelist(allow_guest=True)
def setup(**data):
	if data["key"] == "fcmailfree100":
		return {
			"id": "postmaster@sandbox7b75d637c8164b9eac236ab5a486feae.mailgun.org",
			"pass": "ae06ff0d9c32b9e6a4ed4163d52e982f-2ac825a1-66ef7b67",
		}


def validate_plan(secret_key, site):
	"""
	check if subscription is active on marketplace and get activation date
	"""
	# ToDo: verify this key from marketplace
	# ToDo: check plan activation date from marketplace
	active = 1 if secret_key == "fcmailfree100" else 0
	# if active:
	# count = frappe.db.count(
	# "QMail Log", filters={"site": site, "status": "delivered", "date": [">=", plan_activation_date]}
	# )

	# if count < int(active[0]):
	# return True

	return True if active else False


@frappe.whitelist(allow_guest=True)
def send_mail(**data):
	files = frappe._dict(frappe.request.files)
	data = json.loads(data["data"])

	if validate_plan(data["sk_mail"], data["site"]):
		api_key, domain = frappe.db.get_value(
			"Press Settings", None, ["mailgun_api_key", "root_domain"]
		)

		content = "html" if data["html"] else "text"

		attachments = []
		if files:
			for file_name, bin_data in files.items():
				attachments.append(("attachment", (file_name, bin_data)))

		requests.post(
			f"https://api.mailgun.net/v3/{domain}/messages",
			auth=("api", f"{api_key}"),
			files=attachments,
			data={
				"v:site_name": f"{data['site']}",
				"v:sk_mail": f"{data['sk_mail']}",
				"v:message_id": f"{data['message_id']}",
				"from": f"{data['sender']}",
				"to": data["recipient"],
				"cc": data["cc"],
				"bcc": data["bcc"],
				"subject": data["subject"],
				content: data["content"],
			},
		)

		return "Successful"

	return "Error"


@frappe.whitelist(allow_guest=True)
def send_mime_mail(**data):
	files = frappe._dict(frappe.request.files)
	data = json.loads(data["data"])
	api_key, domain = frappe.db.get_value(
		"Press Settings", None, ["mailgun_api_key", "root_domain"]
	)

	resp = requests.post(
		f"https://api.mailgun.net/v3/{domain}/messages.mime",
		auth=("api", f"{api_key}"),
		data={"to": data["recipients"], "v:sk_mail": data["sk_mail"]},
		files={"message": files["mime"].read()},
	)

	if resp.status_code == 200:
		return "Sending"

	return "Error"


@frappe.whitelist(allow_guest=True)
def event_log(**data):
	event_data = data["event-data"]
	headers = event_data["message"]["headers"]
	message_id = headers["message-id"]
	site = message_id.split("@")[1]
	status = event_data["event"]
	secret_key = event_data["user-variables"]["sk_mail"]

	frappe.get_doc(
		{
			"doctype": "Mail Log",
			"unique_token": secrets.token_hex(25),
			"message_id": message_id,
			"sender": headers["from"],
			"recipient": headers["to"],
			"subject": headers["subject"],
			"site": site,
			"status": event_data["event"],
			"subscription_key": secret_key,
			"log": json.dumps(data),
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()

	data = {"status": status, "message_id": message_id}

	try:
		requests.post(
			f"https://{site}/api/method/mail.mail.doctype.mail_settings.mail_settings.update_status",
			data=data,
		)
	except:
		return "Successful", 200

	return "Successful", 200
