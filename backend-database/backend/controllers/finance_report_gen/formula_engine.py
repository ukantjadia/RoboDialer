import re
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from flask import current_app

class SimpleFormulaEngine:
    """
    Simple formula calculation engine for custom KPI expressions
    Supports basic arithmetic operations and column references
    """

    def __init__(self):
        self.supported_operations = ['+', '-', '*', '/', 'sum', 'avg', 'count', 'max', 'min']
        self.operation_functions = {
            'sum': np.sum,
            'avg': np.mean,
            'count': len,
            'max': np.max,
            'min': np.min
        }

    def calculate_custom_kpi(self, formula: str, data: pd.DataFrame,
                           period_start: Optional[datetime] = None,
                           period_end: Optional[datetime] = None) -> Optional[float]:
        """
        Calculate custom KPI using simple formula
        Example: "revenue / total_assets"
        """
        try:
            current_app.logger.info(f"[FormulaEngine] Calculating formula: {formula}")

            # Filter data by period if provided
            filtered_data = self._filter_data_by_period(data, period_start, period_end)

            # Parse and validate formula
            parsed_formula = self._parse_formula(formula, filtered_data.columns.tolist())
            if not parsed_formula['valid']:
                current_app.logger.error(f"[FormulaEngine] Invalid formula: {parsed_formula['error']}")
                return None

            # Calculate the formula
            result = self._execute_formula(parsed_formula, filtered_data)

            current_app.logger.info(f"[FormulaEngine] Formula result: {result}")
            return result

        except Exception as e:
            current_app.logger.error(f"[FormulaEngine] Error calculating formula {formula}: {str(e)}")
            return None

    def validate_formula(self, formula: str, available_columns: List[str]) -> Dict[str, Any]:
        """
        Validate formula syntax and column availability
        """
        try:
            parsed_formula = self._parse_formula(formula, available_columns)

            return {
                'valid': parsed_formula['valid'],
                'error': parsed_formula.get('error'),
                'required_columns': parsed_formula.get('required_columns', []),
                'missing_columns': parsed_formula.get('missing_columns', []),
                'supported_operations': self.supported_operations
            }

        except Exception as e:
            return {
                'valid': False,
                'error': f"Formula validation error: {str(e)}",
                'required_columns': [],
                'missing_columns': [],
                'supported_operations': self.supported_operations
            }

    def _parse_formula(self, formula: str, available_columns: List[str]) -> Dict[str, Any]:
        """
        Parse formula into components and validate
        """
        try:
            # Clean formula
            formula = formula.strip().replace(' ', '')

            # Extract column references (words that match available columns)
            column_pattern = r'\b([A-Za-z_][A-Za-z0-9_\s]*[A-Za-z0-9_]|[A-Za-z_])\b'
            found_columns = re.findall(column_pattern, formula)

            # Clean column names (remove extra spaces)
            found_columns = [col.strip() for col in found_columns]

            # Check which columns are available
            required_columns = []
            missing_columns = []

            for col in found_columns:
                if col in available_columns:
                    required_columns.append(col)
                else:
                    missing_columns.append(col)

            # Check for unsupported operations
            unsupported_ops = []
            for char in formula:
                if char in ['+', '-', '*', '/', '(', ')']:
                    continue
                elif char.isalnum() or char in ['_', '.']:
                    continue
                else:
                    if char not in unsupported_ops:
                        unsupported_ops.append(char)

            # Validate basic syntax
            if missing_columns:
                return {
                    'valid': False,
                    'error': f"Missing columns: {', '.join(missing_columns)}",
                    'required_columns': required_columns,
                    'missing_columns': missing_columns
                }

            if unsupported_ops:
                return {
                    'valid': False,
                    'error': f"Unsupported operations: {', '.join(unsupported_ops)}",
                    'required_columns': required_columns,
                    'missing_columns': missing_columns
                }

            # Check for balanced parentheses
            if formula.count('(') != formula.count(')'):
                return {
                    'valid': False,
                    'error': "Unbalanced parentheses",
                    'required_columns': required_columns,
                    'missing_columns': missing_columns
                }

            return {
                'valid': True,
                'formula': formula,
                'required_columns': required_columns,
                'missing_columns': missing_columns,
                'components': self._extract_formula_components(formula, required_columns)
            }

        except Exception as e:
            return {
                'valid': False,
                'error': f"Formula parsing error: {str(e)}",
                'required_columns': [],
                'missing_columns': []
            }

    def _extract_formula_components(self, formula: str, columns: List[str]) -> List[Dict[str, Any]]:
        """
        Extract formula components (columns, operations, functions)
        """
        components = []
        i = 0

        while i < len(formula):
            char = formula[i]

            if char in ['+', '-', '*', '/', '(', ')']:
                components.append({
                    'type': 'operation',
                    'value': char
                })
                i += 1

            elif char.isalpha() or char == '_':
                # Extract column name or function
                start = i
                while i < len(formula) and (formula[i].isalnum() or formula[i] in ['_', ' ']):
                    i += 1

                word = formula[start:i].strip()

                if word in columns:
                    components.append({
                        'type': 'column',
                        'value': word
                    })
                elif word in self.operation_functions:
                    components.append({
                        'type': 'function',
                        'value': word
                    })
                else:
                    components.append({
                        'type': 'unknown',
                        'value': word
                    })

            else:
                i += 1

        return components

    def _execute_formula(self, parsed_formula: Dict[str, Any], data: pd.DataFrame) -> Optional[float]:
        """
        Execute the parsed formula on the data
        """
        try:
            formula = parsed_formula['formula']
            required_columns = parsed_formula['required_columns']

            # Replace column names with their values
            working_formula = formula

            for col in required_columns:
                # Get column values and handle NaN
                col_values = pd.to_numeric(data[col], errors='coerce').fillna(0)

                # For simple formulas, use the sum of the column
                col_sum = float(col_values.sum())

                # Replace column name with its sum value
                working_formula = working_formula.replace(col, str(col_sum))

            # Evaluate the formula safely
            try:
                result = eval(working_formula)
                return float(result) if result is not None else None
            except:
                # Fallback: try to calculate manually for simple cases
                return self._calculate_simple_formula(parsed_formula, data)

        except Exception as e:
            current_app.logger.error(f"[FormulaEngine] Error executing formula: {str(e)}")
            return None

    def _calculate_simple_formula(self, parsed_formula: Dict[str, Any], data: pd.DataFrame) -> Optional[float]:
        """
        Calculate simple formulas manually (fallback method)
        """
        try:
            components = parsed_formula.get('components', [])
            required_columns = parsed_formula['required_columns']

            # Get column values
            column_values = {}
            for col in required_columns:
                col_values = pd.to_numeric(data[col], errors='coerce').fillna(0)
                column_values[col] = float(col_values.sum())

            # Simple calculation for basic operations
            if len(required_columns) == 2 and len(components) == 3:
                col1, op, col2 = components[0]['value'], components[1]['value'], components[2]['value']

                if col1 in column_values and col2 in column_values:
                    val1, val2 = column_values[col1], column_values[col2]

                    if op == '+':
                        return val1 + val2
                    elif op == '-':
                        return val1 - val2
                    elif op == '*':
                        return val1 * val2
                    elif op == '/':
                        return val1 / val2 if val2 != 0 else None

            return None

        except Exception as e:
            current_app.logger.error(f"[FormulaEngine] Error in simple calculation: {str(e)}")
            return None

    def _filter_data_by_period(self, data: pd.DataFrame, period_start: Optional[datetime],
                              period_end: Optional[datetime]) -> pd.DataFrame:
        """
        Filter data by time period if date columns are available
        """
        try:
            if period_start is None and period_end is None:
                return data

            # Look for date columns
            date_columns = []
            for col in data.columns:
                if 'date' in col.lower() or 'period' in col.lower():
                    try:
                        pd.to_datetime(data[col], errors='raise')
                        date_columns.append(col)
                    except:
                        continue

            if not date_columns:
                current_app.logger.warning("[FormulaEngine] No date columns found for period filtering")
                return data

            # Use the first date column found
            date_col = date_columns[0]
            data[date_col] = pd.to_datetime(data[date_col], errors='coerce')

            # Filter by period
            if period_start:
                data = data[data[date_col] >= period_start]
            if period_end:
                data = data[data[date_col] <= period_end]

            return data

        except Exception as e:
            current_app.logger.error(f"[FormulaEngine] Error filtering data by period: {str(e)}")
            return data
