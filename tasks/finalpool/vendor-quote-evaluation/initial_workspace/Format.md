# Evaluation Sheet Format

## Files

- Save everything in the current workspace.
- Create one Word document per vendor (latest quotation only), named `Quotation_Evaluation_<VendorCode>.docx`, for example `Quotation_Evaluation_NPS.docx`.
- Create a plain-text file `award.txt` that contains only the name of the vendor to be awarded the contract, exactly as written on the "Vendor:" line of its quotation. Nothing else.

## Default formatting

- Font: Cambria, 11 pt, left-aligned, unless stated otherwise.
- Section titles ("Quotation Summary:", "Due Diligence Notes:", "Evaluation Conclusion:") in bold.

## Document structure

1. First-level heading, centered, Calibri 14 pt bold: `Quotation Evaluation Sheet`
2. Paragraph: `Vendor Code: <code>` (for example `Vendor Code: NPS`)
3. Paragraph: `Vendor Name: <name>`, the name exactly as it appears on the "Vendor:" line of the quotation (for example `Vendor Name: Northpeak Office Supply`)
4. Section title `Quotation Summary:` followed by the complete text of the vendor's quotation entry as it appears in Vendor_Quotations.docx, from its "Vendor Code:" line to the end of its "Notes:" line, copied verbatim. Do not include the "Quotation N" label. For a vendor with several revisions, copy only the latest one.
5. Section title `Due Diligence Notes:` followed by the complete text of the vendor's entry in Supplier_Due_Diligence_Notes.docx, from its "Vendor Code:" line to the end of its "Notes:" line, copied verbatim. Do not include the "Supplier N" label.
6. Section title `Evaluation Conclusion:` followed by a table with two rows and four columns:
   - Header row: `Total Evaluated Cost (USD)` | `Mandatory Criteria Met` | `Decision` | `Disqualification Reasons`
   - Data row:
     - the Total Evaluated Cost in USD with two decimals and thousands separators, without a currency symbol (for example `46,515.00`);
     - the number of mandatory criteria met, for example `6/6`;
     - the decision: `Award`, `Compliant - Not Selected` or `Disqualified`;
     - the reason phrases from Evaluation_Rules.md separated by `; `, or `None` for a compliant vendor.
   - Table formatting: gridline borders on all cells; header row shaded D9D9D9 and data row shaded DAEEF3; cell text centered horizontally and top-aligned vertically.
7. Nothing else: no additional paragraphs, comments, notes, dates or signatures.
