import argparse
import json
import os
import sys
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


def load_policy(policy_path: str) -> dict:
    with open(policy_path, "r", encoding="utf-8") as f:
        return json.load(f)


def dest_key(country: str, city: str) -> str:
    return f"{country}|{city}"


def build_policy_story(policy: dict) -> list:
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle(
        "PolicyTitle",
        parent=styles["Heading1"],
        fontSize=16,
        alignment=1,
        spaceAfter=14,
    )

    story.append(Paragraph("Travel Expense Policy (English)", title_style))
    story.append(Spacer(1, 8))

    # Overview
    overview = [
        ["Policy Name:", policy.get("policy_name", "-")],
        ["Currency:", policy.get("currency", "CNY")],
        ["Effective Date:", policy.get("effective_date", "-")],
        ["Employee Levels:", ", ".join(policy.get("levels", [])) or "-"]
    ]
    t = Table(overview, colWidths=[2.0 * inch, 4.5 * inch])
    t.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
        ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
    ]))
    story.append(t)
    story.append(Spacer(1, 14))

    # Global rules
    story.append(Paragraph("Global Rules", styles["Heading2"]))
    gr = policy.get("global_rules", {})
    bullets = [
        f"Airfare: {gr.get('airfare', {}).get('class_requirement', '')}",
        f"Airfare exception: {gr.get('airfare', {}).get('business_exception', '')}",
        f"Evidence: {gr.get('airfare', {}).get('evidence', '')}",
        f"Receipt threshold: CNY {gr.get('receipt_threshold', 0)} (receipt required above threshold)",
    ]
    if gr.get("client_entertainment_exception"):
        ce = gr["client_entertainment_exception"]
        bullets.append(
            f"Client entertainment exception: up to {ce.get('multiplier', 1)}x meals cap, {ce.get('approval', 'approval required')}"
        )
    for b in bullets:
        story.append(Paragraph(f"- {b}", styles["Normal"]))
    story.append(Spacer(1, 10))

    # Destination-specific rules
    story.append(Paragraph("Destination-Specific Caps", styles["Heading2"]))
    units = policy.get("units", {})
    for dest_key_str, rules in policy.get("destinations", {}).items():
        try:
            country, city = dest_key_str.split("|")
        except ValueError:
            country, city = dest_key_str, "-"
        story.append(Spacer(1, 6))
        story.append(Paragraph(f"{city}, {country}", styles["Heading3"]))

        # Build per-level caps table (Accommodation + Meals)
        levels = policy.get("levels", [])
        header = ["Level", f"Accommodation ({units.get('accommodation_per_night', 'per night')})", f"Meals ({units.get('meals_per_day', 'per day')})"]
        data = [header]
        acc = rules.get("accommodation_per_night", {})
        meals = rules.get("meals_per_day", {})
        for L in levels:
            data.append([
                L,
                str(acc.get(L, "-")),
                str(meals.get(L, "-"))
            ])
        tbl = Table(data, colWidths=[1.0 * inch, 2.2 * inch, 2.2 * inch])
        tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(tbl)

        # Per-day/per-trip caps (destination wide)
        story.append(Spacer(1, 6))
        other_caps = [
            ["Local transport per day:", f"{rules.get('local_transport_per_day', '-') } {units.get('local_transport_per_day', '')}"],
            ["Communication per trip:", f"{rules.get('communication_per_trip', '-') } {units.get('communication_per_trip', '')}"],
            ["Miscellaneous per trip:", f"{rules.get('misc_per_trip', '-') } {units.get('misc_per_trip', '')}"],
        ]
        other_tbl = Table(other_caps, colWidths=[2.5 * inch, 3.0 * inch])
        other_tbl.setStyle(TableStyle([
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.8, colors.black),
            ("BACKGROUND", (0, 0), (0, -1), colors.lightgrey),
        ]))
        story.append(other_tbl)

    # Footer
    story.append(Spacer(1, 14))
    story.append(Paragraph("Note: All amounts are in CNY unless otherwise noted.", styles["Italic"]))
    return story


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent_workspace", type=str, required=True)
    parser.add_argument("--launch_time", type=str, required=False, help="ISO8601 timestamp (for consistency with preprocess)")
    parser.add_argument("--output_filename", type=str, default="policy_en.pdf")
    args = parser.parse_args()

    # Locate policy JSON next to groundtruth
    current_dir = os.path.dirname(os.path.abspath(__file__))
    task_root = os.path.dirname(current_dir)
    groundtruth_dir = os.path.join(task_root, "groundtruth_workspace")
    policy_path = os.path.join(groundtruth_dir, "policy_standards_en.json")

    policy = load_policy(policy_path)

    # Prepare output dir
    files_dir = os.path.join(args.agent_workspace, "files")
    os.makedirs(files_dir, exist_ok=True)
    pdf_path = os.path.join(files_dir, args.output_filename)

    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    story = build_policy_story(policy)
    doc.build(story)

    print(f"✅ Policy PDF generated: {os.path.abspath(pdf_path)}")


if __name__ == "__main__":
    main()

