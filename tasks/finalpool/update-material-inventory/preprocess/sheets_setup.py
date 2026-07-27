"""Google Sheets helper used by the update-material-inventory grader."""

from __future__ import annotations

from typing import Dict, Optional

from googleapiclient.errors import HttpError

from utils.app_specific.googlesheet.drive_helper import get_google_service


class GoogleSheetsClient:
    """Small task-specific client for reading material inventory from Sheets."""

    SPREADSHEET_MIME = "application/vnd.google-apps.spreadsheet"
    FOLDER_MIME = "application/vnd.google-apps.folder"

    def __init__(self) -> None:
        self.drive_service = None
        self.sheets_service = None

    def authenticate(self) -> bool:
        try:
            self.drive_service, self.sheets_service = get_google_service()
            return True
        except Exception:
            self.drive_service = None
            self.sheets_service = None
            return False

    def _resolve_spreadsheet_id(self, spreadsheet_or_folder_id: str) -> Optional[str]:
        """Accept either a spreadsheet ID or the task folder ID."""
        if not spreadsheet_or_folder_id or not self.drive_service:
            return None

        try:
            meta = self.drive_service.files().get(
                fileId=spreadsheet_or_folder_id,
                fields="id,name,mimeType",
                supportsAllDrives=True,
            ).execute()
        except HttpError:
            return spreadsheet_or_folder_id

        mime_type = meta.get("mimeType")
        if mime_type == self.SPREADSHEET_MIME:
            return spreadsheet_or_folder_id
        if mime_type != self.FOLDER_MIME:
            return None

        results = self.drive_service.files().list(
            q=(
                f"'{spreadsheet_or_folder_id}' in parents "
                f"and mimeType='{self.SPREADSHEET_MIME}' and trashed=false"
            ),
            fields="files(id,name)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()
        files = results.get("files", [])
        if not files:
            return None

        preferred_title = "Raw Material Inventory Management Test"
        for item in files:
            if item.get("name") == preferred_title:
                return item.get("id")
        return files[0].get("id")

    def get_current_inventory(self, spreadsheet_id: str) -> Dict[str, float]:
        if not self.sheets_service:
            raise RuntimeError("Google Sheets client is not authenticated")

        resolved_id = self._resolve_spreadsheet_id(spreadsheet_id)
        if not resolved_id:
            return {}

        response = self.sheets_service.spreadsheets().values().get(
            spreadsheetId=resolved_id,
            range="Material_Inventory",
        ).execute()
        values = response.get("values", [])
        if not values:
            return {}

        headers = [str(cell).strip() for cell in values[0]]
        material_col = self._find_column(headers, ["原材料ID", "material id", "raw material id"])
        quantity_col = self._find_column(headers, ["当前库存", "current stock", "inventory", "quantity"])
        if material_col is None or quantity_col is None:
            return {}

        inventory: Dict[str, float] = {}
        for row in values[1:]:
            if len(row) <= max(material_col, quantity_col):
                continue
            material_id = str(row[material_col]).strip()
            if not material_id:
                continue
            try:
                inventory[material_id] = float(str(row[quantity_col]).strip())
            except ValueError:
                continue
        return inventory

    @staticmethod
    def _find_column(headers: list[str], candidates: list[str]) -> Optional[int]:
        normalized = {header.lower().replace(" ", ""): idx for idx, header in enumerate(headers)}
        for candidate in candidates:
            key = candidate.lower().replace(" ", "")
            if key in normalized:
                return normalized[key]
        return None
