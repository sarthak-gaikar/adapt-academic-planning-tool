"""
ADAPT — DOCX Document Generator

Generates faculty-ready formatted Word documents (.docx) for:
1. Examination Papers (MSE & ESE) with institutional headers, sections, choices, and CO/Bloom tags
2. Answer Keys & Marking Schemes
3. Academic Activity Plans (AAP) with tables
4. Assignments
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from app.config import get_settings
from app.core.exceptions import DocumentGenerationError
from app.core.logging import get_logger

logger = get_logger("docgen.docx")
settings = get_settings()


def _set_cell_background(cell, fill_hex: str):
    """Sets background shading of a docx table cell."""
    tc_pr = cell._element.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill_hex)
    tc_pr.append(shd)


class DOCXGenerator:
    """Generates official academic DOCX documents."""

    @staticmethod
    def generate_exam_paper_docx(
        subject_name: str,
        course_code: str,
        exam_type: str,
        title: str,
        total_marks: int,
        instructions: str,
        questions: List[Dict[str, Any]],
        output_path: str,
        include_tags: bool = True,
        institution_name: Optional[str] = None,
        department: Optional[str] = None,
    ) -> str:
        try:
            doc = docx.Document()

            # Set 1 inch margins
            for sec in doc.sections:
                sec.top_margin = Inches(0.8)
                sec.bottom_margin = Inches(0.8)
                sec.left_margin = Inches(0.8)
                sec.right_margin = Inches(0.8)

            inst_name = institution_name or settings.institution_name
            dept_name = department or settings.institution_department

            # --- Header ---
            p_inst = doc.add_paragraph()
            p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_inst = p_inst.add_run(f"{inst_name.upper()}\n")
            run_inst.bold = True
            run_inst.font.size = Pt(14)
            run_inst.font.color.rgb = RGBColor(15, 23, 42)

            run_dept = p_inst.add_run(f"{dept_name}\n")
            run_dept.font.size = Pt(10)
            run_dept.font.color.rgb = RGBColor(71, 85, 105)

            p_title = doc.add_paragraph()
            p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run_title = p_title.add_run(f"{title.upper()}\n")
            run_title.bold = True
            run_title.font.size = Pt(12)

            # Metadata Table
            meta_table = doc.add_table(rows=2, cols=2)
            meta_table.alignment = WD_TABLE_ALIGNMENT.CENTER
            meta_table.autofit = True

            meta_table.rows[0].cells[0].text = f"Course: {subject_name} ({course_code})"
            meta_table.rows[0].cells[1].text = f"Max Marks: {total_marks}"
            meta_table.rows[1].cells[0].text = f"Academic Year: {settings.academic_year} | Sem: {settings.current_semester}"
            meta_table.rows[1].cells[1].text = "Time Allowed: 2 Hours" if exam_type == "MSE" else "Time Allowed: 3 Hours"

            for row in meta_table.rows:
                for cell in row.cells:
                    cell.paragraphs[0].runs[0].font.size = Pt(9.5) if cell.paragraphs[0].runs else Pt(9.5)

            doc.add_paragraph() # Spacing

            # Instructions
            if instructions:
                p_inst_box = doc.add_paragraph()
                r_ih = p_inst_box.add_run("Instructions:\n")
                r_ih.bold = True
                r_ih.font.size = Pt(9.5)
                r_it = p_inst_box.add_run(instructions)
                r_it.font.size = Pt(9.0)
                r_it.italic = True
                doc.add_paragraph()

            # --- Questions grouped by section ---
            sections_map: Dict[str, List[Dict[str, Any]]] = {}
            for q in questions:
                sec_name = q.get("section") or "General Section"
                if sec_name not in sections_map:
                    sections_map[sec_name] = []
                sections_map[sec_name].append(q)

            for sec_name, sec_questions in sections_map.items():
                p_sec = doc.add_paragraph()
                p_sec.alignment = WD_ALIGN_PARAGRAPH.CENTER
                r_sec = p_sec.add_run(f"--- {sec_name.upper()} ---")
                r_sec.bold = True
                r_sec.font.size = Pt(11)
                r_sec.font.color.rgb = RGBColor(30, 41, 59)

                for q in sec_questions:
                    q_num = q.get("sequence_order", 1)
                    q_text = q.get("question_text", "")
                    q_marks = q.get("marks", 0)
                    co = q.get("co_code") or ""
                    bloom = q.get("bloom_level") or ""
                    choice_grp = q.get("choice_group")

                    # Table row for question (Text on left, marks/tags on right)
                    q_table = doc.add_table(rows=1, cols=2)
                    q_table.alignment = WD_TABLE_ALIGNMENT.CENTER
                    q_table.columns[0].width = Inches(5.8)
                    q_table.columns[1].width = Inches(1.2)

                    cell_left = q_table.rows[0].cells[0]
                    cell_right = q_table.rows[0].cells[1]

                    p_q = cell_left.paragraphs[0]
                    r_qn = p_q.add_run(f"Q{q_num}. ")
                    r_qn.bold = True
                    r_qn.font.size = Pt(10)
                    r_qt = p_q.add_run(q_text)
                    r_qt.font.size = Pt(10)

                    # Right cell marks & OBE metadata tags
                    p_marks = cell_right.paragraphs[0]
                    p_marks.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                    r_m = p_marks.add_run(f"[{q_marks}M]\n")
                    r_m.bold = True
                    r_m.font.size = Pt(10)

                    if include_tags and (co or bloom):
                        tag_str = f"({co} / {bloom})" if co and bloom else f"({co or bloom})"
                        r_tag = p_marks.add_run(tag_str)
                        r_tag.font.size = Pt(8)
                        r_tag.font.color.rgb = RGBColor(100, 116, 139)

                    # Spacing
                    doc.add_paragraph()

            # Footer
            p_end = doc.add_paragraph()
            p_end.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_end = p_end.add_run("***** END OF QUESTION PAPER *****")
            r_end.font.size = Pt(9)
            r_end.font.color.rgb = RGBColor(148, 163, 184)

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_path)
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate exam DOCX: {e}")
            raise DocumentGenerationError(f"DOCX generation failed: {str(e)}")

    @staticmethod
    def generate_aap_docx(
        subject_name: str,
        course_code: str,
        total_weeks: int,
        total_hours: int,
        weeks_data: List[Dict[str, Any]],
        output_path: str,
    ) -> str:
        try:
            doc = docx.Document()
            for sec in doc.sections:
                sec.orientation = docx.enum.section.WD_ORIENT.LANDSCAPE
                sec.page_width = Inches(11.0)
                sec.page_height = Inches(8.5)
                sec.top_margin = Inches(0.6)
                sec.bottom_margin = Inches(0.6)
                sec.left_margin = Inches(0.6)
                sec.right_margin = Inches(0.6)

            p_h = doc.add_paragraph()
            p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_h = p_h.add_run(f"ACADEMIC ACTIVITY PLAN (AAP) / LESSON PLAN\n")
            r_h.bold = True
            r_h.font.size = Pt(13)

            r_sub = p_h.add_run(f"Course: {subject_name} ({course_code}) | Total Weeks: {total_weeks} | Total Hours: {total_hours}\n")
            r_sub.font.size = Pt(10)

            # AAP Table
            headers = ["Wk", "Unit", "Topics Planned", "Teaching Method", "CO", "Hrs", "Activity Type"]
            table = doc.add_table(rows=1, cols=len(headers))
            table.alignment = WD_TABLE_ALIGNMENT.CENTER

            # Header Row
            hdr_cells = table.rows[0].cells
            for idx, h in enumerate(headers):
                hdr_cells[idx].text = h
                _set_cell_background(hdr_cells[idx], "1E293B")
                p = hdr_cells[idx].paragraphs[0]
                if p.runs:
                    p.runs[0].font.bold = True
                    p.runs[0].font.color.rgb = RGBColor(255, 255, 255)
                    p.runs[0].font.size = Pt(9.5)

            for w in weeks_data:
                row_cells = table.add_row().cells
                row_cells[0].text = str(w.get("week_number", ""))
                row_cells[1].text = f"Unit {w.get('unit_number', '')}"
                
                topics = w.get("topics_covered", [])
                row_cells[2].text = ", ".join(topics) if isinstance(topics, list) else str(topics)
                row_cells[3].text = str(w.get("teaching_method", ""))
                row_cells[4].text = str(w.get("co_mapped", ""))
                row_cells[5].text = str(w.get("planned_hours", ""))
                row_cells[6].text = str(w.get("activity_type", "Lecture"))

                for cell in row_cells:
                    p = cell.paragraphs[0]
                    if p.runs:
                        p.runs[0].font.size = Pt(9)

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_path)
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate AAP DOCX: {e}")
            raise DocumentGenerationError(f"AAP DOCX generation failed: {str(e)}")

    @staticmethod
    def generate_answer_key_docx(
        subject_name: str,
        exam_title: str,
        answers: List[Dict[str, Any]],
        output_path: str,
    ) -> str:
        try:
            doc = docx.Document()
            p_h = doc.add_paragraph()
            p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_h = p_h.add_run(f"OFFICIAL ANSWER KEY & MARKING SCHEME\n")
            r_h.bold = True
            r_h.font.size = Pt(13)
            r_sub = p_h.add_run(f"{exam_title} — {subject_name}\n")
            r_sub.font.size = Pt(10)

            doc.add_paragraph()

            for ans in answers:
                seq = ans.get("sequence_order", 1)
                marks = ans.get("marks", 0)
                model_ans = ans.get("model_answer", "")
                key_points = ans.get("key_points", [])
                steps = ans.get("expected_steps", [])
                scheme = ans.get("marking_scheme", "")

                p_q = doc.add_paragraph()
                r_q = p_q.add_run(f"Answer Q{seq} [{marks} Marks]:\n")
                r_q.bold = True
                r_q.font.size = Pt(11)

                p_ans = doc.add_paragraph()
                r_at = p_ans.add_run("Model Solution:\n")
                r_at.bold = True
                r_at.font.size = Pt(9.5)
                p_ans.add_run(f"{model_ans}\n")

                if key_points:
                    p_kp = doc.add_paragraph()
                    r_kph = p_kp.add_run("Key Concepts Required:\n")
                    r_kph.bold = True
                    r_kph.font.size = Pt(9.5)
                    for kp in key_points:
                        p_kp.add_run(f"• {kp}\n")

                if steps:
                    p_st = doc.add_paragraph()
                    r_sth = p_st.add_run("Solution Steps:\n")
                    r_sth.bold = True
                    r_sth.font.size = Pt(9.5)
                    for idx, st in enumerate(steps, 1):
                        p_st.add_run(f"{idx}. {st}\n")

                if scheme:
                    p_sc = doc.add_paragraph()
                    r_sch = p_sc.add_run("Marking Scheme Breakdown:\n")
                    r_sch.bold = True
                    r_sch.font.size = Pt(9.5)
                    p_sc.add_run(f"{scheme}\n")

                doc.add_paragraph("--------------------------------------------------------------------------------")

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            doc.save(output_path)
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate Answer Key DOCX: {e}")
            raise DocumentGenerationError(f"Answer Key DOCX generation failed: {str(e)}")
