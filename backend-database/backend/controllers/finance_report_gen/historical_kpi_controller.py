import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date, timedelta
from flask import current_app
from models.lead_model import db
from models.finance_report_gen.kpi_historical_data_model import KPIHistoricalData
from models.finance_report_gen.data_granularity_model import DataGranularity
from models.finance_report_gen.normalized_financial_data_model import NormalizedFinancialData
from models.finance_report_gen.kpi_definitions_model import KPIDefinitions
from models.finance_report_gen.financial_file_model import FinancialFile
from controllers.finance_report_gen.finance_kpi_controller import KPICalculation
from controllers.finance_report_gen.granularity_detector import GranularityDetector
from controllers.finance_report_gen.formula_engine import SimpleFormulaEngine
from utils.finance_file_manager import FilePersistenceManager
import json
import uuid
import csv
import os

class HistoricalKPIController:
    """
    Controller for calculating and managing historical KPI data with period-based filtering
    """

    def __init__(self):
        self.kpi_calculator = KPICalculation()
        self.granularity_detector = GranularityDetector()
        self.formula_engine = SimpleFormulaEngine()
        self.file_manager = FilePersistenceManager()

    def calculate_historical_kpis(self, upload_id: str, period_type: str = None) -> Dict[str, Any]:
        """
        Calculate KPIs for all periods and store historically
        """
        try:
            current_app.logger.info(f"[HistoricalKPIController] Starting historical KPI calculation for upload_id: {upload_id}")

            # Get files for this upload
            files = FinancialFile.query.filter_by(upload_id=upload_id).all()
            if not files:
                return {
                    "success": False,
                    "error": "No files found for upload_id",
                    "upload_id": upload_id
                }

            # NEW: Delete existing historical KPI data for this upload_id first
            self._delete_existing_historical_kpis(upload_id)

            # Detect granularity for the first file (assuming all files have same granularity)
            granularity_info = self._detect_and_store_granularity(upload_id, files[0].file_id)
            if not granularity_info:
                return {
                    "success": False,
                    "error": "Failed to detect data granularity",
                    "upload_id": upload_id
                }

            detected_granularity = granularity_info['granularity']
            suggested_periods = granularity_info['suggested_chart_periods']

            # NEW: Calculate KPIs for ALL period types (monthly, quarterly, yearly)
            all_historical_kpis = []
            total_calculated = 0
            total_failed = 0
            period_type_results = {}

            # Calculate for each period type
            for period_type_to_calculate in ['monthly', 'quarterly', 'yearly']:
                current_app.logger.info(f"[HistoricalKPIController] Calculating KPIs for period_type: {period_type_to_calculate}")

                period_type_calculated = 0
                period_type_failed = 0

                for file_obj in files:
                    try:
                        file_historical_kpis = self._calculate_file_historical_kpis(
                            upload_id, file_obj.file_id, period_type_to_calculate
                        )
                        all_historical_kpis.extend(file_historical_kpis)
                        period_type_calculated += len([kpi for kpi in file_historical_kpis if kpi.get('calculation_status') == 'calculated'])
                        period_type_failed += len([kpi for kpi in file_historical_kpis if kpi.get('calculation_status') == 'failed'])

                    except Exception as e:
                        current_app.logger.error(f"[HistoricalKPIController] Error processing file {file_obj.file_id} for {period_type_to_calculate}: {str(e)}")
                        period_type_failed += 1

                period_type_results[period_type_to_calculate] = {
                    'calculated': period_type_calculated,
                    'failed': period_type_failed
                }
                total_calculated += period_type_calculated
                total_failed += period_type_failed

            # Store historical KPIs in database
            stored_count = self._store_historical_kpis(all_historical_kpis)

            result = {
                "success": True,
                "upload_id": upload_id,
                "granularity_info": granularity_info,
                "period_type_results": period_type_results,
                "total_files_processed": len(files),
                "total_kpis_calculated": total_calculated,
                "total_kpis_failed": total_failed,
                "historical_kpis_stored": stored_count,
                "suggested_chart_periods": suggested_periods
            }

            # NEW: Save results to CSV and JSON files
            self._save_kpi_results_to_files(upload_id, result, all_historical_kpis)

            current_app.logger.info(f"[HistoricalKPIController] Historical KPI calculation completed: {total_calculated} calculated, {total_failed} failed")
            return result

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error in calculate_historical_kpis: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "upload_id": upload_id
            }

    def get_kpi_trends(self, upload_id: str, kpi_names: List[str],
                      period_type: str, periods: int = 12) -> Dict[str, Any]:
        """
        Get KPI trends for charting
        Returns: {
            'kpi_name': {
                'values': [1.2, 1.5, 1.8, ...],
                'periods': ['2023-Q1', '2023-Q2', ...],
                'chart_type': 'line'
            }
        }
        """
        try:
            current_app.logger.info(f"[HistoricalKPIController] Getting KPI trends for {len(kpi_names)} KPIs")
            current_app.logger.info(f"[HistoricalKPIController] Requested KPI names: {kpi_names}")

            # First, get all available KPI names for this upload to find exact matches
            available_kpis = db.session.query(KPIHistoricalData.kpi_name).filter(
                KPIHistoricalData.upload_id == upload_id,
                KPIHistoricalData.period_type == period_type,
                KPIHistoricalData.calculation_status == 'calculated'
            ).distinct().all()

            available_kpi_names = [kpi[0] for kpi in available_kpis]
            current_app.logger.info(f"[HistoricalKPIController] Available KPI names in DB: {available_kpi_names}")

            # Find exact matches for requested KPIs (handle spaces and case sensitivity)
            matched_kpi_names = []
            for requested_kpi in kpi_names:
                # Try exact match first
                if requested_kpi in available_kpi_names:
                    matched_kpi_names.append(requested_kpi)
                else:
                    # Try case-insensitive match
                    for available_kpi in available_kpi_names:
                        if requested_kpi.lower().strip() == available_kpi.lower().strip():
                            matched_kpi_names.append(available_kpi)
                            break
                    else:
                        # Try partial match (in case of extra spaces or encoding issues)
                        for available_kpi in available_kpi_names:
                            if requested_kpi.replace(' ', '').lower() == available_kpi.replace(' ', '').lower():
                                matched_kpi_names.append(available_kpi)
                                break

            current_app.logger.info(f"[HistoricalKPIController] Matched KPI names: {matched_kpi_names}")

            if not matched_kpi_names:
                return {
                    "success": False,
                    "error": f"No matching KPIs found. Requested: {kpi_names}, Available: {available_kpi_names}",
                    "upload_id": upload_id,
                    "kpi_trends": {},
                    "available_kpis": available_kpi_names
                }

            # Query historical KPI data with matched names
            query = KPIHistoricalData.query.filter(
                KPIHistoricalData.upload_id == upload_id,
                KPIHistoricalData.kpi_name.in_(matched_kpi_names),
                KPIHistoricalData.period_type == period_type,
                KPIHistoricalData.calculation_status == 'calculated'
            ).order_by(KPIHistoricalData.period_start_date.desc()).limit(periods * len(matched_kpi_names))

            historical_data = query.all()
            current_app.logger.info(f"[HistoricalKPIController] Found {len(historical_data)} historical records")

            if not historical_data:
                return {
                    "success": False,
                    "error": "No historical KPI data found for matched KPIs",
                    "upload_id": upload_id,
                    "kpi_trends": {},
                    "matched_kpis": matched_kpi_names
                }

            # Group data by KPI name
            kpi_trends = {}
            for requested_kpi in kpi_names:
                # Find the matched KPI name for this request
                matched_kpi = None
                for available_kpi in matched_kpi_names:
                    if (requested_kpi.lower().strip() == available_kpi.lower().strip() or
                        requested_kpi.replace(' ', '').lower() == available_kpi.replace(' ', '').lower()):
                        matched_kpi = available_kpi
                        break

                if matched_kpi:
                    kpi_data = [kpi for kpi in historical_data if kpi.kpi_name == matched_kpi]

                    if kpi_data:
                        # Sort by period start date (ascending for chart)
                        kpi_data.sort(key=lambda x: x.period_start_date)

                        values = [float(kpi.kpi_value) if kpi.kpi_value else 0 for kpi in kpi_data]
                        periods_list = [kpi.period_label or f"{kpi.period_start_date}" for kpi in kpi_data]

                        # Determine chart type based on KPI category
                        chart_type = self._determine_chart_type(kpi_data[0].kpi_category)

                        kpi_trends[requested_kpi] = {
                            'values': values,
                            'periods': periods_list,
                            'chart_type': chart_type,
                            'kpi_category': kpi_data[0].kpi_category,
                            'data_points': len(values),
                            'latest_value': values[-1] if values else None,
                            'period_type': period_type,
                            'matched_kpi_name': matched_kpi  # Include the actual matched name
                        }
                    else:
                        kpi_trends[requested_kpi] = {
                            'values': [],
                            'periods': [],
                            'chart_type': 'line',
                            'kpi_category': 'Unknown',
                            'data_points': 0,
                            'latest_value': None,
                            'period_type': period_type,
                            'error': 'No data available for matched KPI',
                            'matched_kpi_name': matched_kpi
                        }
                else:
                    kpi_trends[requested_kpi] = {
                        'values': [],
                        'periods': [],
                        'chart_type': 'line',
                        'kpi_category': 'Unknown',
                        'data_points': 0,
                        'latest_value': None,
                        'period_type': period_type,
                        'error': 'No matching KPI found in database',
                        'matched_kpi_name': None
                    }

            return {
                "success": True,
                "upload_id": upload_id,
                "period_type": period_type,
                "requested_periods": periods,
                "kpi_trends": kpi_trends,
                "total_kpis_found": len([kpi for kpi in kpi_trends.values() if kpi['data_points'] > 0]),
                "available_kpis": available_kpi_names,
                "matched_kpis": matched_kpi_names
            }

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error getting KPI trends: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "upload_id": upload_id,
                "kpi_trends": {}
            }

    def get_period_division_suggestions(self, upload_id: str) -> Dict[str, Any]:
        """
        Get suggested period divisions based on data
        """
        try:
            # Get granularity info from database
            granularity_record = DataGranularity.query.filter_by(upload_id=upload_id).first()

            if not granularity_record:
                return {
                    "success": False,
                    "error": "No granularity data found. Please run KPI calculation first.",
                    "upload_id": upload_id
                }

            # Parse suggested chart periods from JSON
            suggested_periods = []
            if granularity_record.suggested_chart_periods:
                try:
                    suggested_periods = json.loads(granularity_record.suggested_chart_periods)
                except:
                    suggested_periods = ['monthly', 'quarterly', 'yearly']

            return {
                "success": True,
                "upload_id": upload_id,
                "detected_granularity": granularity_record.detected_granularity,
                "confidence_score": float(granularity_record.confidence_score) if granularity_record.confidence_score else None,
                "period_count": granularity_record.period_count,
                "date_range": {
                    "start": granularity_record.date_range_start.isoformat() if granularity_record.date_range_start else None,
                    "end": granularity_record.date_range_end.isoformat() if granularity_record.date_range_end else None
                },
                "suggested_chart_periods": suggested_periods,
                "auto_detection_notes": granularity_record.auto_detection_notes
            }

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error getting period suggestions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "upload_id": upload_id
            }

    def calculate_custom_kpi(self, upload_id: str, formula: str,
                           period_type: str = 'monthly') -> Dict[str, Any]:
        """
        Calculate custom KPI with formula
        """
        try:
            current_app.logger.info(f"[HistoricalKPIController] Calculating custom KPI: {formula}")

            # Get files for this upload
            files = FinancialFile.query.filter_by(upload_id=upload_id).all()
            if not files:
                return {
                    "success": False,
                    "error": "No files found for upload_id",
                    "upload_id": upload_id
                }

            # Read normalized data from first file
            file_obj = files[0]
            normalized_path = self.file_manager.get_stage_file_path(str(file_obj.file_id), 'normalized')

            if not normalized_path:
                return {
                    "success": False,
                    "error": "Normalized data not found",
                    "upload_id": upload_id
                }

            # Read data
            import pandas as pd
            data = pd.read_csv(normalized_path) if normalized_path.endswith('.csv') else pd.read_excel(normalized_path)

            # Validate formula
            validation_result = self.formula_engine.validate_formula(formula, data.columns.tolist())
            if not validation_result['valid']:
                return {
                    "success": False,
                    "error": validation_result['error'],
                    "upload_id": upload_id,
                    "validation_result": validation_result
                }

            # Calculate custom KPI
            result = self.formula_engine.calculate_custom_kpi(formula, data)

            if result is None:
                return {
                    "success": False,
                    "error": "Formula calculation returned no result",
                    "upload_id": upload_id,
                    "formula": formula
                }

            return {
                "success": True,
                "upload_id": upload_id,
                "formula": formula,
                "result": result,
                "period_type": period_type,
                "validation_result": validation_result
            }

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error calculating custom KPI: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "upload_id": upload_id,
                "formula": formula
            }

    def _detect_and_store_granularity(self, upload_id: str, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Detect granularity and store in database
        """
        try:
            # Read normalized data to get period labels
            normalized_path = self.file_manager.get_stage_file_path(str(file_id), 'normalized')
            if not normalized_path:
                current_app.logger.error(f"[HistoricalKPIController] Normalized file not found for file_id: {file_id}")
                return None

            # Read data
            import pandas as pd
            data = pd.read_csv(normalized_path) if normalized_path.endswith('.csv') else pd.read_excel(normalized_path)

            # Extract period labels from data
            period_labels = self._extract_period_labels(data)

            if not period_labels:
                current_app.logger.error(f"[HistoricalKPIController] No period labels found in data")
                return None

            # Detect granularity
            granularity_info = self.granularity_detector.detect_granularity(period_labels)

            # Store in database
            granularity_record = DataGranularity(
                upload_id=upload_id,
                file_id=file_id,
                detected_granularity=granularity_info['granularity'],
                confidence_score=granularity_info['confidence'],
                period_count=granularity_info['period_count'],
                date_range_start=granularity_info['date_range'][0],
                date_range_end=granularity_info['date_range'][1],
                suggested_chart_periods=json.dumps(granularity_info['suggested_chart_periods']),
                auto_detection_notes=f"Auto-detected from {len(period_labels)} period labels"
            )

            db.session.add(granularity_record)
            db.session.commit()

            current_app.logger.info(f"[HistoricalKPIController] Stored granularity info: {granularity_info['granularity']}")
            return granularity_info

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error detecting granularity: {str(e)}")
            db.session.rollback()
            return None

    def _extract_period_labels(self, data: pd.DataFrame) -> List[str]:
        """
        Extract period labels from normalized data
        """
        period_labels = []

        # Look for period columns
        for col in data.columns:
            if 'period' in col.lower() or 'date' in col.lower():
                # Get unique values from this column
                unique_values = data[col].dropna().unique()
                period_labels.extend([str(val) for val in unique_values])

        # If no period columns found, use row indices as periods
        if not period_labels:
            period_labels = [f"Period_{i+1}" for i in range(len(data))]

        return period_labels

    def _calculate_file_historical_kpis(self, upload_id: str, file_id: str, period_type: str) -> List[Dict[str, Any]]:
        """
        Calculate historical KPIs for a single file
        """
        try:
            # Read normalized data
            normalized_path = self.file_manager.get_stage_file_path(str(file_id), 'normalized')
            if not normalized_path:
                return []

            import pandas as pd
            data = pd.read_csv(normalized_path) if normalized_path.endswith('.csv') else pd.read_excel(normalized_path)

            # Get available columns
            available_columns = set(data.columns)

            # Get calculable KPIs
            calculable_kpis = self._get_calculable_kpis(available_columns)

            if not calculable_kpis:
                return []

            # Get KPI definitions
            kpi_definitions = db.session.query(
                KPIDefinitions.kpi_name,
                KPIDefinitions.required_columns,
                KPIDefinitions.kpi_category
            ).filter(KPIDefinitions.kpi_name.in_(calculable_kpis)).all()

            kpi_requirements = {
                kpi_name: {
                    'required_col': required_col,
                    'kpi_category': kpi_category
                } for kpi_name, required_col, kpi_category in kpi_definitions
            }

            # Calculate KPIs for each period
            historical_kpis = []

            # Group data by periods (assuming first column contains periods)
            period_groups = self._group_data_by_periods(data, period_type)

            for period_info, period_data in period_groups.items():
                period_start, period_end, period_label = period_info

                for kpi_name, kpi_details in kpi_requirements.items():
                    try:
                        start_time = datetime.now()

                        required_cols = kpi_details['required_col']
                        kpi_category = kpi_details['kpi_category']

                        # Calculate KPI for this period
                        result = self.kpi_calculator.calculate_kpi(kpi_name, period_data, required_cols=required_cols)

                        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

                        if result is not None:
                            historical_kpis.append({
                                'upload_id': upload_id,
                                'file_id': file_id,
                                'kpi_name': kpi_name,
                                'kpi_category': kpi_category,
                                'period_start_date': period_start,
                                'period_end_date': period_end,
                                'period_type': period_type,
                                'period_label': period_label,
                                'kpi_value': float(result),
                                'calculation_status': 'calculated',
                                'calculation_duration_ms': processing_time,
                                'data_quality_score': 1.0
                            })
                        else:
                            historical_kpis.append({
                                'upload_id': upload_id,
                                'file_id': file_id,
                                'kpi_name': kpi_name,
                                'kpi_category': kpi_category,
                                'period_start_date': period_start,
                                'period_end_date': period_end,
                                'period_type': period_type,
                                'period_label': period_label,
                                'kpi_value': None,
                                'calculation_status': 'failed',
                                'calculation_duration_ms': processing_time,
                                'error_message': 'Calculation returned None'
                            })

                    except Exception as calc_err:
                        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                        historical_kpis.append({
                            'upload_id': upload_id,
                            'file_id': file_id,
                            'kpi_name': kpi_name,
                            'kpi_category': kpi_category,
                            'period_start_date': period_start,
                            'period_end_date': period_end,
                            'period_type': period_type,
                            'period_label': period_label,
                            'kpi_value': None,
                            'calculation_status': 'failed',
                            'calculation_duration_ms': processing_time,
                            'error_message': str(calc_err)
                        })

            return historical_kpis

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error calculating file historical KPIs: {str(e)}")
            return []

    def _get_calculable_kpis(self, available_columns: set) -> List[str]:
        """
        Get list of KPIs that can be calculated with available columns
        """
        try:
            required_columns = db.session.query(
                KPIDefinitions.kpi_name,
                KPIDefinitions.required_columns
            ).filter(KPIDefinitions.is_active == True).all()

            calculable_kpis = []

            for kpi_name, required_cols in required_columns:
                if required_cols and set(required_cols).issubset(available_columns):
                    calculable_kpis.append(kpi_name)

            return calculable_kpis

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error getting calculable KPIs: {str(e)}")
            return []

    def _delete_existing_historical_kpis(self, upload_id: str) -> int:
        """
        Delete existing historical KPI data for an upload_id
        """
        try:
            # Delete existing historical KPI data
            deleted_count = KPIHistoricalData.query.filter_by(upload_id=upload_id).delete()

            # Delete existing granularity data
            DataGranularity.query.filter_by(upload_id=upload_id).delete()

            db.session.commit()

            current_app.logger.info(f"[HistoricalKPIController] Deleted {deleted_count} existing historical KPI records for upload_id: {upload_id}")
            return deleted_count

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error deleting existing historical KPIs: {str(e)}")
            db.session.rollback()
            return 0

    def _group_data_by_periods(self, data: pd.DataFrame, period_type: str) -> Dict[Tuple[date, date, str], pd.DataFrame]:
        """
        Group data by periods based on period_type with intelligent period detection
        """
        try:
            period_groups = {}
            total_rows = len(data)

            current_app.logger.info(f"[HistoricalKPIController] Grouping {total_rows} rows into {period_type} periods")

            if period_type == 'monthly':
                # Group every 1 row as monthly (since each row represents a month)
                periods_per_group = 1
                period_days = 30
            elif period_type == 'quarterly':
                # Group every 3 rows as quarterly
                periods_per_group = 3
                period_days = 90
            elif period_type == 'yearly':
                # Group every 12 rows as yearly
                periods_per_group = 12
                period_days = 365
            else:
                # Default to monthly
                periods_per_group = 1
                period_days = 30

            # Calculate how many periods we'll have
            num_periods = max(1, total_rows // periods_per_group)
            if total_rows % periods_per_group != 0:
                num_periods += 1

            current_app.logger.info(f"[HistoricalKPIController] Creating {num_periods} {period_type} periods from {total_rows} rows")

            # Group data into periods
            for period_idx in range(num_periods):
                start_row = period_idx * periods_per_group
                end_row = min(start_row + periods_per_group, total_rows)

                # Get data for this period
                period_data = data.iloc[start_row:end_row]

                # Create period label
                period_label = f"{period_type}{period_idx + 1}"

                # Create realistic dates based on period type
                base_date = date.today() - timedelta(days=period_days * (num_periods - period_idx - 1))

                if period_type == 'monthly':
                    period_start = base_date
                    period_end = base_date + timedelta(days=29)
                elif period_type == 'quarterly':
                    period_start = base_date
                    period_end = base_date + timedelta(days=89)
                elif period_type == 'yearly':
                    period_start = base_date
                    period_end = base_date + timedelta(days=364)
                else:
                    period_start = base_date
                    period_end = base_date + timedelta(days=29)

                period_groups[(period_start, period_end, period_label)] = period_data

                current_app.logger.info(f"[HistoricalKPIController] Created {period_label}: {len(period_data)} rows, {period_start} to {period_end}")

            current_app.logger.info(f"[HistoricalKPIController] Successfully created {len(period_groups)} {period_type} periods")
            return period_groups

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error grouping data by periods: {str(e)}")
            return {}

    def _store_historical_kpis(self, historical_kpis: List[Dict[str, Any]]) -> int:
        """
        Store historical KPIs in database
        """
        try:
            if not historical_kpis:
                return 0

            # Create KPIHistoricalData records
            kpi_records = []
            for kpi_data in historical_kpis:
                kpi_record = KPIHistoricalData(
                    upload_id=kpi_data['upload_id'],
                    file_id=kpi_data.get('file_id'),
                    kpi_name=kpi_data['kpi_name'],
                    kpi_category=kpi_data['kpi_category'],
                    period_start_date=kpi_data['period_start_date'],
                    period_end_date=kpi_data['period_end_date'],
                    period_type=kpi_data['period_type'],
                    period_label=kpi_data['period_label'],
                    kpi_value=kpi_data['kpi_value'],
                    calculation_status=kpi_data['calculation_status'],
                    calculation_duration_ms=kpi_data['calculation_duration_ms'],
                    data_quality_score=kpi_data.get('data_quality_score'),
                    error_message=kpi_data.get('error_message')
                )
                kpi_records.append(kpi_record)

            # Bulk insert
            db.session.add_all(kpi_records)
            db.session.commit()

            current_app.logger.info(f"[HistoricalKPIController] Stored {len(kpi_records)} historical KPI records")
            return len(kpi_records)

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error storing historical KPIs: {str(e)}")
            db.session.rollback()
            return 0

    def _determine_chart_type(self, kpi_category: str) -> str:
        """
        Determine appropriate chart type based on KPI category
        """
        if kpi_category in ['Profitability', 'Growth']:
            return 'line'
        elif kpi_category in ['Liquidity', 'Leverage']:
            return 'bar'
        elif kpi_category in ['Efficiency', 'Cash Flow']:
            return 'area'
        else:
            return 'line'

    def _save_kpi_results_to_files(self, upload_id: str, result: Dict[str, Any], all_historical_kpis: List[Dict[str, Any]]) -> None:
        """
        Save KPI calculation results to CSV and JSON files using FilePersistenceManager
        Following the same pattern as finance_kpi_controller.py
        """
        try:
            from datetime import datetime
            from utils.finance_file_manager import FilePersistenceManager

            # Use FilePersistenceManager like finance_kpi_controller.py does
            file_manager = FilePersistenceManager()

            # Get the first file_id for this upload_id to use with FilePersistenceManager
            file_ids = self._get_files_in_upload(upload_id)
            if not file_ids:
                current_app.logger.error(f"[HistoricalKPIController] No files found for upload_id: {upload_id}")
                return

            # Use the first file_id for saving (FilePersistenceManager needs a file_id)
            file_id = str(file_ids[0])

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            current_app.logger.info(f"[HistoricalKPIController] Saving KPI results using FilePersistenceManager for file_id: {file_id}")

            # 1. Save detailed KPI data to CSV in kpi_calculation stage
            csv_filename = f'historical_kpi_data_{timestamp}.csv'
            csv_path = self._save_historical_kpis_to_csv_via_manager(file_manager, file_id, csv_filename, all_historical_kpis)

            # 2. Save organized period data to JSON in kpi_calculation stage
            json_filename = f'kpi_periods_data_{timestamp}.json'
            json_path = self._save_periods_data_to_json_via_manager(file_manager, file_id, json_filename, upload_id, all_historical_kpis)

            # 3. Save calculation summary to JSON in kpi_calculation stage
            summary_filename = f'kpi_calculation_summary_{timestamp}.json'
            summary_path = self._save_calculation_summary_to_json_via_manager(file_manager, file_id, summary_filename, result)

            # 4. Save summary to metadata folder using FilePersistenceManager
            metadata_filename = f'kpi_calculation_summary_{timestamp}.json'

            # Create a simple JSON-safe version of the result
            json_safe_result = self._create_json_safe_result(result)

            metadata_path = file_manager.save_metadata_json(
                file_id=file_id,
                filename=metadata_filename,
                payload=json_safe_result
            )

            # Log success using the same pattern as FilePersistenceManager
            current_app.logger.info(f"[HistoricalKPIController] Saved KPI results to files:")
            current_app.logger.info(f"  - CSV: {file_manager.to_relative_path(csv_path) if csv_path else 'Failed'}")
            current_app.logger.info(f"  - JSON: {file_manager.to_relative_path(json_path) if json_path else 'Failed'}")
            current_app.logger.info(f"  - Summary: {file_manager.to_relative_path(summary_path) if summary_path else 'Failed'}")
            current_app.logger.info(f"  - Metadata: {metadata_path}")

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error saving KPI results to files: {str(e)}")
            import traceback
            current_app.logger.error(f"[HistoricalKPIController] Traceback: {traceback.format_exc()}")

    def _save_historical_kpis_to_csv(self, file_path: str, historical_kpis: List[Dict[str, Any]]) -> None:
        """
        Save historical KPI data to CSV file
        """
        try:
            if not historical_kpis:
                current_app.logger.warning(f"[HistoricalKPIController] No historical KPIs to save to CSV")
                return

            current_app.logger.info(f"[HistoricalKPIController] Saving {len(historical_kpis)} KPI records to CSV: {file_path}")

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = [
                    'upload_id', 'file_id', 'kpi_name', 'kpi_category',
                    'period_start_date', 'period_end_date', 'period_type', 'period_label',
                    'kpi_value', 'calculation_status', 'calculation_duration_ms',
                    'data_quality_score', 'error_message'
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for kpi in historical_kpis:
                    writer.writerow({
                        'upload_id': str(kpi.get('upload_id', '')),
                        'file_id': str(kpi.get('file_id', '')),
                        'kpi_name': str(kpi.get('kpi_name', '')),
                        'kpi_category': str(kpi.get('kpi_category', '')),
                        'period_start_date': str(kpi.get('period_start_date', '')),
                        'period_end_date': str(kpi.get('period_end_date', '')),
                        'period_type': str(kpi.get('period_type', '')),
                        'period_label': str(kpi.get('period_label', '')),
                        'kpi_value': str(kpi.get('kpi_value', '')),
                        'calculation_status': str(kpi.get('calculation_status', '')),
                        'calculation_duration_ms': str(kpi.get('calculation_duration_ms', '')),
                        'data_quality_score': str(kpi.get('data_quality_score', '')),
                        'error_message': str(kpi.get('error_message', ''))
                    })

            current_app.logger.info(f"[HistoricalKPIController] Successfully saved CSV file: {file_path}")

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error saving historical KPIs to CSV: {str(e)}")
            import traceback
            current_app.logger.error(f"[HistoricalKPIController] CSV Traceback: {traceback.format_exc()}")

    def _get_files_in_upload(self, upload_id: str) -> List[str]:
        """
        Get all file IDs for a given upload_id
        """
        try:
            from models.finance_report_gen.financial_file_model import FinancialFile

            files = FinancialFile.query.filter_by(upload_id=upload_id).all()
            return [str(f.file_id) for f in files]
        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error fetching files for upload_id {upload_id}: {str(e)}")
            return []

    def _make_json_serializable(self, data: Any) -> Any:
        """
        Recursively convert data to JSON serializable format
        """
        from datetime import date, datetime
        import decimal

        if isinstance(data, dict):
            return {key: self._make_json_serializable(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._make_json_serializable(item) for item in data]
        elif isinstance(data, (date, datetime)):
            return data.isoformat()
        elif isinstance(data, decimal.Decimal):
            return float(data)
        elif hasattr(data, '__dict__'):
            # Handle custom objects by converting to dict
            return self._make_json_serializable(data.__dict__)
        else:
            return data

    def _convert_dates_to_strings(self, data: Any) -> Any:
        """
        Aggressively convert all date/datetime objects to strings
        """
        from datetime import date, datetime
        import decimal

        if isinstance(data, dict):
            return {key: self._convert_dates_to_strings(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._convert_dates_to_strings(item) for item in data]
        elif isinstance(data, (date, datetime)):
            return str(data)
        elif isinstance(data, decimal.Decimal):
            return str(data)
        elif hasattr(data, '__dict__'):
            # Handle custom objects by converting to dict
            return self._convert_dates_to_strings(data.__dict__)
        else:
            return data

    def _create_json_safe_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a completely JSON-safe version of the result by converting everything to basic types
        """
        try:
            json_safe = {}

            for key, value in result.items():
                if isinstance(value, dict):
                    json_safe[key] = self._create_json_safe_result(value)
                elif isinstance(value, list):
                    json_safe[key] = [self._convert_to_json_safe(item) for item in value]
                else:
                    json_safe[key] = self._convert_to_json_safe(value)

            return json_safe

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error creating JSON-safe result: {str(e)}")
            return {"error": str(e), "original_result": str(result)}

    def _convert_to_json_safe(self, value: Any) -> Any:
        """
        Convert any value to a JSON-safe type
        """
        from datetime import date, datetime
        import decimal

        if value is None:
            return None
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, (date, datetime)):
            return str(value)
        elif isinstance(value, decimal.Decimal):
            return str(value)
        elif hasattr(value, '__dict__'):
            # Convert custom objects to string representation
            return str(value)
        else:
            # Convert everything else to string
            return str(value)

    def _save_historical_kpis_to_csv_via_manager(self, file_manager, file_id: str, filename: str, historical_kpis: List[Dict[str, Any]]) -> str:
        """
        Save historical KPI data to CSV file using FilePersistenceManager
        """
        try:
            if not historical_kpis:
                current_app.logger.warning("[HistoricalKPIController] No historical KPIs to save to CSV")
                return None

            # Convert to DataFrame for FilePersistenceManager
            import pandas as pd

            # Convert all values to strings to prevent CSV writing issues
            csv_data = []
            for kpi in historical_kpis:
                csv_row = {}
                for key, value in kpi.items():
                    csv_row[key] = str(value) if value is not None else ""
                csv_data.append(csv_row)

            df = pd.DataFrame(csv_data)

            # Save using FilePersistenceManager
            file_path = file_manager.save_stage_file(
                file_id=file_id,
                stage_name='kpi_calculation',
                data=df,
                original_filename=filename,
                metadata={
                    'stage': 'kpi_calculation',
                    'file_type': 'historical_kpi_data',
                    'rows': len(csv_data)
                }
            )

            current_app.logger.info(f"[HistoricalKPIController] Saved {len(csv_data)} historical KPIs to CSV via FilePersistenceManager")
            return file_path

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error saving historical KPIs to CSV via manager: {str(e)}")
            import traceback
            current_app.logger.error(f"[HistoricalKPIController] Traceback: {traceback.format_exc()}")
            return None

    def _save_periods_data_to_json_via_manager(self, file_manager, file_id: str, filename: str, upload_id: str, historical_kpis: List[Dict[str, Any]]) -> str:
        """
        Save organized period data to JSON file using FilePersistenceManager
        """
        try:
            if not historical_kpis:
                current_app.logger.warning("[HistoricalKPIController] No historical KPIs to save to JSON")
                return None

            # Create the same structure as the API response
            periods_data = self._organize_kpis_by_periods_for_saving(historical_kpis)

            # Save as JSON using FilePersistenceManager
            import json
            import tempfile
            from datetime import date, datetime

            # Custom JSON encoder to handle date objects
            class DateEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, (date, datetime)):
                        return obj.isoformat()
                    return super().default(obj)

            # Create temporary file to write JSON
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(periods_data, temp_file, indent=2, cls=DateEncoder)
                temp_file_path = temp_file.name

            # Read the JSON content and save via FilePersistenceManager
            with open(temp_file_path, 'r') as f:
                json_content = f.read()

            # Clean up temp file
            os.unlink(temp_file_path)

            # Save using FilePersistenceManager (as bytes)
            file_path = file_manager.save_stage_file(
                file_id=file_id,
                stage_name='kpi_calculation',
                data=json_content.encode('utf-8'),
                original_filename=filename,
                metadata={
                    'stage': 'kpi_calculation',
                    'file_type': 'kpi_periods_data',
                    'upload_id': upload_id
                }
            )

            current_app.logger.info(f"[HistoricalKPIController] Saved periods data to JSON via FilePersistenceManager")
            return file_path

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error saving periods data to JSON via manager: {str(e)}")
            import traceback
            current_app.logger.error(f"[HistoricalKPIController] Traceback: {traceback.format_exc()}")
            return None

    def _save_calculation_summary_to_json_via_manager(self, file_manager, file_id: str, filename: str, result: Dict[str, Any]) -> str:
        """
        Save calculation summary to JSON file using FilePersistenceManager
        """
        try:
            if not result:
                current_app.logger.warning("[HistoricalKPIController] No calculation summary to save")
                return None

            # Save as JSON using FilePersistenceManager
            import json
            import tempfile
            from datetime import date, datetime

            # Custom JSON encoder to handle date objects
            class DateEncoder(json.JSONEncoder):
                def default(self, obj):
                    if isinstance(obj, (date, datetime)):
                        return obj.isoformat()
                    return super().default(obj)

            # Create temporary file to write JSON
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
                json.dump(result, temp_file, indent=2, cls=DateEncoder)
                temp_file_path = temp_file.name

            # Read the JSON content and save via FilePersistenceManager
            with open(temp_file_path, 'r') as f:
                json_content = f.read()

            # Clean up temp file
            os.unlink(temp_file_path)

            # Save using FilePersistenceManager (as bytes)
            file_path = file_manager.save_stage_file(
                file_id=file_id,
                stage_name='kpi_calculation',
                data=json_content.encode('utf-8'),
                original_filename=filename,
                metadata={
                    'stage': 'kpi_calculation',
                    'file_type': 'calculation_summary'
                }
            )

            current_app.logger.info(f"[HistoricalKPIController] Saved calculation summary to JSON via FilePersistenceManager")
            return file_path

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error saving calculation summary to JSON via manager: {str(e)}")
            import traceback
            current_app.logger.error(f"[HistoricalKPIController] Traceback: {traceback.format_exc()}")
            return None

    def _organize_kpis_by_periods_for_saving(self, historical_kpis: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Organize KPIs by periods for saving to JSON (same structure as API response)
        """
        try:
            # Group KPIs by period type
            periods_data = {
                "monthly": {},
                "quarterly": {},
                "yearly": {}
            }

            period_names = []

            # Group by period type and create numbered periods
            for period_type in ["monthly", "quarterly", "yearly"]:
                period_kpis = [kpi for kpi in historical_kpis if kpi.get('period_type') == period_type]

                if period_kpis:
                    # Group by period_label to create numbered periods
                    period_groups = {}
                    for kpi in period_kpis:
                        period_label = kpi.get('period_label', '')
                        if period_label not in period_groups:
                            period_groups[period_label] = {}

                        # Convert date objects to strings for JSON serialization
                        kpi_name = kpi.get('kpi_name', '')
                        kpi_value = kpi.get('kpi_value', 0)

                        # Handle different value types
                        if isinstance(kpi_value, (int, float)):
                            period_groups[period_label][kpi_name] = float(kpi_value)
                        else:
                            period_groups[period_label][kpi_name] = str(kpi_value) if kpi_value is not None else 0

                    # Convert to numbered periods (monthly1, monthly2, etc.)
                    period_counter = 1
                    for period_label, kpi_values in period_groups.items():
                        numbered_period = f"{period_type}{period_counter}"
                        periods_data[period_type][numbered_period] = kpi_values

                        # Add to period_names with proper date formatting
                        period_start = None
                        period_end = None

                        # Find start and end dates for this period
                        for kpi in period_kpis:
                            if kpi.get('period_label') == period_label:
                                period_start = kpi.get('period_start_date')
                                period_end = kpi.get('period_end_date')
                                break

                        period_names.append({
                            "name": numbered_period,
                            "start": str(period_start) if period_start else "",
                            "end": str(period_end) if period_end else ""
                        })

                        period_counter += 1

            return {
                "periods": periods_data,
                "metadata": {
                    "total_periods": len(period_names),
                    "period_names": period_names,
                    "upload_id": historical_kpis[0].get('upload_id') if historical_kpis else "",
                    "calculation_timestamp": str(datetime.utcnow())
                }
            }

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error organizing KPIs by periods: {str(e)}")
            return {
                "periods": {"monthly": {}, "quarterly": {}, "yearly": {}},
                "metadata": {"error": str(e)}
            }

    def _save_periods_data_to_json(self, file_path: str, upload_id: str, historical_kpis: List[Dict[str, Any]]) -> None:
        """
        Save organized period data to JSON file (same schema as API response)
        """
        try:
            # Organize data by periods (same logic as API endpoint)
            periods_data = {
                "monthly": {},
                "quarterly": {},
                "yearly": {}
            }
            kpi_names_set = set()
            period_names_list = []
            period_type_counts = {'monthly': 0, 'quarterly': 0, 'yearly': 0}

            for kpi_record in historical_kpis:
                period_type = kpi_record['period_type']
                if period_type in period_type_counts:
                    period_type_counts[period_type] += 1
                    period_name = f"{period_type}{period_type_counts[period_type]}"

                    kpi_name = kpi_record['kpi_name']
                    kpi_value = float(kpi_record['kpi_value']) if kpi_record['kpi_value'] else 0

                    # Initialize period if not exists
                    if period_name not in periods_data[period_type]:
                        periods_data[period_type][period_name] = {}

                    # Add KPI value to period
                    periods_data[period_type][period_name][kpi_name] = kpi_value

                    # Collect metadata
                    kpi_names_set.add(kpi_name)

                    # Add period info to period_names list (only once per period)
                    if not any(p['name'] == period_name for p in period_names_list):
                        period_names_list.append({
                            "name": period_name,
                            "start": kpi_record['period_start_date'].isoformat() if hasattr(kpi_record['period_start_date'], 'isoformat') else str(kpi_record['period_start_date']),
                            "end": kpi_record['period_end_date'].isoformat() if hasattr(kpi_record['period_end_date'], 'isoformat') else str(kpi_record['period_end_date'])
                        })

            # Convert sets to sorted lists for metadata
            kpi_names_list = sorted(list(kpi_names_set))
            period_names_list.sort(key=lambda x: x['name'])

            # Calculate total periods across all types
            total_periods = sum(len(periods_data[pt]) for pt in periods_data)

            # Create response data
            response_data = {
                "success": True,
                "upload_id": upload_id,
                "periods": periods_data,
                "metadata": {
                    "total_periods": total_periods,
                    "total_kpis": len(kpi_names_list),
                    "kpi_names": kpi_names_list,
                    "period_names": period_names_list,
                    "period_counts": {
                        "monthly": len(periods_data["monthly"]),
                        "quarterly": len(periods_data["quarterly"]),
                        "yearly": len(periods_data["yearly"])
                    },
                    "total_records": len(historical_kpis),
                    "date_range": {
                        "start": min([kpi['period_start_date'] for kpi in historical_kpis if kpi.get('period_start_date')]).isoformat() if historical_kpis else None,
                        "end": max([kpi['period_end_date'] for kpi in historical_kpis if kpi.get('period_end_date')]).isoformat() if historical_kpis else None
                    }
                }
            }

            # Save to JSON file
            current_app.logger.info(f"[HistoricalKPIController] Saving periods data to JSON: {file_path}")

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(response_data, jsonfile, indent=2, ensure_ascii=False, default=str)

            current_app.logger.info(f"[HistoricalKPIController] Successfully saved periods JSON: {file_path}")

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error saving periods data to JSON: {str(e)}")
            import traceback
            current_app.logger.error(f"[HistoricalKPIController] Periods JSON Traceback: {traceback.format_exc()}")

    def _save_calculation_summary_to_json(self, file_path: str, result: Dict[str, Any]) -> None:
        """
        Save calculation summary to JSON file
        """
        try:
            current_app.logger.info(f"[HistoricalKPIController] Saving calculation summary to JSON: {file_path}")

            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as jsonfile:
                json.dump(result, jsonfile, indent=2, ensure_ascii=False, default=str)

            current_app.logger.info(f"[HistoricalKPIController] Successfully saved JSON summary: {file_path}")

        except Exception as e:
            current_app.logger.error(f"[HistoricalKPIController] Error saving calculation summary to JSON: {str(e)}")
            import traceback
            current_app.logger.error(f"[HistoricalKPIController] JSON Summary Traceback: {traceback.format_exc()}")
