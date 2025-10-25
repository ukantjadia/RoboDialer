from flask import current_app
from models.finance_report_gen.financial_file_model import FinancialFile
from models.finance_report_gen.kpi_definitions_model import KPIDefinitions
from typing import List,Dict,Optional
from dataclasses import dataclass
import pandas as pd
from datetime import datetime
import os
import json
import numpy as np
from models.lead_model import db
from uuid import UUID
from models.finance_report_gen.financial_kpi_model import FinancialKPI
from utils.finance_file_manager import FilePersistenceManager

class FileDataReader:
    # Check for extension at router itself
    @staticmethod
    def read_file_data(file_path:str) -> pd.DataFrame:
        try:

            if not os.path.exists(file_path):
                raise FileNotFoundError(
                    f"File not found at path: {file_path}")

            file_extension = os.path.splitext(file_path)[1].lower()
            current_app.logger.info(f'[finance_kpi_controller] file at {file_path} of extension {file_extension} is being processed')

            if file_extension == ".csv":
                return pd.read_csv(file_path)

            elif file_extension in [".xlsx",".xls"]:
                return pd.read_excel(file_path)
            else:
                raise ValueError(f"Unsupported file format:")


        except Exception as e:
            raise Exception(f"[finance_kpi_controller] Error reading file {file_path} : {str(e)}")

