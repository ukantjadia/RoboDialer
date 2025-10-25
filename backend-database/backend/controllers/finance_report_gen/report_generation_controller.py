from typing import Dict, Any, List, Tuple
import json
import re
import uuid
from datetime import datetime
import os
import pandas as pd

from flask import current_app
from sqlalchemy import func

from models.lead_model import db
from models.finance_report_gen.financial_kpi_model import FinancialKPI
from models.finance_report_gen.industry_benchmarks_model import IndustryBenchmarks
from models.finance_report_gen.financial_report_version_model import FinancialReportVersion
from models.finance_report_gen.data_processing_errors_model import DataProcessingErrors
from models.finance_report_gen.financial_file_model import FinancialFile
from utils.llm_message_generator import GenerateController
from utils.finance_file_manager import FilePersistenceManager
from config.config import Config
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from models.finance_report_gen.kpi_historical_data_model import KPIHistoricalData
import random
from reportlab.lib.utils import ImageReader


class ReportGenerationController:
    """
    Generates a structured financial report using KPIs, industry benchmarks, and an LLM (DeepSeek).
    """

    def _group_kpis(self, kpis: List[FinancialKPI]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for k in kpis:
            cat = k.kpi_category or "Uncategorized"
            grouped.setdefault(cat, []).append({
                "kpi": k.kpi_name,
                "value": float(k.kpi_value) if k.kpi_value is not None else None,
                "unit": k.kpi_unit,
                "status": (k.threshold_status or "").replace("_", " ").title() if k.threshold_status else None,
                "calc_status": k.calculation_status
            })
        return grouped

    def _group_kpis_from_payload(self, kpi_payload: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Accepts KPI results JSON (as returned by KPI endpoint) and maps it into the grouped format.
        This function is resilient to different shapes; expected minimal shape:
        {
          "kpis": [ {"kpi_name": str, "kpi_value": number, "kpi_unit": str, "kpi_category": str, "threshold_status": str } ]
        }
        """
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        if not kpi_payload:
            return grouped
        items = []
        if isinstance(kpi_payload, dict):
            if isinstance(kpi_payload.get("kpis"), list):
                items = kpi_payload.get("kpis")
            elif isinstance(kpi_payload.get("data"), list):
                items = kpi_payload.get("data")
            else:
                # Maybe it's already grouped by category
                for cat, arr in kpi_payload.items():
                    if isinstance(arr, list):
                        for k in arr:
                            k = k or {}
                            grouped.setdefault(cat, []).append({
                                "kpi": k.get("kpi") or k.get("kpi_name"),
                                "value": k.get("value") or k.get("kpi_value"),
                                "unit": k.get("unit") or k.get("kpi_unit"),
                                "status": k.get("status") or k.get("threshold_status"),
                                "calc_status": k.get("calc_status") or k.get("calculation_status"),
                                "periodical": k.get("periodical")
                            })
                return grouped
        for k in items:
            cat = (k.get("kpi_category") or "Uncategorized")
            grouped.setdefault(cat, []).append({
                "kpi": k.get("kpi_name") or k.get("kpi"),
                "value": k.get("kpi_value") if k.get("kpi_value") is not None else k.get("value"),
                "unit": k.get("kpi_unit") or k.get("unit"),
                "status": k.get("threshold_status") or k.get("status"),
                "calc_status": k.get("calculation_status") or k.get("calc_status"),
                "periodical": k.get("periodical")
            })
        return grouped

    def _fetch_benchmarks(self, industry: str, kpi_names: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        if not kpi_names:
            return {}
        rows = IndustryBenchmarks.query.filter(
            IndustryBenchmarks.is_active.is_(True),
            IndustryBenchmarks.industry_name == industry,
            IndustryBenchmarks.kpi_name.in_(kpi_names)
        ).all()
        result: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            result.setdefault(r.kpi_name, []).append({
                "benchmark_type": r.benchmark_type,
                "value": float(r.benchmark_value) if r.benchmark_value is not None else None,
                "unit": r.benchmark_unit,
                "source": r.data_source,
                "year": r.data_year,
                "sample_size": r.sample_size,
                "confidence_level": float(r.confidence_level) if r.confidence_level is not None else None,
            })
        return result

    def _read_prompt_template(self) -> str:
        """Read the LLM prompt template from backend/data/finance_report_gen/llm_prompt_template.txt"""
        try:
            template_path = os.path.join(Config.FIN_DATA_ROOT, 'llm_prompt_template.txt')
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read()
            current_app.logger.warning(f"Prompt template missing at {template_path}; using fallback instructions")
            return ""
        except Exception:
            current_app.logger.exception("Failed to read LLM prompt template; using fallback instructions")
            return ""

    def _read_prompt_template_v1(self) -> str:
        """Read classifier agent prompt (v1) from backend/data/finance_report_gen/llm_prompt_template_1.txt"""
        try:
            template_path = os.path.join(Config.FIN_DATA_ROOT, 'llm_prompt_template_1.txt')
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read()
            current_app.logger.warning(f"Classifier prompt template missing at {template_path}; using fallback instructions")
            return ""
        except Exception:
            current_app.logger.exception("Failed to read classifier prompt template v1; using fallback instructions")
            return ""

    def _read_prompt_template_v2(self) -> str:
        """Read report writer prompt (v2) from backend/data/finance_report_gen/llm_prompt_template_2.txt"""
        try:
            template_path = os.path.join(Config.FIN_DATA_ROOT, 'llm_prompt_template_2.txt')
            if os.path.exists(template_path):
                with open(template_path, 'r', encoding='utf-8') as f:
                    return f.read()
            current_app.logger.warning(f"Report prompt template missing at {template_path}; using fallback instructions")
            return ""
        except Exception:
            current_app.logger.exception("Failed to read report prompt template v2; using fallback instructions")
            return ""

    def _build_prompt(self, company_details: Dict[str, Any], kpis: Dict[str, Any], benchmarks: Dict[str, Any]) -> str:
        schema = {
            "summary": "string",
            "insights": ["string"],
            "risks": ["string"],
            "recommendations": ["string"],
        }
        base_instructions = (
            "You are a financial analyst. Using the provided company details, KPIs grouped by category, and industry benchmarks, "
            "write a concise performance summary, highlight key insights (positives), identify risks (weak areas), and provide "
            "actionable recommendations.\n\n"
            "Return ONLY a JSON object with the following schema and no surrounding text or markdown fences."
        )
        template_text = self._read_prompt_template()
        instructions = (template_text + "\n\n" + base_instructions).strip()
        payload = {
            "instructions": instructions,
            "expected_schema": schema,
            "company_details": company_details,
            "kpis": kpis,
            "benchmarks": benchmarks,
            "output_format": "json"
        }
        return json.dumps(payload, ensure_ascii=False)

    def _build_classifier_prompt_v1(self, company_details: Dict[str, Any], kpis: Dict[str, Any]) -> str:
        """
        Build payload for Prompt 1 (classifier agent) using template 1 and the required expected schema.
        Benchmarks intentionally left empty for v1.
        """
        template_text = self._read_prompt_template_v1()
        expected_schema = {
            "growth": "list of objects with keys: kpi, growth_metrics, periodical, status, value, percent_change",
            "critical_kpis": ["string"],
            "data_quality_summary": ["string"]
        }
        payload = {
            "instructions": template_text,
            "expected_schema": expected_schema,
            "company_details": company_details,
            "kpis": kpis,
            "benchmarks": {},
            "output_format": "json"
        }
        return json.dumps(payload, ensure_ascii=False)

    def _build_report_prompt_v2(
        self,
        *,
        company_details: Dict[str, Any],
        kpis: Dict[str, Any],
        benchmarks: Dict[str, Any],
        classificator_agent_result: Dict[str, Any]
    ) -> str:
        """
        Build payload for Prompt 2 (report writer) using template 2, including the classificator_agent_result
        from Prompt 1. This follows the user's specified input shape.
        """
        template_text = self._read_prompt_template_v2()
        schema = {
            "summary": "string",
            "insights": ["string"],
            "risks": ["string"],
            "recommendations": ["string"],
        }
        payload = {
            "instructions": template_text,
            "expected_schema": schema,
            "company_details": company_details,
            "kpis": kpis,
            "classificator_agent_result": classificator_agent_result,
            "benchmarks": benchmarks or {},
            "output_format": "json",
        }
        return json.dumps(payload, ensure_ascii=False)

    def _parse_llm_json(self, text: str) -> Dict[str, Any]:
        # Strip common code fences or extra text
        cleaned = text.strip()
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
        # Find the first JSON object in the text
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            cleaned = match.group(0)
        return json.loads(cleaned)

    def _validate_report(self, obj: Dict[str, Any]) -> Tuple[bool, str]:
        try:
            if not isinstance(obj, dict):
                return False, "Top-level JSON must be an object"
            if "summary" not in obj or not isinstance(obj["summary"], (str, dict)):
                return False, "Missing or invalid 'summary' (must be string or object)"
            for key in ("insights", "risks", "recommendations"):
                if key not in obj or not isinstance(obj[key], list) or not all(isinstance(i, str) for i in obj[key]):
                    return False, f"Missing or invalid '{key}'"
            return True, ""
        except Exception as e:
            return False, str(e)

    def _next_version_number(self, upload_uuid: uuid.UUID) -> int:
        latest = db.session.query(func.max(FinancialReportVersion.version_number)).filter(
            FinancialReportVersion.upload_id == upload_uuid
        ).scalar()
        return (latest or 0) + 1

    def _log_error(self, upload_uuid: uuid.UUID, message: str, code: str = None, affected_data: Dict[str, Any] = None):
        err = DataProcessingErrors(
            upload_id=upload_uuid,
            file_id=None,
            error_type='calculation_failed',
            error_severity='high',
            error_message=message,
            error_code=code,
            affected_data=affected_data or {},
            suggested_action='Retry generation or inspect KPI/benchmark data.',
            stack_trace=None
        )
        db.session.add(err)
        db.session.commit()

    def _build_pdf_from_llm(self, report_obj: Dict[str, Any], company_details: Dict[str, Any]) -> bytes:
        """
        Build a styled PDF from the LLM JSON output. Supports simple H1–H6 tags inside strings.
        Falls back to structured sections: Summary, Insights, Risks, Recommendations.
        Returns the PDF as bytes.
        """
        try:
            # Prepare styles and dynamic theme
            styles = getSampleStyleSheet()

            # Random theme generator (coordinated palette)
            def _mix(c1: colors.Color, c2: colors.Color, t: float) -> colors.Color:
                return colors.Color(c1.red * (1 - t) + c2.red * t,
                                     c1.green * (1 - t) + c2.green * t,
                                     c1.blue * (1 - t) + c2.blue * t)

            base_palettes = [
                colors.HexColor('#1F77B4'),  # blue
                colors.HexColor('#2CA02C'),  # green
                colors.HexColor('#9467BD'),  # purple
                colors.HexColor('#17BECF'),  # teal
                colors.HexColor('#D62728'),  # red
                colors.HexColor('#FF7F0E'),  # orange
            ]
            base = random.choice(base_palettes)
            # Build 6 graded shades for H1..H6 from darker to lighter
            theme_shades = [
                _mix(base, colors.black, 0.20),  # H1 - darkest
                _mix(base, colors.black, 0.10),  # H2
                base,                             # H3
                _mix(base, colors.white, 0.20),  # H4
                _mix(base, colors.white, 0.40),  # H5
                _mix(base, colors.white, 0.60),  # H6 - lightest
            ]
            # Border uses a very light tint of the base theme
            theme_border = _mix(base, colors.white, 0.75)

            # Base body style
            body = styles['Normal']
            body.fontSize = 10
            body.leading = 14
            # Use Times for professional look
            body.fontName = 'Times-Roman'

            # Heading styles
            heading_styles = {
                1: ParagraphStyle('H1', parent=styles['Heading1'], fontSize=18, leading=22, textColor=theme_shades[0], alignment=TA_LEFT, spaceBefore=12, spaceAfter=8, fontName='Times-Bold'),
                2: ParagraphStyle('H2', parent=styles['Heading2'], fontSize=16, leading=20, textColor=theme_shades[1], alignment=TA_LEFT, spaceBefore=10, spaceAfter=6, fontName='Times-Bold'),
                3: ParagraphStyle('H3', parent=styles['Heading3'], fontSize=14, leading=18, textColor=theme_shades[2], alignment=TA_LEFT, spaceBefore=8, spaceAfter=4, fontName='Times-Bold'),
                4: ParagraphStyle('H4', parent=styles['Heading3'], fontSize=12, leading=16, textColor=theme_shades[3], alignment=TA_LEFT, spaceBefore=6, spaceAfter=3, fontName='Times-Roman'),
                5: ParagraphStyle('H5', parent=styles['Heading3'], fontSize=11, leading=15, textColor=theme_shades[4], alignment=TA_LEFT, spaceBefore=4, spaceAfter=2, fontName='Times-Roman'),
                6: ParagraphStyle('H6', parent=styles['Heading3'], fontSize=10, leading=14, textColor=theme_shades[5], alignment=TA_LEFT, spaceBefore=3, spaceAfter=2, fontName='Times-Roman'),
            }

            # Title styles (centered)
            title_style = ParagraphStyle('TitleCenter', parent=styles['Title'], fontSize=26, leading=32, alignment=TA_CENTER, textColor=theme_shades[0], spaceAfter=12, fontName='Times-BoldItalic')
            subtitle_style = ParagraphStyle('SubtitleCenter', parent=styles['Normal'], fontSize=12, leading=16, alignment=TA_CENTER, textColor=colors.black, fontName='Times-Roman')

            def add_heading(flow, level: int, text: str):
                try:
                    lvl = max(1, min(6, level))
                    flow.append(Paragraph(text, heading_styles[lvl]))
                except Exception:
                    # Fallback to body paragraph
                    flow.append(Paragraph(text, body))

            def parse_h_tags(text: str) -> List[Tuple[int, str]]:
                """Extract <h1>..</h6> blocks; returns list of (level, inner_text)."""
                tags = []
                try:
                    pattern = re.compile(r"<(h[1-6])>(.*?)</\1>", re.IGNORECASE | re.DOTALL)
                    for m in pattern.finditer(text or ""):
                        tag = m.group(1)
                        inner = m.group(2).strip()
                        level = int(tag[1])
                        tags.append((level, inner))
                except Exception:
                    pass
                return tags

            # New: parse both <h1>-<h6> and <p> tags in sequence
            def parse_h_and_p_blocks(text: str) -> List[Tuple[str, Any, str]]:
                """
                Parse <h1>-<h6> and <p> tags in order. Returns a list of blocks:
                  ('h', level:int, inner_text:str) or ('p', None, inner_text:str)
                """
                blocks: List[Tuple[str, Any, str]] = []
                try:
                    pattern = re.compile(r"<(?P<tag>h[1-6]|p)>(?P<inner>.*?)</(?P=tag)>", re.IGNORECASE | re.DOTALL)
                    for m in pattern.finditer(text or ""):
                        tag = (m.group('tag') or '').lower()
                        inner = (m.group('inner') or '').strip()
                        if tag == 'p':
                            blocks.append(('p', None, inner))
                        else:
                            level = int(tag[1])
                            blocks.append(('h', level, inner))
                except Exception:
                    pass
                return blocks

            # Footer + border + watermark/logo callback: appears on every page
            def _footer(canvas, doc):
                try:
                    canvas.saveState()
                    width, height = A4
                    # Page border (simple rectangle inset from edges) uses themed color
                    try:
                        margin = 18  # 0.25 inch
                        inset = 10  # bring footer elements inside from the border
                        canvas.setStrokeColor(theme_border)
                        canvas.setLineWidth(1)
                        canvas.rect(margin, margin, width - 2 * margin, height - 2 * margin, stroke=1, fill=0)
                    except Exception:
                        margin = 18
                        pass

                    # Company watermark text and page numbers just above the bottom border
                    try:
                        footer_y = margin + inset  # slightly above the border line
                        canvas.setFont("Times-Bold", 10)
                        # use a very light grey to mimic watermark
                        try:
                            canvas.setFillColor(colors.HexColor('#A8A8A8'))
                            # Optional: if alpha supported, make it more watermark-like
                            if hasattr(canvas, 'setFillAlpha'):
                                canvas.setFillAlpha(0.35)
                        except Exception:
                            canvas.setFillColor(colors.lightgrey)
                        # Left: brand text
                        canvas.drawString(margin + inset, footer_y, "generated by SaaSquatch Leads")
                        # Right: page number
                        try:
                            page_str = f"Page {canvas.getPageNumber()}"
                            canvas.drawRightString(width - margin - inset, footer_y, page_str)
                        except Exception:
                            pass
                        # Reset alpha if it was changed
                        if hasattr(canvas, 'setFillAlpha'):
                            canvas.setFillAlpha(1.0)
                    except Exception:
                        pass

                    # Tiny logo at top-left like a watermark
                    try:
                        logo_path = os.path.join(Config.FIN_DATA_ROOT, 'saasquatchleads_logo_notext.png')
                        if os.path.exists(logo_path):
                            # Keep very small size (e.g., 14x14 pt) and slight inset
                            logo_w = 16
                            logo_h = 16
                            inset = 10
                            x = margin + inset
                            y = height - margin - inset - logo_h
                            canvas.drawImage(logo_path, x, y, width=logo_w, height=logo_h, preserveAspectRatio=True, mask='auto')
                    except Exception:
                        # Non-fatal if logo missing or cannot be drawn
                        pass
                except Exception:
                    # Never block PDF build on footer/border issues
                    pass
                finally:
                    try:
                        canvas.restoreState()
                    except Exception:
                        pass

            story: List[Any] = []

            # ------- Page 1: Centered title page -------
            try:
                company_name = (company_details or {}).get('company_name') or 'Unknown Company'
                industry = (company_details or {}).get('industry') or 'Unknown Industry'
                fiscal_year = (company_details or {}).get('fiscal_year') or ''
                gen_dt = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

                # Add vertical space to roughly center content
                story.append(Spacer(1, 200))  # ~3 inches
                story.append(Paragraph("Financial Report", title_style))
                story.append(Spacer(1, 12))
                story.append(Paragraph(f"Company: {company_name}", subtitle_style))
                story.append(Paragraph(f"Industry: {industry}", subtitle_style))
                if fiscal_year:
                    story.append(Paragraph(f"Fiscal Year: {fiscal_year}", subtitle_style))
                story.append(Spacer(1, 8))
                story.append(Paragraph(f"Generated: {gen_dt}", subtitle_style))
                story.append(PageBreak())
            except Exception:
                # Even if title page fails, continue with rest
                pass

            # ------- Content pages -------
            summary = report_obj.get('summary')
            insights = report_obj.get('insights') or []
            risks = report_obj.get('risks') or []
            recommendations = report_obj.get('recommendations') or []

            # Track to ensure each H1 starts on a new page
            def add_with_h1_pagebreak(level: int, text: str, is_first_content: List[bool]):
                try:
                    if level == 1 and not is_first_content[0]:
                        # Start a new page for H1 only if this isn't the first content after title
                        story.append(PageBreak())
                    add_heading(story, level, text)
                    if is_first_content and is_first_content[0]:
                        is_first_content[0] = False
                except Exception:
                    pass

            is_first_content = [True]

            # Prefer embedded headings in summary
            try:
                blocks = parse_h_and_p_blocks(summary if isinstance(summary, str) else '')
                if blocks:
                    for t, lvl, txt in blocks:
                        if t == 'h':
                            add_with_h1_pagebreak(lvl, txt, is_first_content)
                        else:
                            story.append(Paragraph(txt, body))
                else:
                    add_heading(story, 2, 'Executive Summary')
                    if isinstance(summary, str) and summary.strip():
                        story.append(Paragraph(summary.strip(), body))
                    else:
                        story.append(Paragraph('No summary provided by the model.', body))
                story.append(Spacer(1, 12))
            except Exception:
                # Keep going if summary parsing fails
                pass

            # Insights
            try:
                add_heading(story, 2, 'Key Insights')
                if isinstance(insights, list) and insights:
                    for i in insights:
                        if isinstance(i, str):
                            blocks = parse_h_and_p_blocks(i)
                            if blocks:
                                for t, lvl, txt in blocks:
                                    if t == 'h':
                                        add_with_h1_pagebreak(min(lvl + 1, 6), txt, is_first_content)
                                    else:
                                        story.append(Paragraph(txt, body))
                            else:
                                story.append(Paragraph(f"• {i}", body))
                else:
                    story.append(Paragraph('No insights provided.', body))
                story.append(Spacer(1, 10))
            except Exception:
                pass

            # Risks
            try:
                add_heading(story, 2, 'Risks')
                if isinstance(risks, list) and risks:
                    for r in risks:
                        if isinstance(r, str):
                            blocks = parse_h_and_p_blocks(r)
                            if blocks:
                                for t, lvl, txt in blocks:
                                    if t == 'h':
                                        add_with_h1_pagebreak(min(lvl + 1, 6), txt, is_first_content)
                                    else:
                                        story.append(Paragraph(txt, body))
                            else:
                                story.append(Paragraph(f"• {r}", body))
                else:
                    story.append(Paragraph('No risks provided.', body))
                story.append(Spacer(1, 10))
            except Exception:
                pass

            # Recommendations
            try:
                add_heading(story, 2, 'Recommendations')
                if isinstance(recommendations, list) and recommendations:
                    for rec in recommendations:
                        if isinstance(rec, str):
                            blocks = parse_h_and_p_blocks(rec)
                            if blocks:
                                for t, lvl, txt in blocks:
                                    if t == 'h':
                                        add_with_h1_pagebreak(min(lvl + 1, 6), txt, is_first_content)
                                    else:
                                        story.append(Paragraph(txt, body))
                            else:
                                story.append(Paragraph(f"• {rec}", body))
                else:
                    story.append(Paragraph('No recommendations provided.', body))
            except Exception:
                pass

            # Build PDF to bytes with footer callbacks
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=48, bottomMargin=36)
            try:
                doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
            except Exception:
                # Last-resort fallback: try to build minimal PDF with an error message
                try:
                    fallback_story = [Paragraph('Report generation encountered issues, but completed with partial content.', body)]
                    doc.build(fallback_story, onFirstPage=_footer, onLaterPages=_footer)
                except Exception:
                    pass
            return buffer.getvalue()
        except Exception:
            # Any unexpected error -> return empty bytes so caller can skip saving
            return b""

    def _get_periodical_map(self, upload_uuid: uuid.UUID, kpi_names: List[str]) -> Dict[str, Dict[str, Dict[str, float]]]:
        """
        Build a mapping of KPI -> { 'monthly': {...}, 'quarterly': {...}, 'yearly': {...} } from KPIHistoricalData
        Only includes records with calculation_status == 'calculated'.
        """
        try:
            if not kpi_names:
                return {}
            rows = KPIHistoricalData.query.filter(
                KPIHistoricalData.upload_id == upload_uuid,
                KPIHistoricalData.kpi_name.in_(kpi_names),
                KPIHistoricalData.calculation_status == 'calculated',
                KPIHistoricalData.period_type.in_(['monthly','quarterly','yearly'])
            ).all()

            result: Dict[str, Dict[str, Dict[str, float]]] = {}
            for r in rows:
                kpi = r.kpi_name
                pt = str(r.period_type)
                label = r.period_label or ''
                value = float(r.kpi_value) if r.kpi_value is not None else None
                if value is None:
                    continue
                result.setdefault(kpi, {}).setdefault(pt, {})[label] = value
            return result
        except Exception:
            current_app.logger.exception("Failed to build periodical map from KPIHistoricalData")
            return {}

    def _apply_periodical_to_grouped(self, grouped_kpis: Dict[str, List[Dict[str, Any]]], periodical_map: Dict[str, Dict[str, Dict[str, float]]]) -> None:
        """Mutates grouped_kpis to add 'periodical' where available."""
        if not grouped_kpis or not periodical_map:
            return
        try:
            for cat, arr in grouped_kpis.items():
                for item in arr:
                    name = item.get('kpi')
                    if name and name in periodical_map and not item.get('periodical'):
                        # Ensure all three keys exist, even if empty
                        pm = periodical_map[name]
                        item['periodical'] = {
                            'monthly': pm.get('monthly', {}),
                            'quarterly': pm.get('quarterly', {}),
                            'yearly': pm.get('yearly', {}),
                        }
        except Exception:
            current_app.logger.exception("Failed to apply periodical map to grouped KPIs")

    def _group_kpis_from_db(self, upload_uuid: uuid.UUID) -> Dict[str, List[Dict[str, Any]]]:
        """
        Build grouped KPI payload from KPIHistoricalData rows in the DB for the given upload.
        Uses period_label values (e.g., monthly1, quarterly2) as keys under periodical.
        'value' is chosen as the latest from yearly -> quarterly -> monthly.
        'periodical' includes only rows with calculation_status == 'calculated'.
        """
        try:
            rows: List[KPIHistoricalData] = KPIHistoricalData.query.filter(
                KPIHistoricalData.upload_id == upload_uuid
            ).all()
            if not rows:
                return {}

            # First, aggregate periodical values per KPI
            tmp: Dict[tuple, Dict[str, Any]] = {}
            for r in rows:
                k = (r.kpi_name, r.kpi_category or 'Uncategorized')
                if k not in tmp:
                    tmp[k] = {
                        'periodical': {'monthly': {}, 'quarterly': {}, 'yearly': {}},
                        'statuses': [],
                    }

                # Track all statuses to compute calc_status summary
                if r.calculation_status:
                    tmp[k]['statuses'].append(str(r.calculation_status))

                # Only include calculated values in the time series
                try:
                    if str(r.calculation_status).lower() == 'calculated' and r.kpi_value is not None:
                        pt = str(r.period_type)
                        lbl = r.period_label or ''
                        try:
                            val = float(r.kpi_value)
                        except Exception:
                            val = None
                        if val is not None and pt in ('monthly','quarterly','yearly') and lbl:
                            tmp[k]['periodical'][pt][lbl] = val
                except Exception:
                    # Ignore malformed rows
                    pass

            # Helper to compute latest value from a {label->val} map
            def latest_value(d: Dict[str, float]) -> float | None:
                if not d:
                    return None
                def n(lbl: str) -> int:
                    m = re.search(r"(\d+)$", str(lbl))
                    return int(m.group(1)) if m else 0
                last_key = max(d.keys(), key=n)
                return d.get(last_key)

            grouped: Dict[str, List[Dict[str, Any]]] = {}
            for (kpi_name, kpi_cat), data in tmp.items():
                per = data['periodical']
                value = (
                    latest_value(per['yearly'])
                    or latest_value(per['quarterly'])
                    or latest_value(per['monthly'])
                )

                statuses = [s for s in data['statuses'] if s]
                calc_status = None
                if any(s.lower() == 'calculated' for s in statuses):
                    calc_status = 'calculated'
                elif statuses:
                    # Pick the most frequent status
                    try:
                        calc_status = max(set(statuses), key=statuses.count)
                    except Exception:
                        calc_status = statuses[0]

                item = {
                    'kpi': kpi_name,
                    'value': float(value) if value is not None else None,
                    'periodical': per,
                    'unit': None,
                    'status': None,
                    'calc_status': calc_status,
                }
                cat = kpi_cat or 'Uncategorized'
                grouped.setdefault(cat, []).append(item)

            return grouped
        except Exception:
            current_app.logger.exception("Failed to group KPIs from KPIHistoricalData")
            return {}

    def build_llm_payload_from_db(self, upload_id: str, company_details: Dict[str, Any] | None = None) -> Tuple[Dict[str, Any], int]:
        """
        Build the full LLM input payload directly from KPIHistoricalData in the DB for an upload_id.
        Returns (payload_dict, http_status_code). Benchmarks are left empty in this utility.
        """
        # Validate upload_id
        try:
            upload_uuid = uuid.UUID(upload_id)
        except ValueError:
            return {"error": "Invalid upload_id format"}, 400

        grouped_kpis = self._group_kpis_from_db(upload_uuid)
        if not grouped_kpis:
            return {"error": "No KPIHistoricalData found for upload_id"}, 404

        # Default company context if not provided
        if not company_details:
            company_details = {
                "company_name": "Placeholder Corp",
                "industry": "Technology",
                "fiscal_year": datetime.utcnow().year,
                "revenue_scale": "Mid-size"
            }

        schema = {
            "summary": "string",
            "insights": ["string"],
            "risks": ["string"],
            "recommendations": ["string"],
        }

        base_instructions = (
            "You are a financial analyst. Using the provided company details, KPIs grouped by category, and industry benchmarks, "
            "write a concise performance summary, highlight key insights (positives), identify risks (weak areas), and provide "
            "actionable recommendations.\n\n"
            "Return ONLY a JSON object with the following schema and no surrounding text or markdown fences."
        )
        template_text = self._read_prompt_template()
        instructions = (template_text + "\n\n" + base_instructions).strip()

        payload = {
            "instructions": instructions,
            "expected_schema": schema,
            "company_details": company_details,
            "kpis": grouped_kpis,
            "benchmarks": {},
            "output_format": "json",
        }

        return payload, 200

    def generate_report(self, upload_id: str, kpi_results: Dict[str, Any] | None = None, company_details: Dict[str, Any] | None = None) -> Tuple[Dict[str, Any], int]:
        # Validate upload_id
        try:
            upload_uuid = uuid.UUID(upload_id)
        except ValueError:
            return {"error": "Invalid upload_id format"}, 400

        # Compute the next version number up front so it can be recorded in CSV and reused consistently
        version_number = self._next_version_number(upload_uuid)

        # Track LLM errors to include in metadata summary
        llm_errors: List[str] = []

        # Fetch KPIs or use provided results
        if kpi_results:
            grouped_kpis = self._group_kpis_from_payload(kpi_results)
            # Derive KPI names from grouped structure
            kpi_names = sorted({item.get("kpi") for arr in grouped_kpis.values() for item in arr if item.get("kpi")})
            kpis = None
        else:
            kpis = FinancialKPI.query.filter(FinancialKPI.upload_id == upload_uuid).all()
            if not kpis:
                self._log_error(upload_uuid, "KPIs not found for given upload_id", code="KPIS_MISSING")
                return {"error": "KPIs not found"}, 400
            grouped_kpis = self._group_kpis(kpis)
            kpi_names = sorted({k.kpi_name for k in kpis})

        # Augment with historical periodical data (monthly/quarterly/yearly)
        try:
            periodical_map = self._get_periodical_map(upload_uuid, kpi_names)
            self._apply_periodical_to_grouped(grouped_kpis, periodical_map)
        except Exception:
            current_app.logger.exception("Failed to augment KPIs with periodical data")

        # Company context (use provided or fallback)
        if not company_details:
            company_details = {
                "company_name": "Placeholder Corp",
                "industry": "Technology",
                "fiscal_year": datetime.utcnow().year,
                "revenue_scale": "Mid-size"
            }

        # Fetch industry benchmarks (based on dummy industry)
        benchmarks = self._fetch_benchmarks(company_details["industry"], kpi_names)

        # ---------------------------------
        # New Step: Run Prompt 1 (Classifier)
        # ---------------------------------
        fin_file = None
        try:
            # Build and call classifier agent prompt
            classifier_prompt = self._build_classifier_prompt_v1(company_details, grouped_kpis)
            raw_agent1_text = GenerateController.generate_with_model(classifier_prompt, model_choice="deepseek")

            # Persist raw response as CSV under 'llm_generation' stage
            fin_file = FinancialFile.query.filter_by(upload_id=upload_uuid).order_by(FinancialFile.created_at.asc()).first()
            if fin_file:
                file_manager = FilePersistenceManager()
                # Build stable CSV path: data/finance_report_gen/uploads/<short_upload>/<short_file>/stages/llm_generation/llm_responses.csv
                file_info = file_manager.get_file_metadata(str(fin_file.file_id))
                if file_info:
                    short_upload = str(file_info['upload_id'])[:8]
                    short_file = str(fin_file.file_id)[:8]
                    stage_dir = os.path.join(file_manager.base_path, short_upload, short_file, 'stages', 'llm_generation')
                    os.makedirs(stage_dir, exist_ok=True)
                    csv_path = os.path.join(stage_dir, 'llm_responses.csv')

                    # Prepare row for Prompt 1
                    row = {
                        'upload_id': str(file_info['upload_id']),
                        'file_id': str(fin_file.file_id),
                        'version_number': version_number,
                        'timestamp': datetime.utcnow().isoformat(),
                        'llm agent 1 response': raw_agent1_text,
                        'llm response 2': None,
                    }

                    if os.path.exists(csv_path):
                        try:
                            df_existing = pd.read_csv(csv_path)
                        except Exception:
                            df_existing = pd.DataFrame()
                        df_new = pd.concat([df_existing, pd.DataFrame([row])], ignore_index=True)
                        # Ensure text columns are object dtype to safely hold JSON strings
                        for col in ['llm agent 1 response', 'llm response 2', 'upload_id', 'file_id', 'timestamp']:
                            if col in df_new.columns:
                                df_new[col] = df_new[col].astype('object')
                    else:
                        df_new = pd.DataFrame([row])
                        for col in ['llm agent 1 response', 'llm response 2', 'upload_id', 'file_id', 'timestamp']:
                            if col in df_new.columns:
                                df_new[col] = df_new[col].astype('object')
                    df_new.to_csv(csv_path, index=False)
        except Exception:
            current_app.logger.exception("Prompt 1 (classifier) execution or persistence failed; continuing with main report generation")
            llm_errors.append("Prompt 1 failed: see server logs for details")

        # Build Prompt 2 payload and call DeepSeek (now using template 2 and agent 1 result)
        # Parse agent 1 JSON for inclusion into Prompt 2
        parsed_agent1: Dict[str, Any] | None = None
        try:
            if 'raw_agent1_text' in locals() and raw_agent1_text:
                parsed_agent1 = self._parse_llm_json(raw_agent1_text)
        except Exception:
            parsed_agent1 = None

        # For maximum compatibility with the user's example, if parsed_agent1 is an inner dict,
        # we still wrap it as provided; otherwise pass through.
        classificator_payload = parsed_agent1 if isinstance(parsed_agent1, dict) else {}

        prompt = self._build_report_prompt_v2(
            company_details=company_details,
            kpis=grouped_kpis,
            benchmarks=benchmarks,
            classificator_agent_result=classificator_payload,
        )

        def _call_llm_once() -> Tuple[Dict[str, Any], str]:
            raw = GenerateController.generate_with_model(prompt, model_choice="deepseek")
            parsed = self._parse_llm_json(raw)
            ok, err = self._validate_report(parsed)
            if not ok:
                raise ValueError(f"LLM JSON validation failed: {err}")
            return parsed, raw

        try:
            try:
                report_obj, raw_text = _call_llm_once()
            except Exception as first_err:
                current_app.logger.warning(f"DeepSeek parse/validation failed on first attempt: {first_err}")
                # Retry once
                report_obj, raw_text = _call_llm_once()
        except Exception as e:
            current_app.logger.exception("DeepSeek generation failed")
            self._log_error(upload_uuid, f"DeepSeek generation failed: {e}", code="LLM_FAIL", affected_data={
                "kpi_count": len(kpis) if kpis is not None else sum(len(v) for v in grouped_kpis.values()),
                "kpi_names": kpi_names,
            })
            llm_errors.append(f"Prompt 2 failed: {str(e)}")
            # Expose raw error details in development/debug mode only
            if current_app.config.get("DEBUG"):
                return {"error": "Report generation failed", "details": str(e)}, 502
            return {"error": "Report generation failed"}, 502

        # Append Prompt 2 raw response to the same CSV row (matching upload_id/file_id/version_number)
        try:
            if fin_file:
                file_manager = FilePersistenceManager()
                file_info = file_manager.get_file_metadata(str(fin_file.file_id))
                if file_info:
                    short_upload = str(file_info['upload_id'])[:8]
                    short_file = str(fin_file.file_id)[:8]
                    stage_dir = os.path.join(file_manager.base_path, short_upload, short_file, 'stages', 'llm_generation')
                    csv_path = os.path.join(stage_dir, 'llm_responses.csv')
                    if os.path.exists(csv_path):
                        try:
                            df_existing = pd.read_csv(csv_path)
                        except Exception:
                            df_existing = pd.DataFrame()
                        if not df_existing.empty and {'upload_id','file_id','version_number'}.issubset(df_existing.columns):
                            mask = (
                                (df_existing['upload_id'].astype(str) == str(file_info['upload_id'])) &
                                (df_existing['file_id'].astype(str) == str(fin_file.file_id)) &
                                (df_existing['version_number'].astype(int) == int(version_number))
                            )
                            if mask.any():
                                # Ensure target column can hold string JSON
                                if 'llm response 2' not in df_existing.columns:
                                    df_existing['llm response 2'] = None
                                df_existing['llm response 2'] = df_existing['llm response 2'].astype('object')
                                df_existing.loc[mask, 'llm response 2'] = str(raw_text)
                            else:
                                # If row was not created earlier for any reason, append a new one with both values
                                new_row = {
                                    'upload_id': str(file_info['upload_id']),
                                    'file_id': str(fin_file.file_id),
                                    'version_number': version_number,
                                    'timestamp': datetime.utcnow().isoformat(),
                                    'llm agent 1 response': (raw_agent1_text if 'raw_agent1_text' in locals() else None),
                                    'llm response 2': raw_text,
                                }
                                df_existing = pd.concat([df_existing, pd.DataFrame([new_row])], ignore_index=True)
                                for col in ['llm agent 1 response', 'llm response 2', 'upload_id', 'file_id', 'timestamp']:
                                    if col in df_existing.columns:
                                        df_existing[col] = df_existing[col].astype('object')
                        else:
                            df_existing = pd.DataFrame([{
                                'upload_id': str(file_info['upload_id']),
                                'file_id': str(fin_file.file_id),
                                'version_number': version_number,
                                'timestamp': datetime.utcnow().isoformat(),
                                'llm agent 1 response': (raw_agent1_text if 'raw_agent1_text' in locals() else None),
                                'llm response 2': raw_text,
                            }])
                            for col in ['llm agent 1 response', 'llm response 2', 'upload_id', 'file_id', 'timestamp']:
                                if col in df_existing.columns:
                                    df_existing[col] = df_existing[col].astype('object')
                        df_existing.to_csv(csv_path, index=False)
        except Exception:
            current_app.logger.exception("Failed to append Prompt 2 response to CSV; continuing")

        # Persist report to DB version table (reuse computed version_number)
        summary_value = report_obj.get("summary")
        if isinstance(summary_value, dict):
            try:
                parts: List[str] = []
                dq = summary_value.get("data_quality_summary")
                if dq:
                    parts.append(str(dq).strip())
                crit = summary_value.get("critical_kpis")
                if isinstance(crit, list) and crit:
                    parts.append("Top 3 critical KPIs: " + ", ".join(map(str, crit[:3])))
                growth = summary_value.get("growth")
                if isinstance(growth, list) and growth:
                    # Build a brief growth sentence for first few KPIs
                    growth_bits = []
                    for g in growth[:5]:
                        try:
                            name = g.get("kpi")
                            gm = g.get("growth_metrics", {})
                            pt = gm.get("periodical")
                            st = gm.get("status")
                            pc = gm.get("percent_change")
                            bit = f"{name}: {st or 'n/a'} {( '('+str(pt)+')' ) if pt else ''}{( ' ['+str(pc)+']' ) if pc is not None else ''}"
                            growth_bits.append(bit)
                        except Exception:
                            continue
                    if growth_bits:
                        parts.append("Growth summary: " + "; ".join(growth_bits))
                summary_value = " \n".join(parts) or ""
            except Exception:
                # Fallback to raw JSON string
                try:
                    summary_value = json.dumps(summary_value, ensure_ascii=False)
                except Exception:
                    summary_value = str(summary_value)
        elif not isinstance(summary_value, str):
            summary_value = str(summary_value) if summary_value is not None else ""
        frv = FinancialReportVersion(
            upload_id=upload_uuid,
            version_number=version_number,
            summary=summary_value,
            insights=report_obj.get("insights"),
            risks=report_obj.get("risks"),
            recommendations=report_obj.get("recommendations"),
            generated_by_llm=True,
            llm_model_used="deepseek",
            llm_prompt_version="v2",
            report_metadata={
                "company_details": company_details,
                "kpi_categories": list(grouped_kpis.keys()),
                "benchmarked_kpis": list(benchmarks.keys()),
            }
        )
        db.session.add(frv)
        db.session.commit()

        # Persist LLM JSON output to file system under 'llm_generation' stage and update a single summary metadata file
        try:
            # Find a representative FinancialFile for this upload to anchor persistence paths
            fin_file = FinancialFile.query.filter_by(upload_id=upload_uuid).order_by(FinancialFile.created_at.asc()).first()
            if fin_file:
                file_manager = FilePersistenceManager()
                # Save stage file under 'llm_generation' as the canonical JSON report
                stage_filename = f"llm_report_v{version_number}.json"
                bytes_payload = json.dumps(report_obj, indent=2).encode('utf-8')
                json_relative_path = file_manager.save_stage_file(
                    file_id=str(fin_file.file_id),
                    stage_name='llm_generation',
                    data=bytes_payload,
                    original_filename=stage_filename,
                    metadata={
                        'stage': 'llm_generation',
                        'version_number': version_number,
                        'llm_model': 'deepseek'
                    }
                )
                # Do NOT update DB status to 'llm_generation' as it's not part of FinancialFile.status enum

                # Update aggregated metadata summary in metadata directory
                file_info = file_manager.get_file_metadata(str(fin_file.file_id))
                if file_info:
                    short_upload = str(file_info['upload_id'])[:8]
                    short_file = str(fin_file.file_id)[:8]
                    metadata_dir = os.path.join(file_manager.base_path, short_upload, short_file, 'metadata')
                    os.makedirs(metadata_dir, exist_ok=True)
                    summary_path = os.path.join(metadata_dir, 'llm_generation_summary.json')

                    try:
                        if os.path.exists(summary_path):
                            with open(summary_path, 'r', encoding='utf-8') as f:
                                index_obj = json.load(f)
                        else:
                            index_obj = {
                                'upload_id': str(file_info['upload_id']),
                                'file_id': str(fin_file.file_id),
                                'total_versions': 0,
                                'kpi_count_calculated': 0,
                                'kpi_names_calculated': [],
                                'llm_errors': [],
                                'versions': []
                            }
                    except Exception:
                        index_obj = {
                            'upload_id': str(file_info['upload_id']),
                            'file_id': str(fin_file.file_id),
                            'total_versions': 0,
                            'kpi_count_calculated': 0,
                            'kpi_names_calculated': [],
                            'llm_errors': [],
                            'versions': []
                        }

                    # Compute calculated KPI names and counts
                    try:
                        calc_kpis = sorted({ item.get('kpi') for arr in grouped_kpis.values() for item in arr if (item or {}).get('calc_status') == 'calculated' and item.get('kpi') })
                    except Exception:
                        calc_kpis = []

                    # Update KPI calculated fields and errors
                    index_obj['kpi_names_calculated'] = sorted({*index_obj.get('kpi_names_calculated', []), *calc_kpis})
                    index_obj['kpi_count_calculated'] = len(index_obj['kpi_names_calculated'])
                    if llm_errors:
                        # merge unique errors
                        existing_errs = set(index_obj.get('llm_errors', []))
                        for e in llm_errors:
                            if e not in existing_errs:
                                index_obj.setdefault('llm_errors', []).append(e)
                                existing_errs.add(e)

                    # Determine PDF link if already generated later; placeholder here, will update below when pdf is saved
                    index_obj['versions'].append({
                        'version_number': version_number,
                        'json_report_path': json_relative_path,
                        'pdf_path': None,
                        'created_at': datetime.utcnow().isoformat(),
                        # Per-version fields as requested
                        'kpi_count_calculated': len(calc_kpis),
                        'kpi_names_calculated': list(calc_kpis),
                        'llm_errors': list(llm_errors),
                    })
                    index_obj['total_versions'] = len(index_obj['versions'])

                    with open(summary_path, 'w', encoding='utf-8') as f:
                        json.dump(index_obj, f, indent=2)
        except Exception:
            current_app.logger.exception("Failed to persist LLM output to file system")

        # Generate PDF from LLM output and persist as a new stage file
        pdf_relative_path = None
        try:
            pdf_bytes = self._build_pdf_from_llm(report_obj, company_details)
            if fin_file and pdf_bytes:
                pdf_filename = f"financial_report_v{version_number}.pdf"
                pdf_relative_path = file_manager.save_stage_file(
                    file_id=str(fin_file.file_id),
                    stage_name='report_pdf',
                    data=pdf_bytes,
                    original_filename=pdf_filename,
                    metadata={
                        'stage': 'report_pdf',
                        'version_number': version_number,
                        'created_at': datetime.utcnow().isoformat()
                    }
                )
                # Update the report version with a download link (relative path under data root)
                frv.download_link_pdf = pdf_relative_path
                db.session.commit()

                # Update the metadata summary with the PDF path
                try:
                    file_manager = FilePersistenceManager()
                    file_info = file_manager.get_file_metadata(str(fin_file.file_id))
                    if file_info:
                        short_upload = str(file_info['upload_id'])[:8]
                        short_file = str(fin_file.file_id)[:8]
                        metadata_dir = os.path.join(file_manager.base_path, short_upload, short_file, 'metadata')
                        summary_path = os.path.join(metadata_dir, 'llm_generation_summary.json')
                        if os.path.exists(summary_path):
                            with open(summary_path, 'r', encoding='utf-8') as f:
                                index_obj = json.load(f)
                            # find entry for this version_number and update pdf_path
                            for v in index_obj.get('versions', []):
                                try:
                                    if int(v.get('version_number')) == int(version_number):
                                        v['pdf_path'] = pdf_relative_path
                                except Exception:
                                    continue
                            with open(summary_path, 'w', encoding='utf-8') as f:
                                json.dump(index_obj, f, indent=2)
                except Exception:
                    current_app.logger.exception("Failed to update metadata summary with PDF path")
        except Exception:
            current_app.logger.exception("Failed to generate or persist PDF report")

        response = {
            "version_id": str(frv.version_id),
            "upload_id": str(frv.upload_id),
            "version_number": frv.version_number,
            "generated_date": frv.generated_date.isoformat() if frv.generated_date else None,
            "summary": frv.summary,
            "insights": frv.insights,
            "risks": frv.risks,
            "recommendations": frv.recommendations,
            "generated_by_llm": frv.generated_by_llm,
            "llm_model_used": frv.llm_model_used,
            "llm_prompt_version": frv.llm_prompt_version,
            "download_link_pdf": frv.download_link_pdf,
        }
        return response, 200
