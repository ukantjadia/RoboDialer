import os
import json
import shutil
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union
from flask import current_app
from uuid import UUID
import uuid
import logging


class FilePersistenceManager:
    """
    Manages file persistence for finance_report_gen feature.
    Handles file storage, versioning, and cleanup for different processing stages.
    """

    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize FilePersistenceManager.

        Args:
            base_path: Base directory for file storage. Defaults to config setting.
        """
        try:
            # Try to get from Flask config if available
            self.base_path = base_path or current_app.config.get(
                "FINANCE_FILE_STORAGE_PATH",
                "data/finance_report_gen/uploads"
            )
            self.retention_days = current_app.config.get("FINANCE_FILE_RETENTION_DAYS", 90)
            self.stages = current_app.config.get(
                "FINANCE_STAGES",
                ['uploaded', 'mapped', 'normalized', 'kpi_calculated', 'processed', 'final']
            )
        except RuntimeError:
            # Fallback when not in Flask context (e.g., testing)
            # Use relative path as fallback when not in Flask context
            self.base_path = base_path or "data/finance_report_gen/uploads"
            self.retention_days = 90
            self.stages = ['uploaded', 'mapped', 'normalized', 'kpi_calculated', 'processed', 'final']

        # Ensure base directory exists
        os.makedirs(self.base_path, exist_ok=True)

        # Create a mapping file to track full UUIDs to short IDs
        self.mapping_file = os.path.join(self.base_path, "uuid_mapping.json")
        self._ensure_mapping_file()

    def _log(self, level: str, message: str):
        """Helper method for logging that works both inside and outside Flask context."""
        try:
            # Try to use Flask logger if available
            if level == 'info':
                current_app.logger.info(message)
            elif level == 'error':
                current_app.logger.error(message)
            elif level == 'warning':
                current_app.logger.warning(message)
            else:
                current_app.logger.info(message)
        except RuntimeError:
            # Fallback to Python logging when not in Flask context
            if level == 'info':
                logging.info(message)
            elif level == 'error':
                logging.error(message)
            elif level == 'warning':
                logging.warning(message)
            else:
                logging.info(message)

    def _ensure_mapping_file(self):
        """Ensure the UUID mapping file exists."""
        if not os.path.exists(self.mapping_file):
            with open(self.mapping_file, 'w') as f:
                json.dump({}, f, indent=2)

    def to_relative_path(self, file_path: str) -> str:
        """
        Convert an absolute path to a repo-relative path rooted at
        'data/finance_report_gen/uploads'. If conversion fails, return
        a normalized forward-slashed path.
        """
        try:
            normalized = os.path.normpath(file_path)
            anchor = os.path.normpath(os.path.join('data', 'finance_report_gen', 'uploads'))
            parts = normalized.split(os.sep)
            anchor_parts = anchor.split(os.sep)
            for i in range(0, len(parts) - len(anchor_parts) + 1):
                if parts[i:i + len(anchor_parts)] == anchor_parts:
                    rel = '/'.join(parts[i:])
                    return rel

            # Try relative to project CWD
            rel_any = os.path.relpath(normalized, start=os.getcwd())
            return rel_any.replace('\\', '/')
        except Exception:
            return str(file_path).replace('\\', '/')

    def _update_uuid_mapping(self, upload_id: str, file_id: str):
        """Update the UUID mapping file with new IDs."""
        try:
            if os.path.exists(self.mapping_file):
                with open(self.mapping_file, 'r') as f:
                    mapping = json.load(f)
            else:
                mapping = {}

            # Store mapping: short_id -> full_id
            short_upload_id = upload_id[:8]
            short_file_id = file_id[:8]

            if short_upload_id not in mapping:
                mapping[short_upload_id] = {}

            mapping[short_upload_id][short_file_id] = {
                'full_upload_id': upload_id,
                'full_file_id': file_id
            }

            with open(self.mapping_file, 'w') as f:
                json.dump(mapping, f, indent=2)

        except Exception as e:
            self._log('error', f"[FileManager] Failed to update UUID mapping: {str(e)}")

    def _get_file_directory(self, upload_id: str, file_id: str) -> str:
        """Get the directory path for a specific file."""
        # Use shorter directory names to avoid Windows path length issues
        # Take first 8 characters of UUIDs to keep paths shorter
        short_upload_id = str(upload_id)[:8]
        short_file_id = str(file_id)[:8]
        return os.path.join(self.base_path, short_upload_id, short_file_id)

    def _get_stage_directory(self, upload_id: str, file_id: str, stage: str) -> str:
        """Get the directory path for a specific stage."""
        file_dir = self._get_file_directory(upload_id, file_id)
        return os.path.join(file_dir, "stages", stage)

    def _get_original_directory(self, upload_id: str, file_id: str) -> str:
        """Get the directory path for original files."""
        file_dir = self._get_file_directory(upload_id, file_id)
        return os.path.join(file_dir, "original")

    def _get_metadata_directory(self, upload_id: str, file_id: str) -> str:
        """Get the directory path for metadata files."""
        file_dir = self._get_file_directory(upload_id, file_id)
        return os.path.join(file_dir, "metadata")

    def save_metadata_json(self, file_id: str, filename: str, payload: Dict[str, Any]) -> str:
        """
        Save a JSON payload into the file's metadata directory and return relative path.
        """
        try:
            file_info = self.get_file_metadata(file_id)
            if not file_info:
                raise ValueError(f"File metadata not found for file_id: {file_id}")

            upload_id = file_info['upload_id']
            metadata_dir = self._get_metadata_directory(upload_id, file_id)
            os.makedirs(metadata_dir, exist_ok=True)

            json_path = os.path.join(metadata_dir, filename)
            with open(json_path, 'w') as f:
                json.dump(payload, f, indent=2)

            self._log('info', f"[FileManager] Saved metadata JSON: {self.to_relative_path(json_path)}")
            return self.to_relative_path(json_path)
        except Exception as e:
            self._log('error', f"[FileManager] Failed to save metadata JSON: {str(e)}")
            raise

    def save_original_file(
        self,
        file_id: str,
        upload_id: str,
        file_content: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save the original file uploaded by user.

        Args:
            file_id: UUID of the file
            upload_id: UUID of the upload
            file_content: File content as bytes
            filename: Original filename
            metadata: Additional metadata to store

        Returns:
            Path to the saved file
        """
        try:
            # Create directories
            original_dir = self._get_original_directory(upload_id, file_id)
            metadata_dir = self._get_metadata_directory(upload_id, file_id)
            os.makedirs(original_dir, exist_ok=True)
            os.makedirs(metadata_dir, exist_ok=True)

            # Save original file
            file_path = os.path.join(original_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(file_content)

            # Save file info metadata
            file_info = {
                'file_id': str(file_id),
                'upload_id': str(upload_id),
                'original_filename': filename,
                'file_size': len(file_content),
                'upload_date': datetime.utcnow().isoformat(),
                'file_extension': os.path.splitext(filename)[1].lower(),
                **(metadata or {})
            }

            # Update UUID mapping
            self._update_uuid_mapping(str(upload_id), str(file_id))

            file_info_path = os.path.join(metadata_dir, 'file_info.json')
            with open(file_info_path, 'w') as f:
                json.dump(file_info, f, indent=2)

            # Initialize processing history (store relative path)
            processing_history = {
                'file_id': str(file_id),
                'upload_id': str(upload_id),
                'stages': {
                    'original': {
                        'timestamp': datetime.utcnow().isoformat(),
                        'status': 'completed',
                        'file_path': self.to_relative_path(file_path),
                        'file_size': len(file_content)
                    }
                }
            }

            history_path = os.path.join(metadata_dir, 'processing_history.json')
            with open(history_path, 'w') as f:
                json.dump(processing_history, f, indent=2)

            self._log('info', f"[FileManager] Saved original file: {self.to_relative_path(file_path)}")
            return self.to_relative_path(file_path)

        except Exception as e:
            self._log('error', f"[FileManager] Failed to save original file: {str(e)}")
            raise

    def save_stage_file(
        self,
        file_id: str,
        stage_name: str,
        data: Union[pd.DataFrame, bytes],
        original_filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save file at specific processing stage.

        Args:
            file_id: UUID of the file
            stage_name: Name of the processing stage
            data: Data to save (DataFrame or bytes)
            original_filename: Original filename to preserve
            metadata: Additional metadata for this stage

        Returns:
            Path to the saved file
        """
        try:
            # Get file info to determine upload_id
            file_info = self.get_file_metadata(file_id)
            if not file_info:
                raise ValueError(f"File metadata not found for file_id: {file_id}")

            upload_id = file_info['upload_id']

            # Create stage directory
            stage_dir = self._get_stage_directory(upload_id, file_id, stage_name)
            os.makedirs(stage_dir, exist_ok=True)

            # Determine file path based on original filename
            file_path = os.path.join(stage_dir, original_filename)

            # Enforce CSV for KPI stage regardless of provided extension
            if stage_name == 'kpi_calculated':
                root, _ext = os.path.splitext(file_path)
                file_path = root + '.csv'

            # Save data based on type
            if isinstance(data, pd.DataFrame):
                # Save DataFrame based on file extension
                ext = os.path.splitext(original_filename)[1].lower()
                if stage_name == 'kpi_calculated':
                    # Force CSV for KPI stage
                    data.to_csv(file_path, index=False)
                elif ext == '.csv':
                    data.to_csv(file_path, index=False)
                elif ext in ['.xlsx', '.xls']:
                    data.to_excel(file_path, index=False)
                else:
                    # Default to CSV
                    file_path = os.path.splitext(file_path)[0] + '.csv'
                    data.to_csv(file_path, index=False)
            else:
                # Save bytes directly
                with open(file_path, 'wb') as f:
                    f.write(data)

            # Update processing history (store relative path)
            self._update_processing_history(
                file_id,
                stage_name,
                self.to_relative_path(file_path),
                metadata or {}
            )

            self._log('info', f"[FileManager] Saved stage file: {self.to_relative_path(file_path)}")
            return self.to_relative_path(file_path)

        except Exception as e:
            self._log('error', f"[FileManager] Failed to save stage file: {str(e)}")
            raise

    def get_stage_file_path(self, file_id: str, stage_name: str) -> Optional[str]:
        """
        Get path to file at specific stage.

        Args:
            file_id: UUID of the file
            stage_name: Name of the processing stage

        Returns:
            Path to the file if it exists, None otherwise
        """
        try:
            # Get file info to determine upload_id
            file_info = self.get_file_metadata(file_id)
            if not file_info:
                return None

            upload_id = file_info['upload_id']
            stage_dir = self._get_stage_directory(upload_id, file_id, stage_name)

            # Check if stage directory exists
            if not os.path.exists(stage_dir):
                return None

            # Look for files in stage directory
            files = os.listdir(stage_dir)
            if not files:
                return None

            # Return first file found (should be only one per stage)
            return os.path.join(stage_dir, files[0])

        except Exception as e:
            self._log('error', f"[FileManager] Failed to get stage file path: {str(e)}")
            return None

    def get_latest_stage_file(self, file_id: str) -> Optional[str]:
        """
        Get path to the most recent processed file.

        Args:
            file_id: UUID of the file

        Returns:
            Path to the latest stage file if it exists, None otherwise
        """
        try:
            # Get file info to determine upload_id
            file_info = self.get_file_metadata(file_id)
            if not file_info:
                return None

            upload_id = file_info['upload_id']

            # Check stages in reverse order (latest first)
            for stage in reversed(self.stages):
                file_path = self.get_stage_file_path(file_id, stage)
                if file_path and os.path.exists(file_path):
                    return file_path

            return None

        except Exception as e:
            self._log('error', f"[FileManager] Failed to get latest stage file: {str(e)}")
            return None

    def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get file metadata.

        Args:
            file_id: UUID of the file

        Returns:
            File metadata dictionary if found, None otherwise
        """
        try:
            # Search for file_info.json in upload directories
            # Use shorter file_id for directory search
            short_file_id = str(file_id)[:8]

            for upload_dir in os.listdir(self.base_path):
                upload_path = os.path.join(self.base_path, upload_dir)
                if not os.path.isdir(upload_path):
                    continue

                # Check if file_id directory exists
                file_dir = os.path.join(upload_path, short_file_id)
                if not os.path.exists(file_dir):
                    continue

                # Look for file_info.json
                metadata_dir = os.path.join(file_dir, "metadata")
                file_info_path = os.path.join(metadata_dir, "file_info.json")

                if os.path.exists(file_info_path):
                    with open(file_info_path, 'r') as f:
                        return json.load(f)

            return None

        except Exception as e:
            self._log('error', f"[FileManager] Failed to get file metadata: {str(e)}")
            return None

    def update_db_file_path(self, file_id: str, stage_name: str, file_path: str) -> bool:
        """
        Update processed_file_path in database.

        Args:
            file_id: UUID of the file
            stage_name: Name of the processing stage
            file_path: Path to the file

        Returns:
            True if successful, False otherwise
        """
        try:
            from models.finance_report_gen.financial_file_model import FinancialFile
            from models.lead_model import db

            # Update database record
            fin_file = FinancialFile.query.filter_by(file_id=file_id).first()
            if fin_file:
                fin_file.processed_file_path = self.to_relative_path(file_path)
                fin_file.status = stage_name
                fin_file.updated_at = datetime.utcnow()
                db.session.commit()
                self._log('info', f"[FileManager] Updated DB file path: {file_path}")
                return True

            return False

        except Exception as e:
            self._log('error', f"[FileManager] Failed to update DB file path: {str(e)}")
            return False

    def _update_processing_history(
        self,
        file_id: str,
        stage_name: str,
        file_path: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Update processing history for a stage."""
        try:
            # Get file info to determine upload_id
            file_info = self.get_file_metadata(file_id)
            if not file_info:
                return

            upload_id = file_info['upload_id']
            metadata_dir = self._get_metadata_directory(upload_id, file_id)
            history_path = os.path.join(metadata_dir, 'processing_history.json')

            # Read existing history
            if os.path.exists(history_path):
                with open(history_path, 'r') as f:
                    history = json.load(f)
            else:
                history = {
                    'file_id': str(file_id),
                    'upload_id': str(upload_id),
                    'stages': {}
                }

            # Update stage info
            history['stages'][stage_name] = {
                'timestamp': datetime.utcnow().isoformat(),
                'status': 'completed',
                'file_path': file_path,  # This is already a relative path
                'file_size': os.path.getsize(os.path.join(self.base_path, file_path)) if os.path.exists(os.path.join(self.base_path, file_path)) else 0,
                **metadata
            }

            # Write updated history
            with open(history_path, 'w') as f:
                json.dump(history, f, indent=2)

        except Exception as e:
            self._log('error', f"[FileManager] Failed to update processing history: {str(e)}")

    def cleanup_old_files(self, days_old: Optional[int] = None) -> int:
        """
        Clean up files older than specified days.

        Args:
            days_old: Number of days to keep files. Defaults to retention_days.

        Returns:
            Number of files cleaned up
        """
        try:
            days_old = days_old or self.retention_days
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cleaned_count = 0

            for upload_dir in os.listdir(self.base_path):
                upload_path = os.path.join(self.base_path, upload_dir)
                if not os.path.isdir(upload_path):
                    continue

                # Check upload metadata for date
                upload_metadata_path = os.path.join(upload_path, 'upload_metadata.json')
                if os.path.exists(upload_metadata_path):
                    with open(upload_metadata_path, 'r') as f:
                        upload_metadata = json.load(f)

                    upload_date_str = upload_metadata.get('upload_date')
                    if upload_date_str:
                        try:
                            upload_date = datetime.fromisoformat(upload_date_str.replace('Z', '+00:00'))
                            if upload_date < cutoff_date:
                                # Remove entire upload directory
                                shutil.rmtree(upload_path)
                                cleaned_count += 1
                                self._log('info', f"[FileManager] Cleaned up old upload: {upload_dir}")
                        except Exception:
                            # If date parsing fails, skip this directory
                            continue

            self._log('info', f"[FileManager] Cleanup completed: {cleaned_count} uploads removed")
            return cleaned_count

        except Exception as e:
            self._log('error', f"[FileManager] Failed to cleanup old files: {str(e)}")
            return 0

    def process_normalization_stage(
        self,
        *,
        file_id: str,
        frequency: str = 'monthly',
        transpose: bool = False
    ) -> Optional[tuple]:
        """
        Normalize the mapped-stage file and persist a new file in the 'normalized' stage.

        Behavior:
        - Reads strictly from the 'mapped' stage
        - Keeps original filename and file format
        - Saves a new file into the 'normalized' stage
        - Updates DB processed_file_path and status to 'normalized'
        - Returns (payload, status_code, normalized_file_path) on success; None on failure
        """
        try:
            from models.finance_report_gen.financial_file_model import FinancialFile
            from controllers.finance_report_gen.normalized_financial_data_controller import NormalizedDataController
            from models.lead_model import db

            # Resolve DB record for additional metadata
            fin_file = FinancialFile.query.filter_by(file_id=file_id).first()
            if not fin_file:
                self._log('error', f"[FileManager][Normalize] FinancialFile not found for file_id={file_id}")
                return None

            self._log('info', f"[FileManager][Normalize] Starting normalization for file_id={file_id}, file_type={fin_file.file_type}")

            # Ensure mapped stage file exists and is readable
            mapped_path = self.get_stage_file_path(file_id, 'mapped')
            if not mapped_path or not os.path.exists(mapped_path):
                self._log('error', f"[FileManager][Normalize] Mapped file not found for file_id={file_id}")
                return None

            try:
                mapped_size = os.path.getsize(mapped_path)
            except Exception:
                mapped_size = 0
            self._log('info', f"[FileManager][Normalize] Using mapped file: path={mapped_path}, size={mapped_size} bytes")

            # Read DataFrame without changing format
            ext = os.path.splitext(mapped_path)[1].lower()
            self._log('info', f"[FileManager][Normalize] Reading file extension: {ext}")
            if ext == '.csv':
                df = pd.read_csv(mapped_path)
            elif ext in ['.xlsx', '.xls']:
                df = pd.read_excel(mapped_path)
            else:
                # Unsupported extension for DataFrame read; try bytes copy only but still attempt DB normalization
                self._log('warning', f"[FileManager][Normalize] Unsupported extension for DF read: {ext}. Proceeding with bytes copy and no DF-based normalization.")
                df = None

            if df is not None:
                self._log('info', f"[FileManager][Normalize] DataFrame loaded: shape={df.shape}")

            # Insert normalized rows into DB using existing controller logic
            payload, status = NormalizedDataController.normalize_and_store(
                file_id=str(fin_file.file_id),
                df=df,
                rows=None,
                file_type=fin_file.file_type,
                frequency=frequency,
                upload_id=str(fin_file.upload_id) if getattr(fin_file, 'upload_id', None) else None,
                metric_col=None
            )

            if status != 200:
                self._log('error', f"[FileManager][Normalize] DB normalization failed for file_id={file_id}: status={status}, payload={payload}")
                db.session.rollback()
                return payload, status, None

            self._log('info', f"[FileManager][Normalize] DB normalization inserted={payload.get('inserted')}, skipped={payload.get('skipped')} for file_id={file_id}")

            # Persist a new file in 'normalized' stage with same filename and format
            original_filename = os.path.basename(mapped_path)
            self._log('info', f"[FileManager][Normalize] Saving normalized stage file with original filename: {original_filename}")

            # Save without altering format; if df exists use it, else copy bytes
            if df is not None:
                normalized_path = self.save_stage_file(
                    file_id=file_id,
                    stage_name='normalized',
                    data=df,
                    original_filename=original_filename,
                    metadata={
                        'stage': 'normalized',
                        'source_stage_path': mapped_path,
                        'rows_inserted': payload.get('inserted'),
                        'rows_skipped': payload.get('skipped')
                    }
                )
            else:
                with open(mapped_path, 'rb') as f:
                    file_bytes = f.read()
                normalized_path = self.save_stage_file(
                    file_id=file_id,
                    stage_name='normalized',
                    data=file_bytes,
                    original_filename=original_filename,
                    metadata={
                        'stage': 'normalized',
                        'source_stage_path': mapped_path,
                        'rows_inserted': payload.get('inserted'),
                        'rows_skipped': payload.get('skipped')
                    }
                )

            self._log('info', f"[FileManager][Normalize] Saved normalized file: {normalized_path}")

            # Update DB file path and status
            old_path = fin_file.processed_file_path
            old_status = fin_file.status
            updated = self.update_db_file_path(file_id=file_id, stage_name='normalized', file_path=normalized_path)
            if not updated:
                self._log('error', f"[FileManager][Normalize] Failed to update DB processed_file_path for file_id={file_id}")
                db.session.rollback()
                return {"error": "Failed to update DB processed_file_path"}, 500, None

            # Refresh fin_file to log new values
            try:
                db.session.refresh(fin_file)
            except Exception:
                pass
            self._log('info', f"[FileManager][Normalize] DB updated: processed_file_path: '{old_path}' -> '{fin_file.processed_file_path}', status: '{old_status}' -> '{fin_file.status}'")

            self._log('info', f"[FileManager][Normalize] Completed normalization for file_id={file_id}")
            return payload, 200, normalized_path

        except Exception as e:
            # Rollback DB only. Do not delete or modify any files.
            try:
                from models.lead_model import db
                db.session.rollback()
            except Exception:
                pass
            self._log('error', f"[FileManager][Normalize] Exception during normalization for file_id={file_id}: {str(e)}")
            import traceback
            self._log('error', f"[FileManager][Normalize] Traceback: {traceback.format_exc()}")
            return {"error": str(e)}, 500, None
