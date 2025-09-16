Remove products of a specified model from your WooCommerce store and recall the corresponding products. The product must be taken off the shelf (set to draft or private status, or with catalog visibility set to hidden), rather than deleted. Given a product model, search for historical orders related to that product and send a recall email to the corresponding customer's email address. See `recall_email_template.md` for the email template. The email must include a Google Forms recall form created using the `recall_form_template.json` template, and return the form information in `recall_report.json`. The template is as follows:

```json
{
"form_id": "Google Forms form ID",

"form_url": "Google Forms form link",
}
```