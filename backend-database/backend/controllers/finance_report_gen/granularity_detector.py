import re
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal
import pandas as pd
from flask import current_app

class GranularityDetector:
    """
    Detects data granularity from period labels and suggests optimal chart periods
    """

    def __init__(self):
        self.period_patterns = {
            'daily': [
                r'^\d{4}-\d{2}-\d{2}$',  # 2023-01-15
                r'^\d{1,2}/\d{1,2}/\d{4}$',  # 1/15/2023
                r'^\d{1,2}-\d{1,2}-\d{4}$',  # 1-15-2023
            ],
            'weekly': [
                r'^W\d{1,2}-\d{4}$',  # W1-2023
                r'^Week \d{1,2}, \d{4}$',  # Week 1, 2023
                r'^\d{4}-W\d{2}$',  # 2023-W01
            ],
            'monthly': [
                r'^\d{4}-\d{2}$',  # 2023-01
                r'^[A-Za-z]{3} \d{4}$',  # Jan 2023
                r'^[A-Za-z]+ \d{4}$',  # January 2023
                r'^\d{1,2}/\d{4}$',  # 1/2023
            ],
            'quarterly': [
                r'^\d{4}-Q\d{1}$',  # 2023-Q1
                r'^Q\d{1} \d{4}$',  # Q1 2023
                r'^Q\d{1}-\d{4}$',  # Q1-2023
            ],
            'yearly': [
                r'^\d{4}$',  # 2023
                r'^FY \d{4}$',  # FY 2023
                r'^Financial Year \d{4}$',  # Financial Year 2023
            ]
        }

    def detect_granularity(self, period_labels: List[str]) -> Dict[str, Any]:
        """
        Auto-detect data granularity from period labels
        Returns: {
            'granularity': 'monthly',
            'confidence': 0.95,
            'period_count': 12,
            'date_range': (start_date, end_date),
            'suggested_chart_periods': ['monthly', 'quarterly']
        }
        """
        current_app.logger.info(f"[GranularityDetector] Analyzing {len(period_labels)} period labels")

        if not period_labels:
            return {
                'granularity': 'monthly',
                'confidence': 0.0,
                'period_count': 0,
                'date_range': (None, None),
                'suggested_chart_periods': ['monthly'],
                'error': 'No period labels provided'
            }

        # Analyze each period label
        granularity_scores = {granularity: 0 for granularity in self.period_patterns.keys()}
        valid_periods = []
        date_range_start = None
        date_range_end = None

        for label in period_labels:
            label_str = str(label).strip()
            if not label_str or label_str.lower() in ['nan', 'none', '']:
                continue

            # Check against each granularity pattern
            for granularity, patterns in self.period_patterns.items():
                for pattern in patterns:
                    if re.match(pattern, label_str, re.IGNORECASE):
                        granularity_scores[granularity] += 1
                        valid_periods.append(label_str)

                        # Try to extract date for range calculation
                        parsed_date = self._parse_period_to_date(label_str, granularity)
                        if parsed_date:
                            if date_range_start is None or parsed_date < date_range_start:
                                date_range_start = parsed_date
                            if date_range_end is None or parsed_date > date_range_end:
                                date_range_end = parsed_date
                        break

        # Determine the most likely granularity
        total_matches = sum(granularity_scores.values())
        if total_matches == 0:
            current_app.logger.warning("[GranularityDetector] No patterns matched - defaulting to monthly")
            return {
                'granularity': 'monthly',
                'confidence': 0.1,
                'period_count': len(period_labels),
                'date_range': (None, None),
                'suggested_chart_periods': ['monthly'],
                'error': 'No recognizable period patterns found'
            }

        # Find the granularity with highest score
        best_granularity = max(granularity_scores, key=granularity_scores.get)
        confidence = granularity_scores[best_granularity] / total_matches

        # Calculate period count
        period_count = len(valid_periods)

        # Suggest chart periods based on data span and granularity
        suggested_chart_periods = self._suggest_chart_periods(best_granularity, period_count, date_range_start, date_range_end)

        result = {
            'granularity': best_granularity,
            'confidence': round(confidence, 3),
            'period_count': period_count,
            'date_range': (date_range_start, date_range_end),
            'suggested_chart_periods': suggested_chart_periods,
            'granularity_scores': granularity_scores,
            'valid_periods_count': len(valid_periods)
        }

        current_app.logger.info(f"[GranularityDetector] Detected granularity: {best_granularity} (confidence: {confidence:.3f})")
        return result

    def _parse_period_to_date(self, period_label: str, granularity: str) -> Optional[date]:
        """Parse period label to a date for range calculation"""
        try:
            if granularity == 'yearly':
                match = re.match(r'^(\d{4})$', period_label)
                if match:
                    year = int(match.group(1))
                    return date(year, 1, 1)

            elif granularity == 'quarterly':
                match = re.match(r'^(\d{4})-Q(\d{1})$', period_label)
                if match:
                    year, quarter = int(match.group(1)), int(match.group(2))
                    month = (quarter - 1) * 3 + 1
                    return date(year, month, 1)

            elif granularity == 'monthly':
                # Try YYYY-MM format
                match = re.match(r'^(\d{4})-(\d{2})$', period_label)
                if match:
                    year, month = int(match.group(1)), int(match.group(2))
                    return date(year, month, 1)

                # Try month name format
                try:
                    dt = datetime.strptime(period_label, "%b %Y")
                    return date(dt.year, dt.month, 1)
                except ValueError:
                    try:
                        dt = datetime.strptime(period_label, "%B %Y")
                        return date(dt.year, dt.month, 1)
                    except ValueError:
                        pass

            elif granularity == 'daily':
                try:
                    return datetime.strptime(period_label, "%Y-%m-%d").date()
                except ValueError:
                    try:
                        return datetime.strptime(period_label, "%m/%d/%Y").date()
                    except ValueError:
                        pass

        except Exception as e:
            current_app.logger.debug(f"[GranularityDetector] Error parsing period {period_label}: {e}")

        return None

    def _suggest_chart_periods(self, detected_granularity: str, period_count: int,
                              start_date: Optional[date], end_date: Optional[date]) -> List[str]:
        """
        Suggest optimal chart periods based on data characteristics
        """
        suggestions = []

        # Calculate data span in days if we have dates
        data_span_days = None
        if start_date and end_date:
            data_span_days = (end_date - start_date).days

        # Suggest based on data span and period count
        if data_span_days:
            if data_span_days >= 1825:  # 5+ years
                suggestions = ['yearly', 'quarterly']
            elif data_span_days >= 365:  # 1-5 years
                suggestions = ['quarterly', 'monthly']
            elif data_span_days >= 180:  # 6-12 months
                suggestions = ['monthly', 'weekly']
            else:  # <6 months
                suggestions = ['weekly', 'daily']
        else:
            # Fallback to period count
            if period_count >= 20:
                suggestions = ['yearly', 'quarterly']
            elif period_count >= 12:
                suggestions = ['quarterly', 'monthly']
            elif period_count >= 6:
                suggestions = ['monthly', 'weekly']
            else:
                suggestions = ['weekly', 'daily']

        # Always include the detected granularity
        if detected_granularity not in suggestions:
            suggestions.insert(0, detected_granularity)

        return suggestions[:3]  # Return top 3 suggestions

    def suggest_period_division(self, granularity: str, period_count: int) -> str:
        """
        Suggest optimal period division for charts based on data characteristics
        """
        if period_count >= 20:
            return 'yearly'
        elif period_count >= 12:
            return 'quarterly'
        elif period_count >= 6:
            return 'monthly'
        else:
            return 'weekly'
