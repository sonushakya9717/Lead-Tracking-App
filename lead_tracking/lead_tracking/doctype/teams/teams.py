# Copyright (c) 2025, support@assetplus.com and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
from slugify import slugify


class Teams(Document):
	def autoname(self):
		self.name = slugify(self.team_code)
