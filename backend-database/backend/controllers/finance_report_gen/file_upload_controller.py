import os
import io
import zipfile
import pandas as pd
from typing import Dict, Any, Tuple, List
import math
import numpy as np
from flask import current_app
from datetime import datetime
from models.lead_model import db
from models.finance_report_gen.financial_report_upload_model import FinancialReportUpload
from models.finance_report_gen.financial_file_model import FinancialFile
from utils.finance_file_manager import FilePersistenceManager


def _get_csv_shape(file_path: str) -> Tuple[int, int]:
    df_full = pd.read_csv(file_path)
    return int(df_full.shape[0]), int(df_full.shape[1])


def _get_excel_shapes(file_path: str) -> Dict[str, Tuple[int, int]]:
    shapes: Dict[str, Tuple[int, int]] = {}
    try:
        xls = pd.ExcelFile(file_path)
        for sheet in xls.sheet_names:
            df_full = pd.read_excel(file_path, sheet_name=sheet)
            shapes[sheet] = (int(df_full.shape[0]), int(df_full.shape[1]))
    except Exception as e:
        current_app.logger.error(f"[FileUpload] Failed reading Excel shapes for {os.path.basename(file_path)}: {e}")
        raise
    return shapes


class FileUpload:
    def _to_json_safe(self, value):
        """Convert values to JSON-safe equivalents:
        - NaN/NaT/None/Inf -> None
        - numpy numeric types -> native Python numbers
        - leave others as-is
        """
        # Pandas/NumPy NaN/NaT
        try:
            if pd.isna(value):
                return None
        except Exception:
            pass

        # Float NaN/Inf
        if isinstance(value, float):
            if math.isnan(value) or math.isinf(value):
                return None
            return value

        # Numpy numbers to python scalars
        if np is not None and isinstance(value, (np.floating, np.integer)):
            # Ensure not NaN/Inf
            fval = float(value)
            if math.isnan(fval) or math.isinf(fval):
                return None
            try:
                return value.item()
            except Exception:
                return float(value)

        return value

    def _sanitize_json(self, obj):
        """Recursively sanitize dict/list values to be JSON compliant (no NaN/Inf)."""
        if isinstance(obj, dict):
            return {k: self._sanitize_json(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._sanitize_json(v) for v in obj]
        return self._to_json_safe(obj)
    def allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed (from config)."""
        allowed = current_app.config.get("ALLOWED_EXTENSIONS") or set()
        return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed

    def _read_csv_preview(self, file_path: str) -> Dict[str, Any]:
        current_app.logger.info(f"[FileUpload] Reading CSV preview for {os.path.basename(file_path)}")
        df = pd.read_csv(file_path, nrows=40)
        preview_df = df.head(5)
        rows, cols = _get_csv_shape(file_path)
        # Sanitize columns (replace NaN headers with empty string, cast to str)
        clean_cols = []
        for c in list(preview_df.columns):
            safe = self._to_json_safe(c)
            clean_cols.append(str(safe) if safe is not None else "")
        # Sanitize row values (NaN/Inf -> None)
        clean_rows = self._sanitize_json(preview_df.to_dict("records"))
        result = {
            "columns": clean_cols,
            "rows": clean_rows,
            "shape": {"rows": rows, "cols": cols},
        }
        current_app.logger.info(f"[FileUpload] CSV preview shape rows={rows}, cols={cols}")
        return result

    def _read_excel_preview(self, file_path: str) -> Dict[str, Any]:
        current_app.logger.info(f"[FileUpload] Reading Excel preview for {os.path.basename(file_path)} (sheet-wise)")
        try:
            xls = pd.ExcelFile(file_path)
            shapes = _get_excel_shapes(file_path)
            sheets_preview: Dict[str, Any] = {}
            for sheet in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet, nrows=40)
                preview_df = df.head(5)
                r, c = shapes.get(sheet, (len(df.index), len(df.columns)))
                clean_cols = []
                for col in list(preview_df.columns):
                    safe = self._to_json_safe(col)
                    clean_cols.append(str(safe) if safe is not None else "")
                clean_rows = self._sanitize_json(preview_df.to_dict("records"))
                sheets_preview[sheet] = {
                    "columns": clean_cols,
                    "rows": clean_rows,
                    "shape": {"rows": r, "cols": c},
                }
            return {"sheets": sheets_preview}
        except Exception as e:
            current_app.logger.error(f"[FileUpload] Excel preview failed for {os.path.basename(file_path)}: {e}")
            raise

    def read_file_preview(self, file_path: str) -> Dict[str, Any]:
        """Read preview data from different file types.
        - CSV: returns columns, rows, shape
        - Excel: returns {"sheets": {sheet_name: {columns, rows, shape}}}
        """
        try:
            ext = os.path.splitext(file_path)[1].lower().lstrip(".")
            if ext == "csv":
                return self._read_csv_preview(file_path)
            elif ext in ["xls", "xlsx"]:
                return self._read_excel_preview(file_path)
            else:
                return {"columns": [], "rows": [], "shape": {"rows": 0, "cols": 0}}
        except Exception as e:
            current_app.logger.error(f"[FileUpload] Error reading file '{os.path.basename(file_path)}': {str(e)}")
            raise Exception(f"Error reading file '{os.path.basename(file_path)}': {str(e)}")

    def handle_zip_file(self, zip_path: str, extract_dest_dir: str) -> Dict[str, Any]:
        """Extract and process supported files from ZIP.
        - Persists extracted files to extract_dest_dir/<zip_stem>/...
        - Returns mapping of inner file path -> preview dict (includes shapes)
        - Enforces per-file size limit for entries inside ZIP (from config)
        - Protects against path traversal
        """
        results: Dict[str, Any] = {}

        zip_stem = os.path.splitext(os.path.basename(zip_path))[0]
        target_base = os.path.join(extract_dest_dir, zip_stem)
        target_base_abs = os.path.abspath(target_base)
        os.makedirs(target_base, exist_ok=True)
        current_app.logger.info(f"[FileUpload] Extracting ZIP to {target_base}")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            file_list = zip_ref.namelist()
            allowed = current_app.config.get("ALLOWED_EXTENSIONS") or set()
            supported = [
                f for f in file_list
                if "." in f and f.rsplit(".", 1)[1].lower() in allowed - {"zip"}
            ]

            if not supported:
                raise Exception("No supported files (CSV, XLS, XLSX) found in ZIP")

            per_file_cap = int(current_app.config.get("MAX_FILE_SIZE_BYTES", 10 * 1024 * 1024))

            for inner_path in supported:
                try:
                    info = zip_ref.getinfo(inner_path)
                    if info.file_size and info.file_size > per_file_cap:
                        results[inner_path] = {"error": f"Inner file too large (>{int(per_file_cap/1024/1024)}MB)"}
                        current_app.logger.warning(f"[FileUpload] Skipped inner file {inner_path}: > per-file cap")
                        continue

                    # Normalize and ensure safe extraction path
                    inner_norm = inner_path.replace("\\", "/").lstrip("/")
                    extract_path = os.path.join(target_base, inner_norm)
                    extract_path_abs = os.path.abspath(extract_path)
                    if not extract_path_abs.startswith(target_base_abs + os.sep) and extract_path_abs != target_base_abs:
                        results[inner_path] = {"error": "Unsafe path in ZIP entry"}
                        current_app.logger.warning(f"[FileUpload] Unsafe ZIP entry path: {inner_path}")
                        continue

                    os.makedirs(os.path.dirname(extract_path), exist_ok=True)

                    with zip_ref.open(inner_path) as source, open(extract_path, "wb") as dest:
                        dest.write(source.read())

                    preview = self.read_file_preview(extract_path)
                    results[inner_norm] = preview
                except Exception as e:
                    results[inner_path] = {"error": str(e)}
                    current_app.logger.error(f"[FileUpload] Error processing inner file {inner_path}: {e}")

        return results

    def _preview_from_bytes(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Preview CSV/XLS/XLSX content from memory without saving to disk."""
        try:
            ext = os.path.splitext(filename)[1].lower().lstrip(".")
            bio = io.BytesIO(content)
            if ext == "csv":
                df = pd.read_csv(bio, nrows=40)
                preview_df = df.head(5)
                # full shape requires reading all rows; re-read without nrows
                bio2 = io.BytesIO(content)
                rows, cols = int(pd.read_csv(bio2).shape[0]), int(df.shape[1])
                clean_cols = []
                for c in list(preview_df.columns):
                    safe = self._to_json_safe(c)
                    clean_cols.append(str(safe) if safe is not None else "")
                clean_rows = self._sanitize_json(preview_df.to_dict("records"))
                return {
                    "columns": clean_cols,
                    "rows": clean_rows,
                    "shape": {"rows": rows, "cols": cols},
                }
            elif ext in ["xls", "xlsx"]:
                xls = pd.ExcelFile(bio)
                sheets_preview: Dict[str, Any] = {}
                for sheet in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet, nrows=40)
                    preview_df = df.head(5)
                    # shape for sheet
                    bio_sheet = io.BytesIO(content)
                    full_df = pd.read_excel(bio_sheet, sheet_name=sheet)
                    clean_cols = []
                    for col in list(preview_df.columns):
                        safe = self._to_json_safe(col)
                        clean_cols.append(str(safe) if safe is not None else "")
                    clean_rows = self._sanitize_json(preview_df.to_dict("records"))
                    sheets_preview[sheet] = {
                        "columns": clean_cols,
                        "rows": clean_rows,
                        "shape": {"rows": int(full_df.shape[0]), "cols": int(full_df.shape[1])},
                    }
                return {"sheets": sheets_preview}
            else:
                return {"columns": [], "rows": [], "shape": {"rows": 0, "cols": 0}}
        except Exception as e:
            current_app.logger.error(f"[FileUpload] In-memory preview failed for {filename}: {e}")
            raise

    def process_and_persist_upload(self, files: List, user_id, form_meta: Dict[str, Any]) -> Dict[str, Any]:
        """Create FinancialReportUpload and FinancialFile rows directly without writing to disk.

        - Enforces size caps from config
        - Parses ZIP in-memory and creates child file rows for supported inner files
        - For CSV/XLS/XLSX, reads preview to compute column/row counts
        """
        allowed = current_app.config.get("ALLOWED_EXTENSIONS") or set()
        per_file_cap = current_app.config.get("FIN_PER_FILE_MAX_MB")
        zip_cap = current_app.config.get("FIN_MAX_ZIP_SIZE_MB")
        try:
            per_file_cap_bytes = int(per_file_cap) * 1024 * 1024 if per_file_cap is not None else 0
            zip_cap_bytes = int(zip_cap) * 1024 * 1024 if zip_cap is not None else 0
        except Exception:
            per_file_cap_bytes = 0
            zip_cap_bytes = 0

        if per_file_cap_bytes <= 0 or zip_cap_bytes <= 0:
            raise Exception("Server misconfiguration: size caps missing/invalid")

        # Validate optional form metadata
        industry = (form_meta.get("industry") or None)
        data_granularity = (form_meta.get("data_granularity") or None)
        if data_granularity and data_granularity not in {"monthly", "quarterly", "annual"}:
            raise Exception("Invalid data_granularity. Allowed: ['monthly','quarterly','annual']")

        upload = FinancialReportUpload(
            user_id=user_id,
            upload_date=datetime.utcnow(),
            industry=industry,
            data_granularity=data_granularity,
            status="uploaded",
            total_files=0,
            processed_files=0,
            notes=form_meta.get("notes"),
        )
        db.session.add(upload)
        db.session.flush()

        created_files: List[Dict[str, Any]] = []
        processed_files_count = 0
        total_files_count = 0
        errors: Dict[str, Any] = {}

        for storage in files:
            if not storage or not storage.filename:
                continue
            original_name = storage.filename
            ext = os.path.splitext(original_name)[1].lower().lstrip(".")
            total_files_count += 1

            if not self.allowed_file(original_name):
                errors[original_name] = {"error": "File type not supported. Allowed: CSV, XLS, XLSX, ZIP"}
                continue

            content: bytes = storage.read()
            storage.stream.seek(0)
            size_bytes = len(content) if content is not None else 0

            if size_bytes > per_file_cap_bytes:
                errors[original_name] = {"error": f"File too large. Maximum size per file is {int(per_file_cap_bytes/1024/1024)}MB"}
                continue

            try:
                if ext == "zip":
                    if size_bytes > zip_cap_bytes:
                        errors[original_name] = {"error": f"ZIP too large. Maximum size is {int(zip_cap_bytes/1024/1024)}MB"}
                        continue

                    with zipfile.ZipFile(io.BytesIO(content), "r") as zip_ref:
                        names = zip_ref.namelist()
                        supported_inner = [
                            n for n in names
                            if "." in n and n.rsplit(".", 1)[1].lower() in allowed - {"zip"}
                        ]
                        if not supported_inner:
                            errors[original_name] = {"error": "No supported files (CSV, XLS, XLSX) found in ZIP"}
                        for inner in supported_inner:
                            try:
                                info = zip_ref.getinfo(inner)
                                inner_size = info.file_size or 0
                                if inner_size > per_file_cap_bytes:
                                    errors[inner] = {"error": f"Inner file too large (>{int(per_file_cap_bytes/1024/1024)}MB)"}
                                    continue
                                inner_bytes = zip_ref.read(inner)
                                preview = self._preview_from_bytes(inner, inner_bytes)

                                # Determine counts
                                if "sheets" in preview:
                                    # choose first sheet for counts summary
                                    first_sheet = next(iter(preview["sheets"].values())) if preview["sheets"] else {"shape": {"rows": None, "cols": None}}
                                    row_count = first_sheet.get("shape", {}).get("rows")
                                    column_count = first_sheet.get("shape", {}).get("cols")
                                else:
                                    row_count = preview.get("shape", {}).get("rows")
                                    column_count = preview.get("shape", {}).get("cols")

                                ff = FinancialFile(
                                    upload_id=upload.upload_id,
                                    file_name=os.path.basename(inner),
                                    file_extension=f".{os.path.splitext(inner)[1].lower().lstrip('.')}",
                                    processed_file_path=None,
                                    file_size=int(inner_size),
                                    detected_periodicity=None,
                                    user_selected_periodicity=None,
                                    file_type="unknown",
                                    status="uploaded",
                                    column_count=column_count,
                                    row_count=row_count,
                                    processing_started_at=datetime.utcnow(),
                                    processing_completed_at=None,
                                )
                                db.session.add(ff)
                                db.session.flush()

                                # Save file using FilePersistenceManager
                                try:
                                    file_manager = FilePersistenceManager()

                                    # Save original file
                                    file_manager.save_original_file(
                                        file_id=str(ff.file_id),
                                        upload_id=str(upload.upload_id),
                                        file_content=inner_bytes,
                                        filename=os.path.basename(inner),
                                        metadata={
                                            'file_size': int(inner_size),
                                            'file_type': 'unknown',
                                            'column_count': column_count,
                                            'row_count': row_count
                                        }
                                    )

                                    # Also save as 'uploaded' stage (same as original)
                                    file_manager.save_stage_file(
                                        file_id=str(ff.file_id),
                                        stage_name='uploaded',
                                        data=inner_bytes,
                                        original_filename=os.path.basename(inner)
                                    )

                                    # Update database with file path
                                    file_manager.update_db_file_path(
                                        str(ff.file_id),
                                        'uploaded',
                                        file_manager.get_stage_file_path(str(ff.file_id), 'uploaded')
                                    )

                                    current_app.logger.info(f"[FileUpload] Successfully saved file: {os.path.basename(inner)}")
                                except Exception as file_error:
                                    current_app.logger.error(f"[FileUpload] Failed to save file {os.path.basename(inner)}: {str(file_error)}")
                                    # Continue processing even if file save fails

                                # build preview payload
                                if "sheets" in preview:
                                    sheets_payload: Dict[str, Any] = {}
                                    for sheet_name, sheet_obj in preview["sheets"].items():
                                        sheets_payload[sheet_name] = {
                                            "columns": sheet_obj.get("columns", []),
                                            "preview": sheet_obj.get("rows", []),
                                        }
                                    preview_payload = {"sheets": sheets_payload}
                                else:
                                    preview_payload = {
                                        "columns": preview.get("columns", []),
                                        "preview": preview.get("rows", []),
                                    }
                                created_files.append({**ff.to_dict(), **preview_payload})
                                processed_files_count += 1
                            except Exception as ie:
                                errors[inner] = {"error": str(ie)}
                else:
                    preview = self._preview_from_bytes(original_name, content)
                    if "sheets" in preview:
                        first_sheet = next(iter(preview["sheets"].values())) if preview["sheets"] else {"shape": {"rows": None, "cols": None}}
                        row_count = first_sheet.get("shape", {}).get("rows")
                        column_count = first_sheet.get("shape", {}).get("cols")
                    else:
                        row_count = preview.get("shape", {}).get("rows")
                        column_count = preview.get("shape", {}).get("cols")

                    ff = FinancialFile(
                        upload_id=upload.upload_id,
                        file_name=os.path.basename(original_name),
                        file_extension=f".{ext}",
                        processed_file_path=None,
                        file_size=int(size_bytes),
                        detected_periodicity=None,
                        user_selected_periodicity=None,
                        file_type="unknown",
                        status="uploaded",
                        column_count=column_count,
                        row_count=row_count,
                        processing_started_at=datetime.utcnow(),
                        processing_completed_at=None,
                    )
                    db.session.add(ff)
                    db.session.flush()

                    # Save file using FilePersistenceManager
                    try:
                        file_manager = FilePersistenceManager()

                        # Save original file
                        file_manager.save_original_file(
                            file_id=str(ff.file_id),
                            upload_id=str(upload.upload_id),
                            file_content=content,
                            filename=original_name,
                            metadata={
                                'file_size': int(size_bytes),
                                'file_type': 'unknown',
                                'column_count': column_count,
                                'row_count': row_count
                            }
                        )

                        # Also save as 'uploaded' stage (same as original)
                        file_manager.save_stage_file(
                            file_id=str(ff.file_id),
                            stage_name='uploaded',
                            data=content,
                            original_filename=original_name
                        )

                        # Update database with file path
                        file_manager.update_db_file_path(
                            str(ff.file_id),
                            'uploaded',
                            file_manager.get_stage_file_path(str(ff.file_id), 'uploaded')
                        )

                        current_app.logger.info(f"[FileUpload] Successfully saved file: {original_name}")
                    except Exception as file_error:
                        current_app.logger.error(f"[FileUpload] Failed to save file {original_name}: {str(file_error)}")
                        # Continue processing even if file save fails

                    # build preview payload
                    if "sheets" in preview:
                        sheets_payload: Dict[str, Any] = {}
                        for sheet_name, sheet_obj in preview["sheets"].items():
                            sheets_payload[sheet_name] = {
                                "columns": sheet_obj.get("columns", []),
                                "preview": sheet_obj.get("rows", []),
                            }
                        preview_payload = {"sheets": sheets_payload}
                    else:
                        preview_payload = {
                            "columns": preview.get("columns", []),
                            "preview": preview.get("rows", []),
                        }
                    created_files.append({**ff.to_dict(), **preview_payload})
                    processed_files_count += 1
            except Exception as e:
                errors[original_name] = {"error": str(e)}

        upload.total_files = total_files_count
        upload.processed_files = processed_files_count
        upload.updated_at = datetime.utcnow()
        db.session.commit()

        return {
            "upload": upload.to_dict(),
            "files": created_files,
            "errors": errors,
        }
