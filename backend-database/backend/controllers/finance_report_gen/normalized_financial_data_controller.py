import os
import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import uuid
import pandas as pd
from flask import current_app

from models.lead_model import db
from models.finance_report_gen.normalized_financial_data_model import NormalizedFinancialData
from models.finance_report_gen.financial_file_model import FinancialFile
from utils.finance_file_manager import FilePersistenceManager


class NormalizedDataController:
    """
    Enhanced controller for financial data normalization using FilePersistenceManager.
    Handles auto-transpose detection, comprehensive logging, and batch processing.
    """

    def __init__(self):
        self.file_manager = FilePersistenceManager()

    @staticmethod
    def _clean_numeric(value: Any) -> Tuple[Optional[Decimal], Optional[str]]:
        """
        Clean numeric strings like "$1,234.50", "1,234", "(1,234)", "12%".
        Returns (decimal_value, detected_type) where detected_type in {'currency','percentage','decimal','integer'} or None
        """
        if value is None:
            return None, None
        if isinstance(value, (int, float, Decimal)):
            try:
                d = Decimal(str(value))
                # Determine integer vs decimal for enum compatibility
                if d == d.to_integral_value():
                    return d, 'integer'
                return d, 'decimal'
            except Exception:
                return None, None

        s = str(value).strip()
        if s == '' or s.lower() in {'nan', 'none', 'null', 'na', 'n/a', 'n.a.', 'missing', '--', '-'}:
            return None, None

        detected: Optional[str] = None
        orig = s

        # Detect percentage
        if s.endswith('%'):
            detected = 'percentage'
            s = s[:-1]

        # Remove currency symbols and spaces
        s = re.sub(r"[\$,€£₹\s]", "", s)
        # Remove comma thousands separators (including Indian format)
        s = s.replace(",", "")
        # Normalize parentheses negatives e.g., (123.45)
        if s.startswith('(') and s.endswith(')'):
            s = '-' + s[1:-1]

        # Strip any stray non-numeric marker characters (e.g., '@', '#', letters)
        # Keep only digits, a leading '-', and dots.
        s = re.sub(r"[^0-9\.-]", "", s)
        # If multiple dots appear (e.g., 110.939.000), treat earlier dots as thousand separators
        if s.count('.') > 1:
            parts = s.split('.')
            s = ''.join(parts[:-1]) + '.' + parts[-1]

        try:
            val = Decimal(s)
            if detected is None:
                if any(sym in str(value) for sym in ('$', '€', '£', '₹')):
                    detected = 'currency'
                else:
                    # Decide integer vs decimal
                    detected = 'integer' if val == val.to_integral_value() else 'decimal'
            return val, detected
        except (InvalidOperation, ValueError):
            return None, None

    @staticmethod
    def _parse_period(label: str, frequency: str) -> Tuple[Optional[date], Optional[date]]:
        """
        Parse a time period label to (start_date, end_date) based on frequency.
        - frequency: 'monthly', 'quarterly', or 'annual'
        Supports labels like 'Jan 2023', 'January 2023', '2023-01', '2023-Q1', '2023'.
        """
        if not label:
            return None, None
        s = str(label).strip()

        # Special handling: TTM (Trailing Twelve Months)
        if s.lower() in {"ttm", "trailing twelve months", "trailing 12 months", "last 12 months"}:
            end = date.today()
            start = end - timedelta(days=365)
            return start, end

        try:
            if frequency == 'quarterly':
                # Try quarter format e.g. '2023-Q1', 'Q1 2023'
                m = re.match(r"^(\d{4})[- ]?Q(\d{1})$", s, re.IGNORECASE)
                if m:
                    year, quarter = int(m.group(1)), int(m.group(2))
                    month = (quarter - 1) * 3 + 1
                    start = date(year, month, 1)
                    if quarter == 4:
                        end = date(year, 12, 31)
                    else:
                        end = date(year, month + 3, 1) - timedelta(days=1)
                    return start, end

                # Try reverse format 'Q1 2023'
                m = re.match(r"^Q(\d{1})[- ]?(\d{4})$", s, re.IGNORECASE)
                if m:
                    quarter, year = int(m.group(1)), int(m.group(2))
                    month = (quarter - 1) * 3 + 1
                    start = date(year, month, 1)
                    if quarter == 4:
                        end = date(year, 12, 31)
                    else:
                        end = date(year, month + 3, 1) - timedelta(days=1)
                return start, end

            elif frequency == 'annual':
                # Try year format '2023', 'FY 2023'
                m = re.match(r"^(?:FY\s*)?(\d{4})$", s, re.IGNORECASE)
                if m:
                    year = int(m.group(1))
                    start = date(year, 1, 1)
                    end = date(year, 12, 31)
                return start, end

            else:
                # monthly default
                # Try formats: 'Jan 2023', 'January 2023', '2023-01' or '2023/01'
                try:
                    dt = datetime.strptime(s, "%b %Y")
                except ValueError:
                    try:
                        dt = datetime.strptime(s, "%B %Y")
                    except ValueError:
                        s2 = s.replace('/', '-')
                        try:
                            dt = datetime.strptime(s2, "%Y-%m")
                        except ValueError:
                            dt = pd.to_datetime(s, errors='coerce')
                            if pd.isna(dt):
                                return None, None

                d0 = date(dt.year, dt.month, 1)
                # end date: last day of month
                if dt.month == 12:
                    d1 = date(dt.year, 12, 31)
                else:
                    d1 = date(dt.year, dt.month + 1, 1) - timedelta(days=1)
                return d0, d1

        except Exception:
            return None, None

    @staticmethod
    def _score_and_flags(val: Decimal, dtype: Optional[str]) -> Tuple[str, Decimal, bool, Optional[str]]:
        """
        Compute validation_status, data_quality_score, outlier_flag, and optional note.
        """
        note = None
        status = 'valid'
        score = Decimal('1.00')
        outlier = False

        # Outlier thresholds (basic heuristic)
        try:
            if dtype == 'percentage':
                if val < Decimal('0') or val > Decimal('100'):
                    status = 'suspicious'
                    score = Decimal('0.50')
                    note = 'percentage outside 0-100'
            else:
                if val.copy_abs() > Decimal('1000000000'):  # 1e9
                    outlier = True
                    status = 'suspicious'
                    score = Decimal('0.50')
                    note = 'absolute value > 1e9'
        except Exception:
            status = 'suspicious'
            score = Decimal('0.50')
            note = 'scoring error'

        return status, score.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP), outlier, note

    def _detect_data_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect the structure of financial data to determine if transpose is needed.
        Returns structure analysis with recommendations.
        """
        current_app.logger.info(
            f"[EnhancedNormalizedData] Analyzing data structure: shape={df.shape}")

        if df.empty:
            return {
                'needs_transpose': False,
                'structure_type': 'empty',
                'reason': 'DataFrame is empty',
                'metrics_in_rows': False,
                'periods_in_columns': False
            }

        # Check if first row contains numeric data (indicating it's data, not headers)
        first_row_numeric = False
        if len(df) > 0:
            first_row_values = df.iloc[0].tolist()
            numeric_count = sum(1 for v in first_row_values if pd.api.types.is_numeric_dtype(type(v)) or
                              (isinstance(v, str) and self._clean_numeric(v)[0] is not None))
            first_row_numeric = numeric_count > len(first_row_values) * 0.5

        # Check if first column contains numeric data (indicating it's data, not labels)
        first_col_numeric = False
        if len(df.columns) > 0:
            first_col_values = df.iloc[:, 0].tolist()
            numeric_count = sum(1 for v in first_col_values if pd.api.types.is_numeric_dtype(type(v)) or
                              (isinstance(v, str) and self._clean_numeric(v)[0] is not None))
            first_col_numeric = numeric_count > len(first_col_values) * 0.5

        current_app.logger.info(
            f"[EnhancedNormalizedData] First row numeric: {first_row_numeric}, First col numeric: {first_col_numeric}")

        # Determine structure
        if first_row_numeric and not first_col_numeric:
            # Data starts from first row, first column contains labels (periods)
            structure_type = 'periods_in_rows_metrics_in_columns'
            needs_transpose = False
            reason = 'Data already in correct format: periods in rows, metrics in columns'
        elif first_col_numeric and not first_row_numeric:
            # Data starts from first column, first row contains labels (metrics)
            structure_type = 'metrics_in_rows_periods_in_columns'
            needs_transpose = True
            reason = 'Data needs transpose: metrics in rows, periods in columns'
        elif first_row_numeric and first_col_numeric:
            # Both first row and column contain numeric data
            structure_type = 'data_matrix'
            needs_transpose = True
            reason = 'Data appears to be a matrix, transposing to standardize format'
        else:
            # Neither first row nor column contains numeric data
            structure_type = 'unknown'
            needs_transpose = False
            reason = 'Structure unclear, proceeding without transpose'

        result = {
            'needs_transpose': needs_transpose,
            'structure_type': structure_type,
            'reason': reason,
            'metrics_in_rows': structure_type in ['metrics_in_rows_periods_in_columns', 'data_matrix'],
            'periods_in_columns': structure_type in ['metrics_in_rows_periods_in_columns', 'data_matrix']
        }

        current_app.logger.info(
            f"[EnhancedNormalizedData] Structure analysis: {result}")
        return result

    def _auto_transpose_if_needed(self, df: pd.DataFrame, force_transpose: bool = False) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Only transpose if user explicitly requests it. No automatic transpose.
        Returns (transposed_df, transpose_info)
        """
        if force_transpose:
            current_app.logger.info(
                f"[EnhancedNormalizedData] Force transpose requested by user")
            df_transposed = df.T.reset_index()
            return df_transposed, {
                'transposed': True,
                'reason': 'User requested transpose',
                'original_shape': df.shape,
                'new_shape': df_transposed.shape
            }
        else:
            current_app.logger.info(
                f"[EnhancedNormalizedData] No transpose requested by user - keeping original structure")
            return df, {
                'transposed': False,
                'reason': 'User did not request transpose',
                'original_shape': df.shape,
                'new_shape': df.shape
            }

    def _detect_date_period_column(self, df: pd.DataFrame) -> Optional[str]:
        """
        Detect which column contains date/period information.
        Returns the column name that contains dates, or None if not found.
        """
        current_app.logger.info(
            f"[EnhancedNormalizedData] Detecting date/period column from columns: {list(df.columns)}")

        date_indicators = ['date', 'period', 'month',
            'year', 'quarter', 'time', 'fiscal', 'financial']

        for col_name in df.columns:
            col_str = str(col_name).lower()

            # Check if column name contains date-related keywords
            if any(indicator in col_str for indicator in date_indicators):
                current_app.logger.info(
                    f"[EnhancedNormalizedData] Found potential date column by name: {col_name}")
                return col_name

            # Check if column contains actual date values
            try:
                sample_values = df[col_name].dropna().head(10)
                if len(sample_values) > 0:
                    # Try to parse as dates
                    date_count = 0
                    for val in sample_values:
                        if pd.api.types.is_datetime64_any_dtype(type(val)):
                            date_count += 1
                        elif isinstance(val, str):
                            try:
                                pd.to_datetime(val, errors='raise')
                                date_count += 1
                            except:
                                pass

                    # If more than 50% of values are dates, consider it a date column
                    if date_count > len(sample_values) * 0.5:
                        current_app.logger.info(
                            f"[EnhancedNormalizedData] Found date column by content: {col_name}")
                        return col_name
            except Exception as e:
                current_app.logger.debug(
                    f"[EnhancedNormalizedData] Error checking column {col_name}: {e}")
                continue

        current_app.logger.warning(
            f"[EnhancedNormalizedData] No date/period column detected")
        return None

    def _extract_metrics_and_periods(self, df: pd.DataFrame, transpose_info: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """
        Extract metric names and period labels from the DataFrame.
        Returns (metric_names, period_labels)
        """
        current_app.logger.info(
            f"[EnhancedNormalizedData] Extracting metrics and periods from DataFrame shape: {df.shape}")

        if df.empty:
            return [], []

        # First, try to detect if there's a date/period column
        date_column = self._detect_date_period_column(df)

        if date_column and not transpose_info['transposed']:
            # We have a date column and no transpose - use the date column for periods
            current_app.logger.info(
                f"[EnhancedNormalizedData] Using detected date column: {date_column}")

            # Get all unique dates from the date column
            period_labels = []
            for date_val in df[date_column].dropna().unique():
                if pd.api.types.is_datetime64_any_dtype(type(date_val)):
                    period_labels.append(date_val.strftime('%Y-%m-%d'))
                else:
                    period_labels.append(str(date_val))

            # All other columns are metrics (excluding the date column)
            metric_names = [col for col in df.columns if col != date_column]

            current_app.logger.info(
                f"[EnhancedNormalizedData] Using date column approach: {len(metric_names)} metrics, {len(period_labels)} periods")

        elif transpose_info['transposed']:
            # After transpose: The structure depends on the original data
            # For your case: first column contains metric names, other columns contain periods
            metric_names = []
            for idx, row in df.iterrows():
                metric_val = str(row.iloc[0]).strip()
                if metric_val and metric_val.lower() not in ['nan', 'none', '']:
                    metric_names.append(metric_val)

            # Other columns (starting from index 1) contain periods
            period_labels = []
            for col_idx in range(1, len(df.columns)):
                col_name = str(df.columns[col_idx]).strip()
                if col_name and col_name.lower() not in ['nan', 'none', '']:
                    period_labels.append(col_name)
        else:
            # No transpose and no date column detected: assume first column contains periods
            metric_names = []
            # Skip first column (assumed to be periods)
            for col_idx in range(1, len(df.columns)):
                col_name = str(df.columns[col_idx]).strip()
                if col_name and col_name.lower() not in ['nan', 'none', '']:
                    metric_names.append(col_name)

            period_labels = []
            for idx, row in df.iterrows():
                period_val = str(row.iloc[0]).strip()
                if period_val and period_val.lower() not in ['nan', 'none', '']:
                    period_labels.append(period_val)

        current_app.logger.info(
            f"[EnhancedNormalizedData] Extracted {len(metric_names)} metrics: {metric_names[:5]}")
        current_app.logger.info(
            f"[EnhancedNormalizedData] Extracted {len(period_labels)} periods: {period_labels[:5]}")

        return metric_names, period_labels

    def _process_financial_data(self, df: pd.DataFrame, file_id: str, frequency: str,
                               metric_names: List[str], period_labels: List[str],
                               transpose_info: Dict[str, Any]) -> Tuple[List[NormalizedFinancialData], List[Dict[str, Any]]]:
        """
        Process financial data and create normalized records.
        Returns (normalized_records, errors)
        """
        current_app.logger.info(
            f"[EnhancedNormalizedData] Processing financial data for file_id: {file_id}")

        normalized_records = []
        errors = []
        processed_count = 0
        error_count = 0

        # Check if we have a date column approach
        date_column = self._detect_date_period_column(df)
        using_date_column = date_column and not transpose_info['transposed']

        if using_date_column:
            # Process using date column approach
            current_app.logger.info(
                f"[EnhancedNormalizedData] Processing using date column: {date_column}")

            for row_idx, row in df.iterrows():
                # Get the date from the date column
                date_val = row[date_column]
                if pd.isna(date_val):
                        continue

                # Convert date to period label
                if pd.api.types.is_datetime64_any_dtype(type(date_val)):
                    period_label = date_val.strftime('%Y-%m-%d')
                else:
                    period_label = str(date_val)

                current_app.logger.debug(
                    f"[EnhancedNormalizedData] Processing row with date: {period_label}")

                    # Parse period
                period_start, period_end = self._parse_period(
                    period_label, frequency)
                if not period_start:
                    error_msg = f"Unrecognized period label: {period_label}"
                    current_app.logger.warning(
                        f"[EnhancedNormalizedData] {error_msg}")
                    errors.append({
                        "metric": "Unknown",
                        "period": period_label,
                        "reason": error_msg,
                        "row_index": row_idx
                    })
                    error_count += 1
                    continue

                # Process each metric for this row (excluding the date column)
                for metric_name in metric_names:
                    if metric_name == date_column:
                        continue  # Skip the date column

                    current_app.logger.debug(
                        f"[EnhancedNormalizedData] Processing metric: {metric_name} for period: {period_label}")

                    # Get value from the metric column
                    value = row[metric_name]

                    if value is None or (isinstance(value, float) and pd.isna(value)):
                        current_app.logger.debug(
                            f"[EnhancedNormalizedData] Skipping empty value for {metric_name} at period {period_label}")
                        continue

                    # Clean and validate value
                    cleaned_value, data_type = self._clean_numeric(value)
                    if cleaned_value is None or data_type is None:
                        error_msg = f"Unparseable value: {value}"
                        current_app.logger.warning(
                            f"[EnhancedNormalizedData] {error_msg}")
                        errors.append({
                                        "metric": metric_name,
                            "period": period_label,
                            "reason": error_msg,
                            "row_index": row_idx
                                    })
                        error_count += 1
                        continue

                                # Normalize percentage to proportion for DB storage
                    stored_value = (cleaned_value / Decimal('100')
                                    ) if data_type == 'percentage' else cleaned_value

                    # Score and flag the value
                    validation_status, quality_score, outlier_flag, note = self._score_and_flags(
                        stored_value, data_type)

                    # Create tags for traceability
                    tags = {
                        "file_id": str(file_id),
                                    "frequency": frequency,
                        "period_label": period_label,
                        "transposed": transpose_info['transposed'],
                        "structure_type": transpose_info.get('structure_type', 'unknown'),
                        "date_column": date_column
                                }
                    if note:
                        tags["validation_note"] = note

                    # Create normalized record
                    normalized_record = NormalizedFinancialData(
                                    file_id=uuid.UUID(file_id),
                                    metric_name=metric_name,
                        period_start_date=period_start,
                        period_end_date=period_end,
                        value=stored_value,
                        original_value=str(value),
                        data_type=data_type,
                        validation_status=validation_status,
                        data_quality_score=quality_score,
                        outlier_flag=outlier_flag,
                        validation_notes=str(tags)
                    )

                    normalized_records.append(normalized_record)
                    processed_count += 1

                    current_app.logger.debug(f"[EnhancedNormalizedData] Successfully processed: {metric_name}={stored_value} for {period_label}")
        else:
            # Process using traditional approach
            current_app.logger.info(f"[EnhancedNormalizedData] Processing using traditional approach")

            for row_idx, period_label in enumerate(period_labels):
                current_app.logger.debug(f"[EnhancedNormalizedData] Processing period: {period_label}")

                # Parse period
                period_start, period_end = self._parse_period(period_label, frequency)
                if not period_start:
                    error_msg = f"Unrecognized period label: {period_label}"
                    current_app.logger.warning(f"[EnhancedNormalizedData] {error_msg}")
                    errors.append({
                        "metric": "Unknown",
                        "period": period_label,
                        "reason": error_msg,
                        "row_index": row_idx
                    })
                    error_count += 1
                    continue

                # Process each metric for this period
                for col_idx, metric_name in enumerate(metric_names):
                    current_app.logger.debug(f"[EnhancedNormalizedData] Processing metric: {metric_name} for period: {period_label}")

                    # Get value based on transpose status
                    if transpose_info['transposed']:
                        # After transpose: periods are rows, metrics are columns
                        value = df.iloc[row_idx, col_idx + 1]  # +1 to skip period column
                    else:
                        # No transpose: periods are rows, metrics are columns
                        value = df.iloc[row_idx, col_idx + 1]  # +1 to skip period column

                    if value is None or (isinstance(value, float) and pd.isna(value)):
                        current_app.logger.debug(f"[EnhancedNormalizedData] Skipping empty value for {metric_name} at period {period_label}")
                        continue

                    # Clean and validate value
                    cleaned_value, data_type = self._clean_numeric(value)
                    if cleaned_value is None or data_type is None:
                        error_msg = f"Unparseable value: {value}"
                        current_app.logger.warning(f"[EnhancedNormalizedData] {error_msg}")
                        errors.append({
                                    "metric": metric_name,
                            "period": period_label,
                            "reason": error_msg,
                            "row_index": row_idx,
                            "column_index": col_idx + 1
                        })
                        error_count += 1
                        continue

                            # Normalize percentage to proportion for DB storage
                    stored_value = (cleaned_value / Decimal('100')) if data_type == 'percentage' else cleaned_value

                    # Score and flag the value
                    validation_status, quality_score, outlier_flag, note = self._score_and_flags(stored_value, data_type)

                    # Create tags for traceability
                    tags = {
                        "file_id": str(file_id),
                                "frequency": frequency,
                        "period_label": period_label,
                        "transposed": transpose_info['transposed'],
                        "structure_type": transpose_info.get('structure_type', 'unknown')
                            }
                    if note:
                        tags["validation_note"] = note

                    # Create normalized record
                    normalized_record = NormalizedFinancialData(
                                file_id=uuid.UUID(file_id),
                                metric_name=metric_name,
                        period_start_date=period_start,
                        period_end_date=period_end,
                        value=stored_value,
                        original_value=str(value),
                        data_type=data_type,
                        validation_status=validation_status,
                        data_quality_score=quality_score,
                        outlier_flag=outlier_flag,
                        validation_notes=str(tags)
                    )

                    normalized_records.append(normalized_record)
                    processed_count += 1

                    current_app.logger.debug(f"[EnhancedNormalizedData] Successfully processed: {metric_name}={stored_value} for {period_label}")

        current_app.logger.info(f"[EnhancedNormalizedData] Data processing completed: {processed_count} records, {error_count} errors")
        return normalized_records, errors

    def normalize_file_stage(self, file_id: str, frequency: str = 'monthly',
                           force_transpose: bool = False) -> Tuple[Dict[str, Any], int]:
        """
        Normalize a single file from mapped stage to normalized stage.
        Returns (payload, status_code)
        """
        current_app.logger.info(f"[EnhancedNormalizedData] Starting normalization for file_id: {file_id}")

        try:
            # Get file info from database
            fin_file = FinancialFile.query.filter_by(file_id=file_id).first()
            if not fin_file:
                current_app.logger.error(f"[EnhancedNormalizedData] FinancialFile not found for file_id: {file_id}")
                return {"error": "File not found"}, 404

            current_app.logger.info(f"[EnhancedNormalizedData] Processing file: {fin_file.file_name}, type: {fin_file.file_type}")

            # Get mapped stage file path
            mapped_file_path = self.file_manager.get_stage_file_path(file_id, 'mapped')
            if not mapped_file_path or not os.path.exists(mapped_file_path):
                current_app.logger.error(f"[EnhancedNormalizedData] Mapped file not found for file_id: {file_id}")
                return {"error": "Mapped file not found"}, 404

            current_app.logger.info(f"[EnhancedNormalizedData] Reading mapped file: {mapped_file_path}")

            # Read file based on extension
            file_extension = os.path.splitext(mapped_file_path)[1].lower()
            if file_extension == '.csv':
                df = pd.read_csv(mapped_file_path)
            elif file_extension in ['.xlsx', '.xls']:
                df = pd.read_excel(mapped_file_path)
            else:
                current_app.logger.error(f"[EnhancedNormalizedData] Unsupported file extension: {file_extension}")
                return {"error": f"Unsupported file extension: {file_extension}"}, 400

            current_app.logger.info(f"[EnhancedNormalizedData] File loaded: shape={df.shape}, columns={list(df.columns)}")

            # Auto-transpose if needed
            df_processed, transpose_info = self._auto_transpose_if_needed(df, force_transpose)
            current_app.logger.info(f"[EnhancedNormalizedData] Transpose info: {transpose_info}")

            # Extract metrics and periods
            metric_names, period_labels = self._extract_metrics_and_periods(df_processed, transpose_info)

            if not metric_names or not period_labels:
                current_app.logger.error(f"[EnhancedNormalizedData] Failed to extract metrics or periods")
                return {"error": "Failed to extract metrics or periods from data"}, 400

            # Process financial data
            normalized_records, errors = self._process_financial_data(
                df_processed, file_id, frequency, metric_names, period_labels, transpose_info
            )

            if not normalized_records:
                current_app.logger.warning(f"[EnhancedNormalizedData] No valid data records found")
                return {"error": "No valid data records found"}, 400

            # Insert records into database
            current_app.logger.info(f"[EnhancedNormalizedData] Inserting {len(normalized_records)} records into database")
            db.session.bulk_save_objects(normalized_records)
            db.session.commit()
            current_app.logger.info(f"[EnhancedNormalizedData] Database insertion completed successfully")

            # Save processed file to normalized stage - PRESERVE COLUMN ORDER
            original_filename = os.path.basename(mapped_file_path)

            # Ensure DataFrame maintains exact column order from mapped file
            if not transpose_info['transposed']:
                # For non-transposed data, preserve original column order
                df_to_save = df_processed.copy()
                current_app.logger.info(f"[EnhancedNormalizedData] Preserving column order: {list(df_to_save.columns)}")
            else:
                # For transposed data, the order is already correct
                df_to_save = df_processed
                current_app.logger.info(f"[EnhancedNormalizedData] Transposed data - column order: {list(df_to_save.columns)}")

            normalized_file_path = self.file_manager.save_stage_file(
                file_id=file_id,
                stage_name='normalized',
                data=df_to_save,
                original_filename=original_filename,
                metadata={
                    'stage': 'normalized',
                    'source_stage': 'mapped',
                    'transpose_info': transpose_info,
                    'records_inserted': len(normalized_records),
                    'errors_count': len(errors),
                    'frequency': frequency,
                    'column_order_preserved': True
                }
            )

            if not normalized_file_path:
                current_app.logger.error(f"[EnhancedNormalizedData] Failed to save normalized stage file")
                return {"error": "Failed to save normalized stage file"}, 500

            current_app.logger.info(f"[EnhancedNormalizedData] Saved normalized file: {normalized_file_path}")

            # Update database file path and status
            db_updated = self.file_manager.update_db_file_path(file_id, 'normalized', normalized_file_path)
            if not db_updated:
                current_app.logger.error(f"[EnhancedNormalizedData] Failed to update database file path")
                return {"error": "Failed to update database file path"}, 500

            current_app.logger.info(f"[EnhancedNormalizedData] Database updated successfully")

            # Prepare response payload
            payload = {
                "success": True,
                "file_id": str(file_id),
                "file_name": fin_file.file_name,
                "records_inserted": len(normalized_records),
                "errors_count": len(errors),
                "errors": errors[:100],  # Limit errors in response
                "transpose_info": transpose_info,
                "normalized_file_path": normalized_file_path,
                "processing_summary": {
                    "total_periods": len(period_labels),
                    "total_metrics": len(metric_names),
                    "data_shape": df_processed.shape,
                    "frequency": frequency,
                    "column_order_preserved": True
                }
            }

            current_app.logger.info(f"[EnhancedNormalizedData] Normalization completed successfully for file_id: {file_id}")
            return payload, 200

        except Exception as e:
            current_app.logger.error(f"[EnhancedNormalizedData] Error during normalization: {str(e)}")
            db.session.rollback()
            return {"error": f"Normalization failed: {str(e)}"}, 500

    def normalize_upload_stage(self, upload_id: str, frequency: str = 'monthly',
                             force_transpose: bool = False) -> Tuple[Dict[str, Any], int]:
        """
        Normalize all files in an upload from mapped stage to normalized stage.
        Returns (payload, status_code)
        """
        current_app.logger.info(f"[EnhancedNormalizedData] Starting batch normalization for upload_id: {upload_id}")

        try:
            # Get all files for this upload
            files = FinancialFile.query.filter_by(upload_id=upload_id).all()
            if not files:
                current_app.logger.error(f"[EnhancedNormalizedData] No files found for upload_id: {upload_id}")
                return {"error": "No files found for upload_id"}, 404

            current_app.logger.info(f"[EnhancedNormalizedData] Found {len(files)} files to process")

            results = []
            total_inserted = 0
            total_errors = 0
            successful_files = 0
            failed_files = 0

            for fin_file in files:
                current_app.logger.info(f"[EnhancedNormalizedData] Processing file: {fin_file.file_name}")

                try:
                    payload, status = self.normalize_file_stage(
                        str(fin_file.file_id), frequency, force_transpose
                    )

                    if status == 200:
                        successful_files += 1
                        total_inserted += payload.get('records_inserted', 0)
                        total_errors += payload.get('errors_count', 0)
                        results.append({
                            "file_id": str(fin_file.file_id),
                            "file_name": fin_file.file_name,
                            "status": "success",
                            "result": payload
                        })
                        current_app.logger.info(f"[EnhancedNormalizedData] File {fin_file.file_name} processed successfully")
                    else:
                        failed_files += 1
                        results.append({
                            "file_id": str(fin_file.file_id),
                            "file_name": fin_file.file_name,
                            "status": "failed",
                            "error": payload.get('error', 'Unknown error')
                        })
                        current_app.logger.error(f"[EnhancedNormalizedData] File {fin_file.file_name} failed: {payload.get('error')}")

                except Exception as e:
                    failed_files += 1
                    error_msg = f"Exception during processing: {str(e)}"
                    current_app.logger.error(f"[EnhancedNormalizedData] Exception processing file {fin_file.file_name}: {error_msg}")
                    results.append({
                        "file_id": str(fin_file.file_id),
                        "file_name": fin_file.file_name,
                        "status": "failed",
                        "error": error_msg
                    })

            # Prepare batch response
            payload = {
                "success": True,
                "upload_id": str(upload_id),
                "total_files": len(files),
                "successful_files": successful_files,
                "failed_files": failed_files,
                "total_records_inserted": total_inserted,
                "total_errors": total_errors,
                "file_results": results,
                "summary": {
                    "success_rate": f"{(successful_files/len(files)*100):.1f}%",
                    "processing_completed": successful_files + failed_files == len(files)
                }
            }

            current_app.logger.info(f"[EnhancedNormalizedData] Batch normalization completed: {successful_files} successful, {failed_files} failed")
            return payload, 200

        except Exception as e:
            current_app.logger.error(f"[EnhancedNormalizedData] Error during batch normalization: {str(e)}")
            return {"error": f"Batch normalization failed: {str(e)}"}, 500

    @staticmethod
    def normalize_and_store(file_id: str, df: pd.DataFrame = None, rows: List[Dict] = None,
                           file_type: str = None, frequency: str = 'monthly',
                           upload_id: str = None, metric_col: str = None) -> Tuple[Dict[str, Any], int]:
        """
        Legacy method for backward compatibility.
        Handles both DataFrame and row-based data insertion.
        """
        try:
            if df is not None and not df.empty:
                # Handle DataFrame input
                controller = NormalizedDataController()
                return controller.normalize_file_stage(
                    file_id=file_id,
                    frequency=frequency,
                    force_transpose=False
                )
            elif rows:
                # Handle row-based input
                normalized_records = []
                for row_data in rows:
                    try:
                        # Parse dates if provided
                        period_start = None
                        period_end = None
                        if 'period_start_date' in row_data:
                            period_start = _parse_date(row_data['period_start_date'])
                        if 'period_end_date' in row_data:
                            period_end = _parse_date(row_data['period_end_date'])

                        # Create normalized record
                        record = NormalizedFinancialData(
                            file_id=uuid.UUID(file_id),
                            metric_name=row_data.get('metric_name', 'Unknown'),
                            period_start_date=period_start,
                            period_end_date=period_end,
                            value=row_data.get('value'),
                            original_value=row_data.get('original_value', ''),
                            data_type=row_data.get('data_type', 'decimal'),
                            validation_status='valid',
                            data_quality_score=1.0,
                            outlier_flag=False
                        )
                        normalized_records.append(record)
                    except Exception as e:
                        current_app.logger.error(f"Error processing row: {e}")
                        continue

                if normalized_records:
                    db.session.bulk_save_objects(normalized_records)
                    db.session.commit()
                    return {"success": True, "records_inserted": len(normalized_records)}, 200
                else:
                    return {"error": "No valid records to insert"}, 400
            else:
                return {"error": "No data provided for insertion"}, 400

        except Exception as e:
            current_app.logger.error(f"Error in normalize_and_store: {str(e)}")
            db.session.rollback()
            return {"error": f"Normalization failed: {str(e)}"}, 500

    @staticmethod
    def _parse_date(value: str):
        """Helper method to parse date strings"""
        if not value:
            return None
        try:
            # Expecting YYYY-MM-DD
            return datetime.strptime(value, "%Y-%m-%d").date()
        except Exception:
            return None
