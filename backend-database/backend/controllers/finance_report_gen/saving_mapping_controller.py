from models.finance_report_gen.column_mapping_model import ColumnMapping
from models.lead_model import db
from flask import current_app
from uuid import UUID
from models.finance_report_gen.financial_file_model import FinancialFile
from models.finance_report_gen.standard_column_definitions_model import StandardColumnDefinitions
from utils.finance_file_manager import FilePersistenceManager
import pandas as pd
import os
from pathlib import Path
from config.config import Config

class ColumnMappingController:

    @staticmethod
    def save_column_mapping(data):
        current_app.logger.info(f"[saving_mapping_controller] Starting save_column_mapping with data keys: {list(data.keys()) if data else 'None'}")
        current_app.logger.info(f"[saving_mapping_controller] Data received: {data}")

        try:
            # Checking Data recived or not
            if not data:
                current_app.logger.error("[saving_mapping_controller] No mapping data provided")
                return {"error":"No mapping data provided"},400

            # Checking if file_id and mappings are there
            if 'file_id' not in data or 'mappings' not in data:
                return {"error":"file_id and mappings are required"},400

            file_id = data['file_id']
            mappings=data['mappings']
            complete_mapping_json = data.get('complete_mapping_json', {})

            # Validate File_id
            try:
                UUID(file_id)
            except ValueError:
                return {"error":"Invalid file_id format"},400

            # Referential integrity: ensure FinancialFile exists
            current_app.logger.info(f"[saving_mapping_controller] Looking up FinancialFile with file_id: {file_id}")
            fin_file = FinancialFile.query.filter_by(file_id=file_id).first()
            if not fin_file:
                current_app.logger.error(f"[saving_mapping_controller] FinancialFile not found for file_id: {file_id}")
                return {"error": "financial_file not found for provided file_id"}, 404

            file_type = fin_file.file_type  # may be None/"unknown"
            # Some deployments may not have original_filename column; avoid attribute error
            try:
                original_filename_log = getattr(fin_file, 'original_filename', None)
            except Exception:
                original_filename_log = None
            current_app.logger.info(f"[saving_mapping_controller] Found FinancialFile: file_type={file_type}, original_filename={original_filename_log}, status={fin_file.status}")
            current_app.logger.info(f"[saving_mapping_controller] Current processed_file_path: {fin_file.processed_file_path}")

            # Checking is mapping is list or empty
            current_app.logger.info(f"[saving_mapping_controller] Validating mappings: type={type(mappings)}, count={len(mappings) if isinstance(mappings, list) else 'N/A'}")
            if not isinstance(mappings,list) or len(mappings)==0:
                current_app.logger.error(f"[saving_mapping_controller] Invalid mappings: type={type(mappings)}, count={len(mappings) if isinstance(mappings, list) else 'N/A'}")
                return {"error":"Mappings must be Provided and should be non-empty list"},400


            # Remove any existing mappings for this file to allow replacement behavior
            existing_count = ColumnMapping.query.filter_by(file_id=file_id).count()
            if existing_count > 0:
                ColumnMapping.query.filter_by(file_id=file_id).delete()
                db.session.commit()
                replaced_previous = True
            else:
                replaced_previous = False

            # Preload standard columns and existing mappings for validations
            std_cols = StandardColumnDefinitions.query.filter_by(is_active=True).all()
            # Build applicability map in Python to avoid DB JSON ops
            def _is_applicable(std, ftype):
                if not std.applicable_file_types:
                    return True
                try:
                    return ftype in set(std.applicable_file_types)
                except Exception:
                    return False

            applicable_std = {s.column_name for s in std_cols if _is_applicable(s, file_type)}
            required_std = {s.column_name for s in std_cols if s.is_required and _is_applicable(s, file_type)}

            # Existing mappings for this file (to prevent duplicates and to check required coverage)
            existing = ColumnMapping.query.filter_by(file_id=file_id).all()
            # Only include non-skipped existing mappings in duplicate check
            existing_by_original = {m.original_column_name.lower(): m for m in existing if not m.skipped}
            existing_mapped_names = {m.mapped_column_name for m in existing if m.mapped_column_name and not m.skipped}

            # Business exceptions: mapped_column_name that may allow duplicates for a file
            allowed_duplicate_mapped = {"Notes"}

            seen_originals = set()
            seen_mapped = {}
            saved_mappings = []

            for mapping_data in mappings:

                if 'original_column_name' not in mapping_data:
                    return {"error":"Original Column name is required for each mapping"},400

                # Original column validations
                original = (mapping_data.get('original_column_name') or '').strip()
                if not original:
                    return {"error": "original_column_name cannot be empty"}, 400

                # Check if this column is skipped
                skipped = mapping_data.get('skipped', False)

                # Only check for duplicates among non-skipped columns
                if not skipped:
                    key_original = original.lower()
                    if key_original in seen_originals or key_original in existing_by_original:
                        return {"error": "Duplicate mapping for original_column_name within the same file is not allowed",
                                "original_column_name": original}, 409
                    seen_originals.add(key_original)

                # TODO: Validate original against actual extracted headers if/when headers are stored. Currently
                # we do not have headers persisted; only column_count exists in FinancialFile.

                # Mapped column validations (if provided and not skipped)
                mapped_name = (mapping_data.get('mapped_column_name')).strip() if mapping_data.get('mapped_column_name') else None
                if mapped_name and not skipped:
                    # Must exist in standard_column_definitions and be applicable to file_type
                    # if mapped_name not in applicable_std:
                    #     return {"error": "mapped_column_name is invalid or not applicable for this file type",
                    #             "mapped_column_name": mapped_name, "file_type": file_type}, 400

                    # Prevent duplicate mapped targets per file unless allowed
                    if mapped_name not in allowed_duplicate_mapped:
                        # Check in current payload
                        seen_mapped[mapped_name] = seen_mapped.get(mapped_name, 0) + 1
                        if seen_mapped[mapped_name] > 1:
                            return {"error": "Duplicate mapped_column_name for this file in payload",
                                    "mapped_column_name": mapped_name}, 409
                        # Check against existing DB rows
                        if mapped_name in existing_mapped_names:
                            return {"error": "Duplicate mapped_column_name for this file already exists",
                                    "mapped_column_name": mapped_name}, 409

                column_mapping = ColumnMapping(
                    file_id=file_id,
                    original_column_name=original,
                    mapped_column_name=mapped_name,
                    mapping_confidence=mapping_data.get('mapping_confidence'),
                    auto_suggested=mapping_data.get('auto_suggested', False),
                    is_required=mapping_data.get('is_required', False),
                    skipped=mapping_data.get('skipped', False),
                    mapping_notes=mapping_data.get('mapping_notes'),
                    synonyms_used=mapping_data.get('synonyms_used'),
                    complete_mapping_json=complete_mapping_json
                )

                db.session.add(column_mapping)
                saved_mappings.append(column_mapping)

            # Required standard columns coverage check disabled globally.

            # Commit all mappings
            db.session.commit()
            current_app.logger.info(f"[saving_mapping_controller] Successfully Saved {len(saved_mappings)} Mappings")
            # Process mapped file to produce output and count kept columns
            actual_columns_kept = None
            try:
                processing_result = ColumnMappingController.process_column_mapping_files(file_id, mappings, fin_file)
                if isinstance(processing_result, dict) and processing_result.get('success'):
                    actual_columns_kept = processing_result.get('columns_kept')
                elif processing_result is False:
                    current_app.logger.warning("[saving_mapping_controller] File processing returned False; columns_kept unavailable")
            except Exception as e:
                current_app.logger.warning(f"[saving_mapping_controller] Exception during file processing: {str(e)}")

            # Return message
            result = {
                'message': f'Successfully saved {len(saved_mappings)} column mappings' + (f" and processed {actual_columns_kept} columns" if actual_columns_kept is not None else ''),
                'file_id': file_id,
                'mappings_saved': len(saved_mappings),
                'columns_processed': actual_columns_kept,
            }

            current_app.logger.info(f"[saving_mapping_controller] Returning success response: {result}")

            # If we replaced existing mappings, include a helpful note and flag
            if replaced_previous:
                note = f"Old mappings for file_id {file_id} were replaced with new mappings ({existing_count} old rows deleted)."
                result.setdefault('messages', [])
                result['messages'].append(note)
                result['replaced_previous_mappings'] = True

            return result, 200

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[saving_mapping_controller] Failed to Save Mapping: {str(e)}")
            return {"error": f"Failed to Save  Mappings: {str(e)}"}, 500

    @staticmethod
    def process_column_mapping_files(file_id: str, mappings: list, fin_file: FinancialFile):
        """Process column mapping files using existing FilePersistenceManager methods."""
        current_app.logger.info(f"[ColumnMapping] Starting file processing for file_id: {file_id}")
        try:
            _orig_name = getattr(fin_file, 'original_filename', None) or getattr(fin_file, 'file_name', None)
        except Exception:
            _orig_name = getattr(fin_file, 'file_name', None)
        current_app.logger.info(f"[ColumnMapping] File type: {fin_file.file_type}, Original filename: {_orig_name}")

        try:
            file_manager = FilePersistenceManager()
            current_app.logger.info(f"[ColumnMapping] FilePersistenceManager initialized")

            # Read uploaded file
            current_app.logger.info(f"[ColumnMapping] Looking for uploaded file in stage 'uploaded'")
            uploaded_file_path = file_manager.get_stage_file_path(file_id, 'uploaded')
            if not uploaded_file_path:
                current_app.logger.error(f"[ColumnMapping] No uploaded file found for file_id: {file_id}")
                return False

            current_app.logger.info(f"[ColumnMapping] Found uploaded file: {file_manager.to_relative_path(uploaded_file_path)}")
            current_app.logger.info(f"[ColumnMapping] File size: {os.path.getsize(uploaded_file_path)} bytes")

            # Read and apply mappings
            current_app.logger.info(f"[ColumnMapping] Reading file with extension: {os.path.splitext(uploaded_file_path)[1]}")
            if uploaded_file_path.endswith('.csv'):
                df = pd.read_csv(uploaded_file_path)
                current_app.logger.info(f"[ColumnMapping] Successfully read CSV file, shape: {df.shape}")
            else:
                df = pd.read_excel(uploaded_file_path)
                current_app.logger.info(f"[ColumnMapping] Successfully read Excel file, shape: {df.shape}")

            current_app.logger.info(f"[ColumnMapping] Original columns: {list(df.columns)}")
            current_app.logger.info(f"[ColumnMapping] Processing {len(mappings)} column mappings")

            # Apply column mappings while preserving original order
            applied_mappings = 0
            skipped_mappings = 0
            columns_to_keep = []  # Track which columns to keep in original order
            original_column_order = list(df.columns)  # Store original column order

            # First pass: collect all valid mappings
            valid_mappings = []
            for i, mapping in enumerate(mappings):
                original_col = (mapping.get('original_column_name') or '').strip()
                mapped_col = (mapping.get('mapped_column_name') or '').strip()
                skipped = mapping.get('skipped', False)

                current_app.logger.info(f"[ColumnMapping] Mapping {i+1}: original='{original_col}' -> mapped='{mapped_col}', skipped={skipped}")

                if skipped:
                    current_app.logger.info(f"[ColumnMapping] Skipping mapping {i+1} (marked as skipped)")
                    skipped_mappings += 1
                    continue

                if not mapped_col:
                    current_app.logger.info(f"[ColumnMapping] Skipping mapping {i+1} (no mapped column name)")
                    skipped_mappings += 1
                    continue

                if original_col not in df.columns:
                    current_app.logger.warning(f"[ColumnMapping] Original column '{original_col}' not found in DataFrame, skipping")
                    skipped_mappings += 1
                    continue

                valid_mappings.append((original_col, mapped_col))

            # Second pass: apply mappings in original column order
            for original_col, mapped_col in valid_mappings:
                # Apply the mapping
                df = df.rename(columns={original_col: mapped_col})
                applied_mappings += 1
                current_app.logger.info(f"[ColumnMapping] Successfully applied mapping: '{original_col}' -> '{mapped_col}'")

            # Preserve original column order by reordering based on original positions
            if valid_mappings:
                # Create a mapping from original column names to their positions
                original_positions = {col: idx for idx, col in enumerate(original_column_order)}

                # Get the new column names in the order they appeared in the original file
                ordered_columns = []
                for original_col, mapped_col in valid_mappings:
                    if original_col in original_positions:
                        ordered_columns.append((original_positions[original_col], mapped_col))

                # Sort by original position and extract just the column names
                ordered_columns.sort(key=lambda x: x[0])
                columns_to_keep = [col[1] for col in ordered_columns]

                # Reorder the DataFrame to match original column order
                df = df[columns_to_keep]
                current_app.logger.info(f"[ColumnMapping] Preserved original column order. Final DataFrame shape: {df.shape}")
                current_app.logger.info(f"[ColumnMapping] Final columns in original order: {list(df.columns)}")
            else:
                current_app.logger.warning(f"[ColumnMapping] No valid mappings found! DataFrame will be empty.")
                df = df.iloc[:, :0]  # Create empty DataFrame with no columns

            current_app.logger.info(f"[ColumnMapping] Mapping summary: {applied_mappings} applied, {skipped_mappings} skipped")
            current_app.logger.info(f"[ColumnMapping] Columns to keep: {columns_to_keep}")

            # Save mapped file using existing method
            original_filename = os.path.basename(uploaded_file_path)
            current_app.logger.info(f"[ColumnMapping] Saving mapped file with original filename: {original_filename}")
            current_app.logger.info(f"[ColumnMapping] Target stage: 'mapped', DataFrame shape: {df.shape}")

            mapped_file_path = file_manager.save_stage_file(
                file_id=file_id,
                stage_name='mapped',
                data=df,
                original_filename=original_filename
            )

            if mapped_file_path:
                current_app.logger.info(f"[ColumnMapping] Successfully saved mapped file to: {mapped_file_path}")

                # Update database with new file path
                current_app.logger.info(f"[ColumnMapping] Updating database file path from '{fin_file.processed_file_path}' to '{mapped_file_path}'")
                db_update_result = file_manager.update_db_file_path(file_id, 'mapped', mapped_file_path)

                if db_update_result:
                    current_app.logger.info(f"[ColumnMapping] Database updated successfully. New processed_file_path: {mapped_file_path}")
                    current_app.logger.info(f"[ColumnMapping] File processing completed successfully for file_id: {file_id}")
                    return {'success': True, 'columns_kept': len(columns_to_keep)}
                else:
                    current_app.logger.error(f"[ColumnMapping] Failed to update database file path for file_id: {file_id}")
                    return False
            else:
                current_app.logger.error(f"[ColumnMapping] Failed to save mapped file for file_id: {file_id}")
                return False

        except Exception as e:
            current_app.logger.error(f"[ColumnMapping] File processing failed with exception: {str(e)}")
            current_app.logger.error(f"[ColumnMapping] Exception type: {type(e).__name__}")
            import traceback
            current_app.logger.error(f"[ColumnMapping] Full traceback: {traceback.format_exc()}")
            return False
        