class KPICalculation:

    def calculate_kpi(self, kpi_name: str, data: pd.DataFrame, required_cols) -> Dict:
        try:
            current_app.logger.info(f"Calculating the KPI for {kpi_name}")

            if kpi_name == "Net Profit Margin":
                return self._calculate_net_profit_margin(data, required_cols)
            elif kpi_name == "Gross Profit Margin":
                return self._calculate_gross_profit_margin(data, required_cols)
            elif kpi_name == "Operating Profit Margin":
                return self._calculate_operating_profit_margin(data, required_cols)
            elif kpi_name == "EBITDA Margin":
                return self._calculate_ebitda_margin(data, required_cols)
            elif kpi_name == "Return on Assets (ROA)":
                return self._calculate_return_on_assets(data, required_cols)
            elif kpi_name == "Return on Equity (ROE)":
                return self._calculate_return_on_equity(data, required_cols)
            elif kpi_name == "Debt to Equity Ratio":
                return self._calculate_debt_to_equity_ratio(data, required_cols)

            elif kpi_name == "Current Ratio":
                return self._calculate_current_ratio(data, required_cols)

            elif kpi_name == "Quick Ratio":
                return self._calculate_quick_ratio(data, required_cols)

            elif kpi_name == "Working Capital":
                return self._calculate_working_capital(data, required_cols)

            elif kpi_name == "Inventory Turnover":
                return self._calculate_inventory_turnover(data, required_cols)

            elif kpi_name == "Days Inventory Outstanding (DIO)":
                return self._calculate_days_inventory_outstanding(data, required_cols)

            elif kpi_name == "Receivables Turnover":
                return self._calculate_receivables_turnover(data, required_cols)

            elif kpi_name == "Payables Turnover":
                return self._calculate_payables_turnover(data, required_cols)

            elif kpi_name == "Accounts Receivable Turnover":
                return self._calculate_receivables_turnover(data, required_cols)

            elif kpi_name == "Accounts Payable Turnover":
                return self._calculate_payables_turnover(data, required_cols)

            elif kpi_name == "Days Payable Outstanding (DPO)":
                return self._calculate_days_payable_outstanding(data, required_cols)

            elif kpi_name == "Budget Variance":
                return self._calculate_budget_variance(data, required_cols)

            elif kpi_name == "Budget Creation Cycle Time":
                return self._calculate_budget_creation_cycle_time(data, required_cols)

            elif kpi_name == "Line Items in Budget":
                return self._calculate_line_items_in_budget(data, required_cols)

            elif kpi_name == "Number of Budget Iterations":
                return self._calculate_number_of_budget_iterations(data, required_cols)

            elif kpi_name == "Cash Ratio":
                return self._calculate_cash_ratio(data, required_cols)

            elif kpi_name == "Cash Conversion Cycle":
                return self._calculate_cash_conversion_cycle(data, required_cols)

            elif kpi_name == "Free Cash Flow":
                return self._calculate_free_cash_flow(data, required_cols)

            elif kpi_name == "Operating Cash Flow Ratio":
                return self._calculate_operating_cash_flow_ratio(data, required_cols)

            elif kpi_name == "Capex to Revenue":
                return self._calculate_capex_to_revenue(data, required_cols)

            elif kpi_name == "Debt Ratio":
                return self._calculate_debt_ratio(data, required_cols)

            elif kpi_name == "Interest Coverage Ratio":
                return self._calculate_interest_coverage_ratio(data, required_cols)

            elif kpi_name == "Earnings Per Share (EPS)":
                return self._calculate_earnings_per_share(data, required_cols)

            elif kpi_name == "Price to Earnings Ratio (P/E)":
                return self._calculate_price_to_earnings_ratio(data, required_cols)

            elif kpi_name == "Book Value per Share":
                return self._calculate_book_value_per_share(data, required_cols)

            elif kpi_name == "Dividend Payout Ratio":
                return self._calculate_dividend_payout_ratio(data, required_cols)

            elif kpi_name == "Dividend Yield":
                return self._calculate_dividend_yield(data, required_cols)

            elif kpi_name == "Total Asset Turnover":
                return self._calculate_total_asset_turnover(data, required_cols)

            elif kpi_name == "Fixed Asset Turnover":
                return self._calculate_fixed_asset_turnover(data, required_cols)

            elif kpi_name == "Revenue Growth Rate":
                return self._calculate_revenue_growth_rate(data, required_cols)

            elif kpi_name == "Net Income Growth Rate":
                return self._calculate_net_income_growth_rate(data, required_cols)

            elif kpi_name == "Operating Income Growth":
                return self._calculate_operating_income_growth(data, required_cols)

            elif kpi_name == "R&D to Revenue":
                return self._calculate_rd_to_revenue(data, required_cols)

            elif kpi_name == "SG&A to Revenue":
                return self._calculate_sga_to_revenue(data, required_cols)

            elif kpi_name == "Interest Expense to Revenue":
                return self._calculate_interest_expense_to_revenue(data, required_cols)

            elif kpi_name == "Net PPE to Total Assets":
                return self._calculate_net_ppe_to_total_assets(data, required_cols)

            elif kpi_name == "Intangibles to Total Assets":
                return self._calculate_intangibles_to_total_assets(data, required_cols)

            elif kpi_name == "Goodwill to Total Assets":
                return self._calculate_goodwill_to_total_assets(data, required_cols)

            elif kpi_name == "Capital Expenditure Ratio":
                return self._calculate_capital_expenditure_ratio(data, required_cols)

            elif kpi_name == "Operating Expense Ratio":
                return self._calculate_operating_expense_ratio(data, required_cols)

            elif kpi_name == "Tax Burden":
                return self._calculate_tax_burden(data, required_cols)

            elif kpi_name == "Long-Term Debt to Equity":
                return self._calculate_long_term_debt_to_equity(data, required_cols)

            elif kpi_name == "Total Liabilities to Equity":
                return self._calculate_total_liabilities_to_equity(data, required_cols)

            elif kpi_name == "Cash Flow to Net Income":
                return self._calculate_cash_flow_to_net_income(data, required_cols)

            elif kpi_name == "Cash Flow Margin":
                return self._calculate_cash_flow_margin(data, required_cols)

            else:
                raise ValueError(f"Unknown KPI: {kpi_name}")

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_calculation] [finance_kpi_controller] Error occured During Calculating Kpi {kpi_name}")
            raise Exception(f"Error calculating {kpi_name}: {str(e)}")


    def _calculate_net_profit_margin(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            net_income = pd.to_numeric(data["Net Income"], errors="coerce").fillna(0).to_numpy()
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()

            net_income_sum = np.sum(net_income, axis=0)
            total_revenue_sum = np.sum(total_revenue, axis=0)

            return net_income_sum/total_revenue_sum

        except Exception as e:
            current_app.logger.error(f"Error calculating net profit margin: {str(e)}")
            return None


    def _calculate_gross_profit_margin(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            gross_profit = pd.to_numeric(data["Gross Profit"], errors="coerce").fillna(0).to_numpy()
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()

            gross_profit_sum = np.sum(gross_profit, axis=0)
            total_revenue_sum = np.sum(total_revenue, axis=0)

            return gross_profit_sum / total_revenue_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Gross profit margin {e}")
            return None

    def _calculate_operating_profit_margin(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            operating_income = pd.to_numeric(data["Operating Income"], errors="coerce").fillna(0).to_numpy()
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()

            operating_income_sum = np.sum(operating_income, axis=0)
            total_revenue_sum = np.sum(total_revenue, axis=0)

            return operating_income_sum / total_revenue_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Operating profit margin {e}")
            return None

    def _calculate_ebitda_margin(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            operating_income = pd.to_numeric(data["Operating Income"], errors="coerce").fillna(0).to_numpy()
            depreciation_amortization = pd.to_numeric(data["Depreciation & Amortization"], errors="coerce").fillna(0).to_numpy()
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()

            operating_income_sum = np.sum(operating_income, axis=0)
            depreciation_amortization_sum = np.sum(depreciation_amortization, axis=0)
            total_revenue_sum = np.sum(total_revenue, axis=0)

            ebitda = operating_income_sum + depreciation_amortization_sum

            return ebitda / total_revenue_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating EBITDA margin {e}")
            return None

    def _calculate_return_on_assets(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            net_income = pd.to_numeric(data["Net Income"], errors="coerce").fillna(0).to_numpy()
            total_assets = pd.to_numeric(data["Total Assets"], errors="coerce").fillna(0).to_numpy()

            net_income_sum = np.sum(net_income, axis=0)
            total_assets_sum = np.sum(total_assets, axis=0)

            return net_income_sum / total_assets_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Return on Assets {e}")
            return None

    def _calculate_return_on_equity(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            net_income = pd.to_numeric(data["Net Income"], errors="coerce").fillna(0).to_numpy()
            shareholder_equity = pd.to_numeric(data["Shareholder Equity"], errors="coerce").fillna(0).to_numpy()

            net_income_sum = np.sum(net_income, axis=0)
            shareholder_equity_sum = np.sum(shareholder_equity, axis=0)

            return net_income_sum / shareholder_equity_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Return on Equity {e}")
            return None

    def _calculate_debt_to_equity_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            total_liabilities = pd.to_numeric(data["Total Liabilities"], errors="coerce").fillna(0).to_numpy()
            shareholder_equity = pd.to_numeric(data["Shareholder Equity"], errors="coerce").fillna(0).to_numpy()

            total_liabilities_sum = np.sum(total_liabilities, axis=0)
            shareholder_equity_sum = np.sum(shareholder_equity, axis=0)

            return total_liabilities_sum / shareholder_equity_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Debt to Equity Ratio {e}")
            return None

    def _calculate_current_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            current_assets = pd.to_numeric(data["Current Assets"], errors="coerce").fillna(0).to_numpy()
            current_liabilities = pd.to_numeric(data["Current Liabilities"], errors="coerce").fillna(0).to_numpy()

            current_assets_sum = np.sum(current_assets, axis=0)
            current_liabilities_sum = np.sum(current_liabilities, axis=0)

            return current_assets_sum / current_liabilities_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Current Ratio {e}")
            return None

    def _calculate_quick_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            cash = pd.to_numeric(data["Cash"], errors="coerce").fillna(0).to_numpy()
            receivables = pd.to_numeric(data["Receivables"], errors="coerce").fillna(0).to_numpy()
            current_liabilities = pd.to_numeric(data["Current Liabilities"], errors="coerce").fillna(0).to_numpy()

            cash_sum = np.sum(cash, axis=0)
            receivables_sum = np.sum(receivables, axis=0)
            current_liabilities_sum = np.sum(current_liabilities, axis=0)

            return (cash_sum + receivables_sum) / current_liabilities_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Quick Ratio {e}")
            return None

    def _calculate_working_capital(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            current_assets = pd.to_numeric(data["Current Assets"], errors="coerce").fillna(0).to_numpy()
            current_liabilities = pd.to_numeric(data["Current Liabilities"], errors="coerce").fillna(0).to_numpy()

            current_assets_sum = np.sum(current_assets, axis=0)
            current_liabilities_sum = np.sum(current_liabilities, axis=0)

            return current_assets_sum - current_liabilities_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Working Capital {e}")
            return None

    def _calculate_inventory_turnover(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            cost_of_revenue = pd.to_numeric(data["Cost of Revenue"], errors="coerce").fillna(0).to_numpy()
            inventory = pd.to_numeric(data["Inventory"], errors="coerce").fillna(0).to_numpy()

            cost_of_revenue_sum = np.sum(cost_of_revenue, axis=0)
            inventory_sum = np.sum(inventory, axis=0)

            return cost_of_revenue_sum / inventory_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Inventory Turnover {e}")
            return None

    def _calculate_days_inventory_outstanding(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # DIO ≈ 365 * Average Inventory / Cost of Revenue
            # With available aggregate columns, we use Inventory and Cost of Revenue totals
            inventory = pd.to_numeric(data["Inventory"], errors="coerce").fillna(0).to_numpy()
            cost_of_revenue = pd.to_numeric(data["Cost of Revenue"], errors="coerce").fillna(0).to_numpy()

            inventory_sum = np.sum(inventory, axis=0)
            cost_of_revenue_sum = np.sum(cost_of_revenue, axis=0)

            if cost_of_revenue_sum == 0:
                current_app.logger.error("Division by zero in DIO: Cost of Revenue total is 0")
                return None

            return (inventory_sum / cost_of_revenue_sum) * 365

        except Exception as e:
            current_app.logger.error(f"Error occured During Calculating Days Inventory Outstanding (DIO) {e}")
            return None

    def _calculate_days_inventory_outstanding(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # DIO ≈ 365 * Average Inventory / Cost of Revenue
            # With available aggregate columns, we use Inventory and Cost of Revenue totals
            inventory = pd.to_numeric(data["Inventory"], errors="coerce").fillna(0).to_numpy()
            cost_of_revenue = pd.to_numeric(data["Cost of Revenue"], errors="coerce").fillna(0).to_numpy()

            inventory_sum = np.sum(inventory, axis=0)
            cost_of_revenue_sum = np.sum(cost_of_revenue, axis=0)

            if cost_of_revenue_sum == 0:
                current_app.logger.error("Division by zero in DIO: Cost of Revenue total is 0")
                return None

            return (inventory_sum / cost_of_revenue_sum) * 365

        except Exception as e:
            current_app.logger.error(f"Error occured During Calculating Days Inventory Outstanding (DIO) {e}")
            return None

    def _calculate_receivables_turnover(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()
            accounts_receivable = pd.to_numeric(data["Accounts Receivable"], errors="coerce").fillna(0).to_numpy()

            total_revenue_sum = np.sum(total_revenue, axis=0)
            accounts_receivable_sum = np.sum(accounts_receivable, axis=0)

            return total_revenue_sum / accounts_receivable_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Receivables Turnover {e}")
            return None

    def _calculate_payables_turnover(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            cost_of_revenue = pd.to_numeric(data["Cost of Revenue"], errors="coerce").fillna(0).to_numpy()
            accounts_payable = pd.to_numeric(data["Accounts Payable"], errors="coerce").fillna(0).to_numpy()

            cost_of_revenue_sum = np.sum(cost_of_revenue, axis=0)
            accounts_payable_sum = np.sum(accounts_payable, axis=0)

            # Handle division by zero
            if accounts_payable_sum == 0 or pd.isna(accounts_payable_sum):
                current_app.logger.warning("Payables Turnover: Division by zero - Accounts Payable is zero or NaN")
                return 0.0

            return cost_of_revenue_sum / accounts_payable_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Payables Turnover {e}")
            return None

    def _calculate_cash_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            cash = pd.to_numeric(data["Cash"], errors="coerce").fillna(0).to_numpy()
            current_liabilities = pd.to_numeric(data["Current Liabilities"], errors="coerce").fillna(0).to_numpy()

            cash_sum = np.sum(cash, axis=0)
            current_liabilities_sum = np.sum(current_liabilities, axis=0)

            return cash_sum / current_liabilities_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Cash Ratio {e}")
            return None

    def _calculate_cash_conversion_cycle(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            inventory = pd.to_numeric(data["Inventory"], errors="coerce").fillna(0).to_numpy()
            receivables = pd.to_numeric(data["Receivables"], errors="coerce").fillna(0).to_numpy()
            payables = pd.to_numeric(data["Payables"], errors="coerce").fillna(0).to_numpy()

            inventory_sum = np.sum(inventory, axis=0)
            receivables_sum = np.sum(receivables, axis=0)
            payables_sum = np.sum(payables, axis=0)

            return inventory_sum + receivables_sum - payables_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Cash Conversion Cycle {e}")
            return None

    def _calculate_free_cash_flow(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            operating_cf = pd.to_numeric(data["Operating CF"], errors="coerce").fillna(0).to_numpy()
            capex = pd.to_numeric(data["Capex"], errors="coerce").fillna(0).to_numpy()

            operating_cf_sum = np.sum(operating_cf, axis=0)
            capex_sum = np.sum(capex, axis=0)

            return operating_cf_sum - capex_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Free Cash Flow {e}")
            return None

    def _calculate_operating_cash_flow_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            operating_cf = pd.to_numeric(data["Operating CF"], errors="coerce").fillna(0).to_numpy()
            current_liabilities = pd.to_numeric(data["Current Liabilities"], errors="coerce").fillna(0).to_numpy()

            operating_cf_sum = np.sum(operating_cf, axis=0)
            current_liabilities_sum = np.sum(current_liabilities, axis=0)

            return operating_cf_sum / current_liabilities_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Operating Cash Flow Ratio {e}")
            return None

    def _calculate_capex_to_revenue(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            capex = pd.to_numeric(data["Capex"], errors="coerce").fillna(0).to_numpy()
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()

            capex_sum = np.sum(capex, axis=0)
            total_revenue_sum = np.sum(total_revenue, axis=0)

            return capex_sum / total_revenue_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Capex to Revenue {e}")
            return None

    def _calculate_debt_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            total_liabilities = pd.to_numeric(data["Total Liabilities"], errors="coerce").fillna(0).to_numpy()
            total_assets = pd.to_numeric(data["Total Assets"], errors="coerce").fillna(0).to_numpy()

            total_liabilities_sum = np.sum(total_liabilities, axis=0)
            total_assets_sum = np.sum(total_assets, axis=0)

            return total_liabilities_sum / total_assets_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Debt Ratio {e}")
            return None

    def _calculate_interest_coverage_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            operating_income = pd.to_numeric(data["Operating Income"], errors="coerce").fillna(0).to_numpy()
            interest_expense = pd.to_numeric(data["Interest Expense"], errors="coerce").fillna(0).to_numpy()

            operating_income_sum = np.sum(operating_income, axis=0)
            interest_expense_sum = np.sum(interest_expense, axis=0)

            return operating_income_sum / interest_expense_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Interest Coverage Ratio {e}")
            return None

    def _calculate_earnings_per_share(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            net_income = pd.to_numeric(data["Net Income"], errors="coerce").fillna(0).to_numpy()
            diluted_average_shares = pd.to_numeric(data["Diluted Average Shares"], errors="coerce").fillna(0).to_numpy()

            net_income_sum = np.sum(net_income, axis=0)
            diluted_average_shares_sum = np.sum(diluted_average_shares, axis=0)

            return net_income_sum / diluted_average_shares_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Earnings Per Share {e}")
            return None

    def _calculate_price_to_earnings_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            share_price = pd.to_numeric(data["Share Price"], errors="coerce").fillna(0).to_numpy()
            eps = pd.to_numeric(data["EPS"], errors="coerce").fillna(0).to_numpy()

            share_price_sum = np.sum(share_price, axis=0)
            eps_sum = np.sum(eps, axis=0)

            return share_price_sum / eps_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Price to Earnings Ratio {e}")
            return None

    def _calculate_book_value_per_share(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            shareholder_equity = pd.to_numeric(data["Shareholder Equity"], errors="coerce").fillna(0).to_numpy()
            number_of_shares = pd.to_numeric(data["Number of Shares"], errors="coerce").fillna(0).to_numpy()

            shareholder_equity_sum = np.sum(shareholder_equity, axis=0)
            number_of_shares_sum = np.sum(number_of_shares, axis=0)

            return shareholder_equity_sum / number_of_shares_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Book Value per Share {e}")
            return None

    def _calculate_dividend_payout_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            dividends = pd.to_numeric(data["Dividends"], errors="coerce").fillna(0).to_numpy()
            net_income = pd.to_numeric(data["Net Income"], errors="coerce").fillna(0).to_numpy()

            dividends_sum = np.sum(dividends, axis=0)
            net_income_sum = np.sum(net_income, axis=0)

            return dividends_sum / net_income_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Dividend Payout Ratio {e}")
            return None

    def _calculate_dividend_yield(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            dividend_per_share = pd.to_numeric(data["Dividend per Share"], errors="coerce").fillna(0).to_numpy()
            share_price = pd.to_numeric(data["Share Price"], errors="coerce").fillna(0).to_numpy()

            dividend_per_share_sum = np.sum(dividend_per_share, axis=0)
            share_price_sum = np.sum(share_price, axis=0)

            return dividend_per_share_sum / share_price_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Dividend Yield {e}")
            return None

    def _calculate_total_asset_turnover(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()
            total_assets = pd.to_numeric(data["Total Assets"], errors="coerce").fillna(0).to_numpy()

            total_revenue_sum = np.sum(total_revenue, axis=0)
            total_assets_sum = np.sum(total_assets, axis=0)

            return total_revenue_sum / total_assets_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Total Asset Turnover {e}")
            return None

    def _calculate_fixed_asset_turnover(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()
            net_ppe = pd.to_numeric(data["Net PPE"], errors="coerce").fillna(0).to_numpy()

            total_revenue_sum = np.sum(total_revenue, axis=0)
            net_ppe_sum = np.sum(net_ppe, axis=0)

            return total_revenue_sum / net_ppe_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Fixed Asset Turnover {e}")
            return None

    def _calculate_revenue_growth_rate(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            revenue_this_year = pd.to_numeric(data["Revenue This Year"], errors="coerce").fillna(0).to_numpy()
            revenue_last_year = pd.to_numeric(data["Revenue Last Year"], errors="coerce").fillna(0).to_numpy()

            revenue_this_year_sum = np.sum(revenue_this_year, axis=0)
            revenue_last_year_sum = np.sum(revenue_last_year, axis=0)

            return (revenue_this_year_sum - revenue_last_year_sum) / revenue_last_year_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Revenue Growth Rate {e}")
            return None

    def _calculate_net_income_growth_rate(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            net_income_ty = pd.to_numeric(data["Net Income TY"], errors="coerce").fillna(0).to_numpy()
            net_income_ly = pd.to_numeric(data["Net Income LY"], errors="coerce").fillna(0).to_numpy()

            net_income_ty_sum = np.sum(net_income_ty, axis=0)
            net_income_ly_sum = np.sum(net_income_ly, axis=0)

            return (net_income_ty_sum - net_income_ly_sum) / net_income_ly_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Net Income Growth Rate {e}")
            return None

    def _calculate_operating_income_growth(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            opinc_ty = pd.to_numeric(data["OpInc TY"], errors="coerce").fillna(0).to_numpy()
            opinc_ly = pd.to_numeric(data["OpInc LY"], errors="coerce").fillna(0).to_numpy()

            opinc_ty_sum = np.sum(opinc_ty, axis=0)
            opinc_ly_sum = np.sum(opinc_ly, axis=0)

            return (opinc_ty_sum - opinc_ly_sum) / opinc_ly_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Operating Income Growth {e}")
            return None

    def _calculate_rd_to_revenue(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            rd_expense = pd.to_numeric(data["R&D Expense"], errors="coerce").fillna(0).to_numpy()
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()

            rd_expense_sum = np.sum(rd_expense, axis=0)
            total_revenue_sum = np.sum(total_revenue, axis=0)

            return rd_expense_sum / total_revenue_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating R&D to Revenue {e}")
            return None

    def _calculate_sga_to_revenue(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            sga = pd.to_numeric(data["SG&A"], errors="coerce").fillna(0).to_numpy()
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()

            sga_sum = np.sum(sga, axis=0)
            total_revenue_sum = np.sum(total_revenue, axis=0)

            return sga_sum / total_revenue_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating SG&A to Revenue {e}")
            return None

    def _calculate_interest_expense_to_revenue(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            interest_expense = pd.to_numeric(data["Interest Expense"], errors="coerce").fillna(0).to_numpy()
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()

            interest_expense_sum = np.sum(interest_expense, axis=0)
            total_revenue_sum = np.sum(total_revenue, axis=0)

            return interest_expense_sum / total_revenue_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Interest Expense to Revenue {e}")
            return None

    def _calculate_net_ppe_to_total_assets(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            net_ppe = pd.to_numeric(data["Net PPE"], errors="coerce").fillna(0).to_numpy()
            total_assets = pd.to_numeric(data["Total Assets"], errors="coerce").fillna(0).to_numpy()

            net_ppe_sum = np.sum(net_ppe, axis=0)
            total_assets_sum = np.sum(total_assets, axis=0)

            # Handle division by zero
            if total_assets_sum == 0 or pd.isna(total_assets_sum):
                current_app.logger.warning("Net PPE to Total Assets: Division by zero - Total Assets is zero or NaN")
                return 0.0

            return net_ppe_sum / total_assets_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Net PPE to Total Assets {e}")
            return None

    def _calculate_intangibles_to_total_assets(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            intangibles = pd.to_numeric(data["Intangibles"], errors="coerce").fillna(0).to_numpy()
            total_assets = pd.to_numeric(data["Total Assets"], errors="coerce").fillna(0).to_numpy()

            intangibles_sum = np.sum(intangibles, axis=0)
            total_assets_sum = np.sum(total_assets, axis=0)

            return intangibles_sum / total_assets_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Intangibles to Total Assets {e}")
            return None

    def _calculate_goodwill_to_total_assets(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            goodwill = pd.to_numeric(data["Goodwill"], errors="coerce").fillna(0).to_numpy()
            total_assets = pd.to_numeric(data["Total Assets"], errors="coerce").fillna(0).to_numpy()

            goodwill_sum = np.sum(goodwill, axis=0)
            total_assets_sum = np.sum(total_assets, axis=0)

            # Handle division by zero
            if total_assets_sum == 0 or pd.isna(total_assets_sum):
                current_app.logger.warning("Goodwill to Total Assets: Division by zero - Total Assets is zero or NaN")
                return 0.0

            return goodwill_sum / total_assets_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Goodwill to Total Assets {e}")
            return None

    def _calculate_capital_expenditure_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            capex = pd.to_numeric(data["Capex"], errors="coerce").fillna(0).to_numpy()
            total_assets = pd.to_numeric(data["Total Assets"], errors="coerce").fillna(0).to_numpy()

            capex_sum = np.sum(capex, axis=0)
            total_assets_sum = np.sum(total_assets, axis=0)

            return capex_sum / total_assets_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Capital Expenditure Ratio {e}")
            return None

    def _calculate_operating_expense_ratio(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            operating_expense = pd.to_numeric(data["Operating Expense"], errors="coerce").fillna(0).to_numpy()
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()

            operating_expense_sum = np.sum(operating_expense, axis=0)
            total_revenue_sum = np.sum(total_revenue, axis=0)

            return operating_expense_sum / total_revenue_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Operating Expense Ratio {e}")
            return None

    def _calculate_tax_burden(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            tax_provision = pd.to_numeric(data["Tax Provision"], errors="coerce").fillna(0).to_numpy()
            pretax_income = pd.to_numeric(data["Pretax Income"], errors="coerce").fillna(0).to_numpy()

            tax_provision_sum = np.sum(tax_provision, axis=0)
            pretax_income_sum = np.sum(pretax_income, axis=0)

            return tax_provision_sum / pretax_income_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Tax Burden {e}")
            return None

    def _calculate_long_term_debt_to_equity(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            long_term_debt = pd.to_numeric(data["Long-Term Debt"], errors="coerce").fillna(0).to_numpy()
            shareholder_equity = pd.to_numeric(data["Shareholder Equity"], errors="coerce").fillna(0).to_numpy()

            long_term_debt_sum = np.sum(long_term_debt, axis=0)
            shareholder_equity_sum = np.sum(shareholder_equity, axis=0)

            return long_term_debt_sum / shareholder_equity_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Long-Term Debt to Equity {e}")
            return None

    def _calculate_total_liabilities_to_equity(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            total_liabilities = pd.to_numeric(data["Total Liabilities"], errors="coerce").fillna(0).to_numpy()
            equity = pd.to_numeric(data["Equity"], errors="coerce").fillna(0).to_numpy()

            total_liabilities_sum = np.sum(total_liabilities, axis=0)
            equity_sum = np.sum(equity, axis=0)

            return total_liabilities_sum / equity_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Total Liabilities to Equity {e}")
            return None

    def _calculate_cash_flow_to_net_income(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            operating_cf = pd.to_numeric(data["Operating CF"], errors="coerce").fillna(0).to_numpy()
            net_income = pd.to_numeric(data["Net Income"], errors="coerce").fillna(0).to_numpy()

            operating_cf_sum = np.sum(operating_cf, axis=0)
            net_income_sum = np.sum(net_income, axis=0)

            return operating_cf_sum / net_income_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Cash Flow to Net Income {e}")
            return None

    def _calculate_cash_flow_margin(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # If any data value is NAN replace with Zero
            operating_cf = pd.to_numeric(data["Operating CF"], errors="coerce").fillna(0).to_numpy()
            total_revenue = pd.to_numeric(data["Total Revenue"], errors="coerce").fillna(0).to_numpy()

            operating_cf_sum = np.sum(operating_cf, axis=0)
            total_revenue_sum = np.sum(total_revenue, axis=0)

            return operating_cf_sum / total_revenue_sum

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured During Calculating Cash Flow Margin {e}")
            return None

    def _calculate_days_payable_outstanding(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # DPO ≈ 365 * Average Accounts Payable / Cost of Revenue
            accounts_payable = pd.to_numeric(data["Accounts Payable"], errors="coerce").fillna(0).to_numpy()
            cost_of_revenue = pd.to_numeric(data["Cost of Revenue"], errors="coerce").fillna(0).to_numpy()

            accounts_payable_sum = np.sum(accounts_payable, axis=0)
            cost_of_revenue_sum = np.sum(cost_of_revenue, axis=0)

            if cost_of_revenue_sum == 0:
                current_app.logger.error("Division by zero in DPO: Cost of Revenue total is 0")
                return None

            return (accounts_payable_sum / cost_of_revenue_sum) * 365

        except Exception as e:
            current_app.logger.error(f"Error occurred During Calculating Days Payable Outstanding (DPO) {e}")
            return None

    def _calculate_budget_variance(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # Budget Variance = (Actual - Budget) / Budget
            actual = pd.to_numeric(data["Actual Results"], errors="coerce").fillna(0).to_numpy()
            budget = pd.to_numeric(data["Budget"], errors="coerce").fillna(0).to_numpy()

            actual_sum = np.sum(actual, axis=0)
            budget_sum = np.sum(budget, axis=0)

            if budget_sum == 0:
                current_app.logger.error("Division by zero in Budget Variance: Budget total is 0")
                return None

            return (actual_sum - budget_sum) / budget_sum

        except Exception as e:
            current_app.logger.error(f"Error occurred During Calculating Budget Variance {e}")
            return None

    def _calculate_budget_creation_cycle_time(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # This is a placeholder - would need actual budget creation dates
            # For now, return a default value or None
            current_app.logger.warning("Budget Creation Cycle Time calculation not implemented - requires budget creation dates")
            return None

        except Exception as e:
            current_app.logger.error(f"Error occurred During Calculating Budget Creation Cycle Time {e}")
            return None

    def _calculate_line_items_in_budget(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # Count non-zero budget items
            budget_columns = [col for col in data.columns if 'budget' in col.lower() or 'Budget' in col]
            if not budget_columns:
                current_app.logger.warning("No budget columns found for Line Items in Budget calculation")
                return None

            line_items_count = 0
            for col in budget_columns:
                budget_values = pd.to_numeric(data[col], errors="coerce").fillna(0).to_numpy()
                if np.any(budget_values > 0):
                    line_items_count += 1

            return line_items_count

        except Exception as e:
            current_app.logger.error(f"Error occurred During Calculating Line Items in Budget {e}")
            return None

    def _calculate_number_of_budget_iterations(self, data: pd.DataFrame, required_cols: set):
        try:
            # Safety check
            if not set(required_cols).issubset(data.columns):
                missing = required_cols - set(data.columns)
                current_app.logger.error(f"Missing Required Columns: {missing}")
                return None

            # This is a placeholder - would need budget version history
            # For now, return a default value or None
            current_app.logger.warning("Number of Budget Iterations calculation not implemented - requires budget version history")
            return None

        except Exception as e:
            current_app.logger.error(f"Error occurred During Calculating Number of Budget Iterations {e}")
            return None




class FileKPICalculationEngine:
    def __init__(self):
        self.db = db
        self.file_reader = FileDataReader()
        self.kpi_calculator = KPICalculation()
        self.save_kpi_info = SaveKPI()

    def _get_file_info(self,file_id:str) -> Dict[str,str]:
        file_record = FinancialFile.query.filter_by(file_id=file_id).first()

        if not file_record:
            raise Exception(f"File not found {file_id}")

        return {
            'file_id': file_record.file_id,
            'file_name': file_record.file_name,
            'file_type': file_record.file_type,
            'file_path': file_record.processed_file_path or file_record.file_path,
            'upload_id': file_record.upload_id
        }

        # test
        # current_app.logger.info(f"getting file_info for file_id{file_id}")

        # return {
        #     'file_id': UUID('8c73b85b-29d8-45e9-8d8c-f35ceea8369d'),
        #     'file_name': "Test kpi file - Sheet1.csv",
        #     'file_type': ".csv",
        #     'file_path': 'C:\\Users\\91835\\Desktop\\LeadGenAI\\uploads\\Test kpi file - Sheet1.csv',
        #     'upload_id': UUID('e5c2bcfd-3ff5-48d1-8c2c-4776ae0861c2')
        # }


    def _get_files_in_upload(self,upload_id:str) ->List[str]:
        try:
            files:FinancialFile = FinancialFile.query.filter_by(
                upload_id=upload_id
            ).all()

            current_app.logger.info(f"Successfully Fetched files with upload_id{upload_id}")
            return [f.file_id for f in files]
        except Exception as e:
            current_app.logger.error(f"Error in fetching the files with upload id:{upload_id}")

        # # for testing
        # return UUID('e5c2bcfd-3ff5-48d1-8c2c-4776ae0861c2')

    def _read_file_data(self,file_info) -> pd.DataFrame:
        """Read file data from 'normalized' stage using FilePersistenceManager"""

        file_manager = FilePersistenceManager()
        normalized_path = file_manager.get_stage_file_path(str(file_info['file_id']), 'normalized')
        if not normalized_path or not os.path.exists(normalized_path):
            current_app.logger.info(f"Normalized file not found for file_id {file_info['file_id']}")
            raise FileNotFoundError(f"Normalized file not found for file_id: {file_info['file_id']}")

        current_app.logger.info(f"Reading normalized file for KPI: {normalized_path}")
        return self.file_reader.read_file_data(normalized_path)


    # def _get_applicable_kpis(self,file_type:str) -> List[str]:

    #     applicable_kpis = []
    #     try:
    #     # Fetching the kpi_name
    #         kpis  = self.db.session.query(
    #             KPIDefinitions.kpi_name,
    #             KPIDefinitions.kpi_file_type, # File_type should come here
    #         ).all()
    #     except Exception as e:
    #         current_app.logger.info(f"Error in Fetching from kpi definations table {e}")
    #         return None
    #     try:
    #         # Converting the tuples into dictionary
    #         Kpi_definations = {
    #             kpi_name:[kpi_file_type] # [balance sheet,Income sheet]
    #             for kpi_name,kpi_file_type in kpis
    #         }

    #         for kpi_name,kpi_file_type in Kpi_definations.items():
    #             if file_type in kpi_file_type:
    #                 applicable_kpis.append(kpi_name)


    #         current_app.logger.info(f"Applicable KPI's for {file_type}:{applicable_kpis}")
    #         return applicable_kpis

    #     except Exception as e:
    #         current_app.logger.error(f"[finance_kpi_controller] Error occred during _get_applicable_kpi,{e}")
    #         return None



    def _check_calculable_kpis(self,available_columns):
        calculable_kpis =[] # Kpis for which we have the columns
        failed_kpis = [] # kpis for which we don't have the columns and we cannot caculate it

        try:

            # Fetch all kpis all columns
            try:
                required_columns = db.session.query(
                    KPIDefinitions.kpi_name,
                    KPIDefinitions.required_columns
                ).filter(KPIDefinitions.is_active == True).all()

                if required_columns:
                    kpis_with_req_cols = {name:set(cols) for name,cols in required_columns}
                current_app.logger.info("[finance_kpi_controller] Successfully fetched the kpi names and colums for _check_caculable kpis")

            except Exception as e:
                current_app.logger.error(f"[finance_kpi_controller] Error fetching required columns for kpi {e}")

            for kpi_name,required_columns in kpis_with_req_cols.items():

                if required_columns:
                    missing_columns =  required_columns - available_columns

                    if not missing_columns:
                        calculable_kpis.append(kpi_name)

                    else:
                        failed_kpis.append({
                            "kpi_name":kpi_name,
                            "failed_kpis":len(missing_columns)
                        })

            current_app.logger.info(f"[finance_kpi_controller] Total Caculable Kpis - {len(calculable_kpis)}")
            return calculable_kpis,failed_kpis

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occured during Checking Calculable kpis {e}")


    def _calculate_kpis(self,calculable_kpis:List[str],file_data:pd.DataFrame,file_id:str,file_type:str,upload_id=None):
        if not calculable_kpis:
            current_app.logger.warning(f"No calculable KPIs provided for file {file_id}")
            return []

        calculated_results = []

        # For calculation whats need to be passed file_data,needed columns(required cols for calcualting the kpi)
        try:
            rows = db.session.query(
                    KPIDefinitions.kpi_name,
                    KPIDefinitions.required_columns,
                    KPIDefinitions.kpi_category
                ).filter(KPIDefinitions.kpi_name.in_(calculable_kpis)).all()

            current_app.logger.info(f"[finance_kpi_controller] Fetched from KPIDefinations table kpi_name and required")
            kpi_requirements = {kpi_name:
                                {'required_col':required_col,
                                 'kpi_category':kpi_category
                                 } for kpi_name,required_col,kpi_category in rows}

        except Exception as e:
                current_app.logger.error(f"[finance_kpi_controller] Error fetching required columns for kpi{e}")
                return None

        try:
            for kpi_name,kpi_details in kpi_requirements.items():
                start_time = datetime.now()

                required_cols = kpi_details['required_col']
                kpi_category = kpi_details['kpi_category']

                try:
                    result = self.kpi_calculator.calculate_kpi(kpi_name, file_data,required_cols=required_cols)
                    if result is not None:
                        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                        kpi_result = {
                            "kpi_name":kpi_name,
                            "value" :float(result),
                            "file_id" : file_id,
                            "file_type":file_type,
                            "kpi_category":kpi_category,
                            "processing_time_ms":processing_time,
                            "calculation_status":"calculated"
                        }
                        calculated_results.append(kpi_result)
                    else:
                        current_app.logger.error(f"Falied to calcualte the kpi for {kpi_name}")
                        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                        calculated_results.append({
                            "kpi_name":kpi_name,
                            "value": None,
                            "file_id": file_id,
                            "file_type": file_type,
                            "kpi_category": kpi_category,
                            "processing_time_ms": processing_time,
                            "calculation_status": "failed",
                            "error_message": "Computation returned None"
                        })
                except Exception as calc_err:
                    current_app.logger.error(f"[finance_kpi_calculation] Error occured during Calculating Kpi {kpi_name}: {calc_err}")
                    processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
                    calculated_results.append({
                        "kpi_name":kpi_name,
                        "value": None,
                        "file_id": file_id,
                        "file_type": file_type,
                        "kpi_category": kpi_category,
                        "processing_time_ms": processing_time,
                        "calculation_status": "failed",
                        "error_message": str(calc_err)
                    })

            return calculated_results

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_calculation] Error occured during kpi calculation{e}")
            return calculated_results


    def calculate_file_kpi(self,file_id):
        start_time = datetime.now()

        try:
            # Get file information
            file_info = self._get_file_info(file_id)
            current_app.logger.info("[debug] get_file_info completed")

            # Read file data from normalized stage
            file_manager = FilePersistenceManager()
            normalized_path = file_manager.get_stage_file_path(str(file_info['file_id']), 'normalized')
            if not normalized_path or not os.path.exists(normalized_path):
                current_app.logger.error(f"Normalized file not found for file_id: {file_id}")
                raise FileNotFoundError(f"Normalized file not found for file_id: {file_id}")
            file_data = self.file_reader.read_file_data(normalized_path)

            # Get applicable KPIs for this file type
            # applicable_kpis = self._get_applicable_kpis(file_info['file_type'])


            # Give a list all kpis are possible.

            # Check which KPIs can be calculated with available columns
            available_columns = set(file_data.columns)
            calculable_kpis, failed_kpis = self._check_calculable_kpis(available_columns)

            # Calculate KPIs with better error handling
            calculated_results = []
            failed_calculations = []

            for kpi_name in calculable_kpis:
                try:
                    start_time_kpi = datetime.now()

                    # Get KPI requirements
                    kpi_requirement = db.session.query(
                        KPIDefinitions.required_columns,
                        KPIDefinitions.kpi_category
                    ).filter(KPIDefinitions.kpi_name == kpi_name).first()

                    if not kpi_requirement:
                        failed_calculations.append({
                            "kpi_name": kpi_name,
                            "error": "KPI definition not found in database",
                            "calculation_status": "failed"
                        })
                        continue

                    required_cols = kpi_requirement.required_columns
                    kpi_category = kpi_requirement.kpi_category

                    # Calculate the KPI
                    result = self.kpi_calculator.calculate_kpi(kpi_name, file_data, required_cols=required_cols)

                    processing_time_kpi = int((datetime.now() - start_time_kpi).total_seconds() * 1000)

                    if result is not None:
                        calculated_results.append({
                            "kpi_name": kpi_name,
                            "value": float(result),
                            "file_id": str(file_id),
                            "file_type": file_info['file_type'],
                            "kpi_category": kpi_category,
                            "processing_time_ms": processing_time_kpi,
                            "calculation_status": "calculated",
                            "error_message": None
                        })
                    else:
                        # Check for specific calculation issues
                        error_msg = self._get_calculation_error_details(kpi_name, file_data, required_cols)
                        failed_calculations.append({
                            "kpi_name": kpi_name,
                            "error": error_msg,
                            "calculation_status": "failed",
                            "processing_time_ms": processing_time_kpi
                        })

                except Exception as calc_err:
                    processing_time_kpi = int((datetime.now() - start_time_kpi).total_seconds() * 1000)
                    failed_calculations.append({
                        "kpi_name": kpi_name,
                        "error": str(calc_err),
                        "calculation_status": "failed",
                        "processing_time_ms": processing_time_kpi
                    })
                    current_app.logger.error(f"Failed to calculate KPI {kpi_name}: {calc_err}")


            # Calculate processing time
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Create simplified summary
            summary = {
                "file_id": str(file_id),
                "file_name": file_info.get('file_name', 'Unknown'),
                "file_type": file_info["file_type"],
                "upload_id": str(file_info['upload_id']),
                "total_calculable_kpis": len(calculable_kpis),
                "total_missing_columns_kpis": len(failed_kpis),
                "successful_calculations": len(calculated_results),
                "failed_calculations": len(failed_calculations),
                "calculable_kpis": calculable_kpis,
                "failed_calculations_details": failed_calculations,
                "kpi_calculation_results": calculated_results,
                "processing_time": processing_time,
                "calculation_status": "completed" if calculated_results else "failed"
            }

            # Persist outputs in 'kpi_calculated' stage using FilePersistenceManager
            original_filename = os.path.basename(normalized_path)
            root, _ext = os.path.splitext(original_filename)
            kpi_results_filename = f"{root}_kpi_results.csv"

            # Persist all calculated KPIs as CSV (persistent stage file)
            results_df = pd.DataFrame(calculated_results or [])
            kpi_results_path = file_manager.save_stage_file(
                file_id=str(file_info['file_id']),
                stage_name='kpi_calculated',
                data=results_df,
                original_filename=kpi_results_filename,
                metadata={
                    'stage': 'kpi_calculated',
                    'source_stage_path': normalized_path,
                    'rows': len(results_df.index) if not results_df.empty else 0
                }
            )

            # Save KPI summary JSON into metadata directory
            kpi_summary_path = file_manager.save_metadata_json(
                file_id=str(file_info['file_id']),
                filename='kpi_summary.json',
                payload=summary
            )

            # Update DB processed_file_path (to KPI results CSV) and status to 'kpi_calculated'
            old_path = file_info.get('file_path')
            updated = file_manager.update_db_file_path(
                file_id=str(file_info['file_id']),
                stage_name='kpi_calculated',
                file_path=kpi_results_path
            )
            if not updated:
                current_app.logger.error(f"Failed to update DB processed_file_path for file_id={file_id}")

            # Save KPI rows to DB in a single commit per file
            try:
                # Build FinancialKPI records
                kpi_records = []
                upload_id = file_info['upload_id']
                for idx, item in enumerate(calculated_results or []):
                    kpi_records.append(
                        FinancialKPI(
                            upload_id=upload_id,
                            kpi_name=item.get('kpi_name'),
                            kpi_category=item.get('kpi_category'),
                            kpi_value=item.get('value'),
                            kpi_unit=item.get('kpi_unit'),
                            calculation_status=item.get('calculation_status') or 'calculated',
                            threshold_status=item.get('threshold_status'),
                            industry_benchmark=item.get('industry_benchmark'),
                            benchmark_source=item.get('benchmark_source'),
                            calculation_notes=item.get('calculation_notes'),
                            error_message=item.get('error_message'),
                            dependencies_satisfied=item.get('dependencies_satisfied', True),
                            calculation_duration_ms=item.get('processing_time_ms'),
                            calculation_order=item.get('calculation_order')
                        )
                    )

                if kpi_records:
                    db.session.add_all(kpi_records)
                    db.session.commit()
                    current_app.logger.info(f"Saved {len(kpi_records)} KPI rows for upload_id={upload_id}")
                else:
                    current_app.logger.info("No KPI rows to save.")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Failed to save KPI rows: {e}")

            current_app.logger.info(f"KPI calculation for file_id {file_id} has been completed; paths: results={kpi_results_path}, summary={kpi_summary_path}")

            # Extend response with persisted paths
            summary.update({
                'kpi_results_path': file_manager.to_relative_path(kpi_results_path),
                'kpi_summary_path': file_manager.to_relative_path(kpi_summary_path)
            })

            return summary
        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] KPI calculation failed for file_id:{file_id}")
            # Return error summary instead of raising
            return {
                "file_id": str(file_id),
                "file_name": "Unknown",
                "file_type": "unknown",
                "upload_id": "unknown",
                "total_calculable_kpis": 0,
                "total_missing_columns_kpis": 0,
                "successful_calculations": 0,
                "failed_calculations": 0,
                "calculable_kpis": [],
                "failed_calculations_details": [],
                "kpi_calculation_results": [],
                "processing_time": 0,
                "calculation_status": "error",
                "error_message": str(e),
                "kpi_results_path": None,
                "kpi_summary_path": None
            }

    def _get_calculation_error_details(self, kpi_name: str, file_data: pd.DataFrame, required_cols: set) -> str:
        """Get specific error details for KPI calculation failures"""
        try:
            # Check if required columns are missing
            missing_cols = required_cols - set(file_data.columns)
            if missing_cols:
                return f"Missing required columns: {', '.join(missing_cols)}"

            # Check for zero division issues
            if kpi_name in ["Net Profit Margin", "Gross Profit Margin", "Operating Profit Margin", "EBITDA Margin"]:
                if "Total Revenue" in file_data.columns:
                    total_revenue = pd.to_numeric(file_data["Total Revenue"], errors="coerce").fillna(0).sum()
                    if total_revenue == 0:
                        return "Total Revenue is zero - cannot calculate margin ratios"

            elif kpi_name in ["Return on Assets (ROA)", "Return on Equity (ROE)"]:
                if kpi_name == "Return on Assets (ROA)" and "Total Assets" in file_data.columns:
                    total_assets = pd.to_numeric(file_data["Total Assets"], errors="coerce").fillna(0).sum()
                    if total_assets == 0:
                        return "Total Assets is zero - cannot calculate ROA"
                elif kpi_name == "Return on Equity (ROE)" and "Shareholder Equity" in file_data.columns:
                    shareholder_equity = pd.to_numeric(file_data["Shareholder Equity"], errors="coerce").fillna(0).sum()
                    if shareholder_equity == 0:
                        return "Shareholder Equity is zero - cannot calculate ROE"

            elif kpi_name in ["Current Ratio", "Quick Ratio", "Cash Ratio"]:
                if "Current Liabilities" in file_data.columns:
                    current_liabilities = pd.to_numeric(file_data["Current Liabilities"], errors="coerce").fillna(0).sum()
                    if current_liabilities == 0:
                        return "Current Liabilities is zero - cannot calculate ratio"

            elif kpi_name in ["Inventory Turnover", "Days Inventory Outstanding (DIO)"]:
                if "Inventory" in file_data.columns:
                    inventory = pd.to_numeric(file_data["Inventory"], errors="coerce").fillna(0).sum()
                    if inventory == 0:
                        return "Inventory is zero - cannot calculate turnover ratios"

            elif kpi_name in ["Receivables Turnover", "Accounts Receivable Turnover"]:
                if "Accounts Receivable" in file_data.columns:
                    accounts_receivable = pd.to_numeric(file_data["Accounts Receivable"], errors="coerce").fillna(0).sum()
                    if accounts_receivable == 0:
                        return "Accounts Receivable is zero - cannot calculate turnover"

            elif kpi_name in ["Payables Turnover", "Accounts Payable Turnover"]:
                if "Accounts Payable" in file_data.columns:
                    accounts_payable = pd.to_numeric(file_data["Accounts Payable"], errors="coerce").fillna(0).sum()
                    if accounts_payable == 0:
                        return "Accounts Payable is zero - cannot calculate turnover"

            # Generic error for other cases
            return "Calculation failed due to invalid data or mathematical error"

        except Exception as e:
            return f"Error analyzing calculation failure: {str(e)}"


    def calculate_upload_kpi(self, upload_id: str):
        start_time = datetime.now()

        try:
            file_ids = self._get_files_in_upload(upload_id=upload_id)
            file_summaries = []
            failed_files = []

            for file_id in file_ids:
                try:
                    file_summary = self.calculate_file_kpi(file_id=file_id)
                    file_summaries.append(file_summary)

                except Exception as e:
                    current_app.logger.error(f" [finance_kpi_controller] Error to process file {file_id}:{e}")
                    failed_files.append({
                        "file_id": str(file_id),
                        "error": str(e),
                        "status": "failed"
                    })

            current_app.logger.info(f"[finance_kpi_controller] Upload KPI calculation completed for upload_id:{upload_id}")
            processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
            # Identify failures that returned structured error summaries
            structured_failed_files = []
            for summary in file_summaries:
                if summary.get("calculation_status") == "error":
                    structured_failed_files.append({
                        "file_id": str(summary.get("file_id")),
                        "error": summary.get("error_message") or "KPI calculation failed",
                        "status": "failed"
                    })

            if structured_failed_files:
                failed_files.extend(structured_failed_files)

            # Calculate upload-level summary
            total_calculable_kpis = sum(f.get('total_calculable_kpis', 0) for f in file_summaries)
            total_missing_columns_kpis = sum(f.get('total_missing_columns_kpis', 0) for f in file_summaries)
            total_successful_calculations = sum(f.get('successful_calculations', 0) for f in file_summaries)
            total_failed_calculations = sum(f.get('failed_calculations', 0) for f in file_summaries)
            # Determine overall status
            has_failures = len(failed_files) > 0
            has_successes = len(file_summaries) > 0 and any(f.get('calculation_status') == 'calculated' or f.get('successful_calculations', 0) > 0 for f in file_summaries)
            if has_failures and has_successes:
                overall_status = "partial"
            elif has_failures and not has_successes:
                overall_status = "failed"
            else:
                overall_status = "completed"

            # NEW: Calculate historical KPIs after regular KPI calculation
            historical_kpi_result = None
            try:
                from controllers.finance_report_gen.historical_kpi_controller import HistoricalKPIController
                historical_controller = HistoricalKPIController()
                historical_kpi_result = historical_controller.calculate_historical_kpis(upload_id)
                current_app.logger.info(f"[finance_kpi_controller] Historical KPI calculation completed for upload_id:{upload_id}")
            except Exception as hist_e:
                current_app.logger.error(f"[finance_kpi_controller] Error in historical KPI calculation: {str(hist_e)}")
                historical_kpi_result = {
                    "success": False,
                    "error": str(hist_e)
                }

            return {
                "upload_id": upload_id,
                "upload_summary": {
                    "total_files": len(file_ids),
                    "successful_files": max(len(file_summaries) - len(structured_failed_files), 0) if file_summaries else 0,
                    "failed_files_count": len(failed_files),
                    "total_calculable_kpis": total_calculable_kpis,
                    "total_missing_columns_kpis": total_missing_columns_kpis,
                    "total_successful_calculations": total_successful_calculations,
                    "total_failed_calculations": total_failed_calculations,
                    "processing_time": processing_time,
                    "overall_status": overall_status
                },
                "file_summaries": file_summaries,
                "failed_files": failed_files,
                "historical_kpis": historical_kpi_result  # NEW: Include historical KPI results
            }

        except Exception as e:
            current_app.logger.error(f"[finance_kpi_controller] Error occurred for upload_id{upload_id}")
            return {
                "upload_id": upload_id,
                "upload_summary": {
                    "total_files": 0,
                    "successful_files": 0,
                    "failed_files_count": 0,
                    "total_calculable_kpis": 0,
                    "total_missing_columns_kpis": 0,
                    "total_successful_calculations": 0,
                    "total_failed_calculations": 0,
                    "processing_time": 0,
                    "overall_status": "error"
                },
                "file_summaries": [],
                "failed_files": [],
                "error_message": str(e),
                "historical_kpis": None
            }

        # def _get_applicable_kpis(self,file_type:str) -> List[str]:

    #     applicable_kpis = []
    #     try:
    #     # Fetching the kpi_name
    #         kpis  = self.db.session.query(
    #             KPIDefinitions.kpi_name,
    #             KPIDefinitions.kpi_file_type, # File_type should come here
    #         ).all()
    #     except Exception as e:
    #         current_app.logger.info(f"Error in Fetching from kpi definations table {e}")
    #         return None
    #     try:
    #         # Converting the tuples into dictionary
    #         Kpi_definations = {
    #             kpi_name:[kpi_file_type] # [balance sheet,Income sheet]
    #             for kpi_name,kpi_file_type in kpis
    #         }

    #         for kpi_name,kpi_file_type in Kpi_definations.items():
    #             if file_type in kpi_file_type:
    #                 applicable_kpis.append(kpi_name)


    #         current_app.logger.info(f"[finance_kpi_controller] Applicable KPI's for {file_type}:{applicable_kpis}")
    #         return applicable_kpis

    #     except Exception as e:
    #         current_app.logger.error(f"[finance_kpi_controller] Error occred during _get_applicable_kpi,{e}")
    #         return None



# Class for Saving the Each calculated KPI
class SaveKPI:

    @staticmethod
    def save_calculated_kpis(data):
        try:
            if not data:
                return {
                    "success": False,
                    "error": "No data provided for saving calculated KPI"
                }

            # Add validation for critical fields
            required_fields = ['kpi_name', 'kpi_category', 'value']
            missing_fields = [field for field in required_fields if not data.get(field)]

            if missing_fields:
                return {
                    "success": False,
                    "error": f"Missing required fields: {', '.join(missing_fields)}"
                }


            kpi_record_data = {
                'upload_id': data.get('upload_id'),
                'kpi_name': data.get('kpi_name'),
                'kpi_category': data.get('kpi_category'),
                'kpi_value': data.get('value'),
                'kpi_unit': data.get('kpi_unit') or None,
                'calculation_status': data.get('calculation_status') or 'calculated',
                'threshold_status': data.get('threshold_status') or None,
                'industry_benchmark': data.get('industry_benchmark') or None,
                'benchmark_source': data.get('benchmark_source') or None,
                'calculation_notes': data.get('calculation_notes') or None,
                'error_message': data.get('error_message') or None,
                'dependencies_satisfied': data.get('dependencies_satisfied', True),
                'calculation_duration_ms': data.get('processing_time_ms'),
                'calculation_order': data.get('calculation_order') or None,
            }

            # Create new FinancialKPI record
            financial_kpi = FinancialKPI(**kpi_record_data)

            # Save to database
            db.session.add(financial_kpi)
            db.session.flush()
            db.session.commit()

            current_app.logger.info(f"[finance_kpi_controller] Successfully saved KPI: {data.get('kpi_name')} for upload_id: {data.get('upload_id')}")

            return {
                "success": True,
                "upload_id": data.get('upload_id'),
                "message": f"KPI {data.get('kpi_name')} saved successfully"
            }

        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"[finance_kpi_controller] Error saving calculated KPI: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to save KPI: {str(e)}"
            }
        finally:
            db.session.close()
