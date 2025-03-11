import frappe
import random
from slugify import slugify
from frappe.model.document import Document

class Lead(Document):

    def after_insert(self):
        """Assign new leads when created with 'Cold Calling' status."""
        self.owner_of_lead = frappe.session.user

        if self.status == "Cold Calling":
            assign_to_team_and_l2(self, "CC Team")

    def on_change(self):
        """Handle lead reassignments based on status changes."""
        previous_status = self.get_doc_before_save().status if self.get_doc_before_save() else None

        if self.status == "Lead":
            remove_all_shares(self.name)
            assign_to_team_and_l2(self, "LR Team")

        elif self.status == "Register":
            if previous_status == "Cold Calling":
                remove_all_shares(self.name)
                assign_to_team_and_l2(self, "LR Team")
            elif previous_status == "Lead":
                frappe.msgprint("✅ Previous status was 'Lead' — Keeping the current team assignment.")

        elif self.status == "Customer":
            remove_all_shares(self.name)
            assign_to_team_and_l2(self, "Customer Team")

# ------------------------------- #
#       ASSIGNMENT LOGIC          #
# ------------------------------- #

def assign_to_team_and_l2(doc, team_type):
    """Assign leads to a Team and distribute to an L2 within that team."""

    # Fetch available teams
    teams = frappe.get_all("Teams", filters={"team_type": team_type}, fields=["name"])

    if not teams:
        frappe.throw(f"No teams available for {team_type}")

    # Round-robin logic using Lead Settings
    lead_settings_field = get_lead_settings_field(team_type)
    last_assigned_team = frappe.db.get_single_value("Lead Settings", lead_settings_field)
    team_names = [team['name'] for team in teams]

    index = 0 if last_assigned_team not in team_names else (team_names.index(last_assigned_team) + 1) % len(team_names)

    selected_team = teams[index]

    # Update Lead Settings for tracking last assigned team
    frappe.db.set_value("Lead Settings", None, lead_settings_field, selected_team["name"])

    frappe.db.set_value("Lead", doc.name, "assigned_team", selected_team["name"])

    # Distribute Lead to L2 (Fair Distribution)
    l2_members = frappe.get_all("Team Member", filters={
        "team": selected_team["name"],  # ✅ Corrected back to `team`
        "role": "L2"
    }, fields=["user"])

    if l2_members:
        assigned_l2 = random.choice(l2_members)
        frappe.msgprint(f"✅ Assigned L2: {assigned_l2['user']}")
        frappe.db.set_value("Lead", doc.name, "assigned_to", assigned_l2['user'])
        frappe.share.add("Lead", doc.name, assigned_l2['user'])
    doc.reload()
    
    # Confirm success message
    frappe.msgprint(f"✅ Saved Successfully - Assigned Team: {selected_team['name']}, Assigned To: {assigned_l2['user']}")


def remove_all_shares(lead_name):
    """Remove all shared users for a given Lead."""
    shared_users = frappe.get_all("DocShare", filters={
        "share_doctype": "Lead",
        "share_name": lead_name
    }, fields=["user"])

    for user in shared_users:
        frappe.share.remove("Lead", lead_name, user['user'])

def get_lead_settings_field(team_type):
    """Converts team_type like 'CC Team' → 'last_assigned_cc_team'"""
    return f"last_assigned_{team_type.lower().replace(' ', '_')}"       