class DeleteFileController:

    @staticmethod
    def delete_file(file_id):
        try:
            UUID(file_id)
        except ValueError:
            current_app.logger.error(f"[saving_mapping_controller] Invalid file_id format file_id:{file_id}")
            return {"error":"Invalid file_id format"},400
    
        try:
            
            fin_file = FinancialFile.query.filter_by(file_id=file_id).first()
            if not fin_file:
                current_app.logger.error(f"[saving_mapping_controller] FinancialFile not found for file_id: {file_id}")
                return {"error": "financial_file not found for provided file_id for Delete"}, 404
        except Exception as e:
            current_app.logger.error(f"[saving_mapping_controller] Error occured while fetching file info from Finacial File {str(e)}")
            return {"error": f"Error while getting file from finance_file table: {str(e)}"}, 500

        try:
            file_name = fin_file.file_name  
            upload_id = fin_file.upload_id  
            processed_file_path = fin_file.processed_file_path
            
            
            finance_storage_path = Config.FINANCE_FILE_STORAGE_PATH
            
            upload_id_prefix = str(upload_id)[:8] if upload_id else ""
            file_id_prefix = str(file_id)[:8]
            
            uploaded_file_path = os.path.join(
                finance_storage_path,
                upload_id_prefix,
                file_id_prefix,
                "stages",
                "uploaded",
                file_name
            )
            
            full_uploaded_path = os.path.join(Config.BASE_DIR,'..',uploaded_file_path)
            
            # Try to remove the uploaded file
            if os.path.exists(full_uploaded_path):
                os.remove(full_uploaded_path)
                current_app.logger.info(f"[saving_mapping_controller] Uploaded file removed successfully from: {uploaded_file_path}")
                
            else:
                current_app.logger.error(f"[saving_mapping_controller] Uploaded file not found at: {uploaded_file_path} Error:{str(e)}")
            
        except Exception as e:
            current_app.logger.error(f"[saving_mapping_controller] Error deleting files: {str(e)}")
            return {"error": f"Failed to delete files: {str(e)}"}, 500
        

        try:
            db.session.delete(fin_file)
            db.session.commit()
            current_app.logger.info(
                f"[saving_mapping_controller] FinancialFile record deleted for file_id: {file_id}"
            )
            return {"message":f"Successfully Removed File"},200
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(
                f"[saving_mapping_controller] DB deletion failed for file_id {file_id}: str{e}"
            )
            return {"error": f"Failed to delete record from DB :{str(e)} "}, 500
