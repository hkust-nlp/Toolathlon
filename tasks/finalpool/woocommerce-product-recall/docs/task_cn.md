对woocommerce商店中指定型号的产品下架，并对相应产品进行召回。给定产品型号，搜索该产品相关的历史订单，并通过 emails 给相应的顾客邮箱发送召回邮件，邮件模板见`recall_email_template.md`,邮件中需要包含按照模板`recall_form_template.json`创建的 Google_Forms 召回表单,并在`recall_report.json`中返回表单信息，模板如下：

```json
{
  "form_id": "Google Forms表单ID",
  "form_url": "Google Forms表单链接",
}
```