from . import __version__ as app_version

app_name = "whatsapp_calling"
app_title = "WhatsApp Calling"
app_publisher = "Your Company"
app_description = "WhatsApp voice calling integration for ERPNext CRM"
app_icon = "octicon octicon-device-mobile"
app_color = "#25D366"
app_email = "support@example.com"
app_license = "MIT"
app_version = app_version

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "whatsapp_calling.bundle.css"
app_include_js = "whatsapp_calling.bundle.js"

# include js, css files in header of web template
# web_include_css = "/assets/whatsapp_calling/css/whatsapp_calling.css"
# web_include_js = "/assets/whatsapp_calling/js/whatsapp_calling.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "whatsapp_calling/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Lead": "public/js/lead_call_button.js",
    "CRM Lead": "public/js/crm_lead.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "whatsapp_calling.utils.jinja_methods",
# 	"filters": "whatsapp_calling.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "whatsapp_calling.install.before_install"
# after_install = "whatsapp_calling.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "whatsapp_calling.uninstall.before_uninstall"
# after_uninstall = "whatsapp_calling.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "whatsapp_calling.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
# 	"all": [
# 		"whatsapp_calling.tasks.all"
# 	],
# 	"daily": [
# 		"whatsapp_calling.tasks.daily"
# 	],
	"hourly": [
		"whatsapp_calling.whatsapp_calling.tasks.cleanup_old_recordings"
	],
	"daily": [
		"whatsapp_calling.whatsapp_calling.tasks.check_expired_permissions"
	],
# 	"weekly": [
# 		"whatsapp_calling.tasks.weekly"
# 	],
# 	"monthly": [
# 		"whatsapp_calling.tasks.monthly"
# 	],
}

# Testing
# -------

# before_tests = "whatsapp_calling.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "whatsapp_calling.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "whatsapp_calling.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"whatsapp_calling.auth.validate"
# ]

