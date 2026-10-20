"""Exportação local, sem enviar registros para serviços externos."""
import csv
from io import BytesIO, StringIO
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle

FONT_DIR = Path(reportlab.__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("Diario", str(FONT_DIR / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("DiarioBold", str(FONT_DIR / "VeraBd.ttf")))
pdfmetrics.registerFontFamily("Diario", normal="Diario", bold="DiarioBold")
GREEN = colors.HexColor("#244e43")
PALE = colors.HexColor("#edf3ed")
GRAY = colors.HexColor("#56615d")

CSV_COLUMNS = [
    "Escola", "Ano", "Turma", "Período", "Início do período", "Fim do período", "Disciplina",
    "Matrícula ID", "Aluno", "Identificação", "Situação da matrícula", "Entrada", "Saída",
    "Cálculo", "Escala", "Referência", "Arredondamento", "Casas decimais", "Regra de recuperação",
    "Base ou parcial", "Recuperação", "Resultado", "Situação das notas", "Notas pendentes", "Não entregues", "Dispensas",
    "Aulas no vínculo", "Aulas com chamada", "Presenças", "Faltas", "Faltas justificadas",
    "Aulas com chamada pendente", "Frequência registrada (%)", "Datas da matrícula pendentes",
    "Avaliações pendentes", "Observações", "Emitido em",
]


def number(value):
    return "" if value is None else str(value).replace(".", ",")


def safe_cell(value):
    text = str(value) if value is not None else ""
    # Quoting CSV alone does not prevent formulas when opened in a spreadsheet.
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        return "'" + text
    return text


def date_text(value):
    return value.strftime("%d/%m/%Y") if value else ""


def csv_report(report):
    output = StringIO(newline="")
    writer = csv.writer(output, delimiter=";", lineterminator="\r\n")
    writer.writerow(CSV_COLUMNS)
    for row in report["rows"]:
        pupil, book, grade, frequency = row["enrollment"], row["book"], row["grade"], row["frequency"]
        room, term = report["classroom"], report["term"]
        values = [
            room.school.name, room.academic_year.year, room.name, term.name, date_text(term.start_date),
            date_text(term.end_date), row["subject"].name, pupil.pk, pupil.student.name, pupil.student.reference,
            pupil.get_status_display(), date_text(pupil.starts_on), date_text(pupil.ends_on),
            book.get_calculation_display() if book else "", number(book.scale) if book else "",
            number(book.minimum) if book else "", book.get_rounding_display() if book else "",
            book.precision if book else "", book.get_recovery_display() if book else "",
            number(grade["original"]) if grade else "", number(grade["recovery"]) if grade else "",
            number(grade["final"]) if grade else "", row["status"], grade["pending"] if grade else "",
            grade["missing"] if grade else "", grade["exempt"] if grade else "",
            frequency["total"], frequency["recorded"], frequency["present"], frequency["absences"],
            frequency["justified"], frequency["pending"], number(frequency["percentage"]),
            "Sim" if row["dates_missing"] else "Não", "\n".join(row["pending_items"]),
            "\n".join(row["observations"]), report["generated_at"].strftime("%d/%m/%Y %H:%M:%S"),
        ]
        writer.writerow([safe_cell(value) for value in values])
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def pdf_report(report):
    stream = BytesIO()
    individual = report["enrollment"] is not None
    pagesize = A4 if individual else landscape(A4)
    width = pagesize[0] - 30 * mm
    doc = SimpleDocTemplate(stream, pagesize=pagesize, rightMargin=15 * mm, leftMargin=15 * mm,
                            topMargin=18 * mm, bottomMargin=19 * mm,
                            title="Ficha individual" if individual else "Relatório de conselho",
                            author=report["teacher"])
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", fontName="DiarioBold", fontSize=19, leading=24,
                               textColor=GREEN, spaceAfter=10))
    styles.add(ParagraphStyle(name="ReportHeading", fontName="DiarioBold", fontSize=12, leading=16,
                               textColor=GREEN, spaceBefore=15, spaceAfter=8, keepWithNext=True))
    styles.add(ParagraphStyle(name="ReportText", fontName="Diario", fontSize=8.5, leading=12, spaceAfter=6))
    styles.add(ParagraphStyle(name="ReportCell", fontName="Diario", fontSize=7.5, leading=10))
    styles.add(ParagraphStyle(name="ReportHead", fontName="DiarioBold", fontSize=7.5, leading=10, textColor=GREEN))

    def para(text, style="ReportText"):
        # No markup, URLs or images from teacher-entered text are interpreted.
        clean = "".join(char for char in str(text) if char in "\n\t" or ord(char) >= 32)
        return Paragraph(escape(clean).replace("\n", "<br/>"), styles[style])

    def table(headers, data, proportions):
        matrix = [[para(item, "ReportHead") for item in headers]]
        matrix += [[para("—" if item is None or item == "" else item, "ReportCell") for item in line] for line in data]
        if len(matrix) == 1:
            return para("Nenhum registro neste recorte.")
        result = LongTable(matrix, colWidths=[width * item for item in proportions],
                           repeatRows=1, hAlign="LEFT", splitByRow=1, splitInRow=1)
        result.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), PALE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, 0), 0.7, GREEN),
            ("LINEBELOW", (0, 1), (-1, -1), 0.3, colors.HexColor("#dce3dd")),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return result

    room, term = report["classroom"], report["term"]
    story = [para("Ficha individual" if individual else "Relatório de conselho", "ReportTitle"),
             para(f"{room.school.name} | {room.name} | {room.academic_year.year}"),
             para(f"{term.name}: {date_text(term.start_date)} a {date_text(term.end_date)}"),
             para(f"Professor: {report['teacher']} | Emitido em {report['generated_at']:%d/%m/%Y %H:%M:%S}")]
    if individual:
        story.append(para(f"Aluno: {report['enrollment'].student}", "ReportHeading"))
    story.append(para("Frequência considera apenas aulas com chamada. Pendências não são presenças; "
                      "faltas justificadas integram o total de faltas. Base parcial não é resultado final. "
                      "As referências de notas não determinam aprovação oficial."))
    if report["missing_dates"]:
        story.append(para("Atenção: há matrículas com datas pendentes de revisão. Confira os vínculos antes de usar o relatório."))
    if not report["rows"]:
        story.append(para("Nenhum aluno com vínculo ou registros neste período."))
    displayed_group = False
    for group in report["groups"]:
        if not group["rows"]:
            continue
        if displayed_group:
            story.append(PageBreak())
        displayed_group = True
        book = group["book"]
        story.append(para(group["subject"].name, "ReportHeading"))
        if book:
            story.append(para(f"{book.get_calculation_display()} | Escala: {number(book.scale)} | "
                              f"Referência: {number(book.minimum)} | {book.get_rounding_display()}, {book.precision} casas | "
                              f"Recuperação: {book.get_recovery_display()}"))
            if not group["points_ready"]:
                story.append(para(f"Planejamento de pontos incompleto: {number(group['planned'])} de {number(book.scale)}."))
        else:
            story.append(para("Sem caderno de notas configurado para esta disciplina e período."))
        if not individual:
            data, frequencies = [], []
            for row in group["rows"]:
                g, f = row["grade"], row["frequency"]
                data.append([str(row["enrollment"].student), number(g["original"]) if g else None,
                             number(g["recovery"]) if g else None, number(g["final"]) if g else None,
                             g["pending"] if g else None, g["missing"] if g else None,
                             g["exempt"] if g else None, row["status"]])
                frequencies.append([str(row["enrollment"].student), f["total"], f["recorded"],
                             f["present"], f["absences"], f["justified"], f["pending"],
                             number(f["percentage"]) + "%" if f["percentage"] is not None else "Sem chamada",
                             ])
            story.append(para(f"Desempenho - {group['subject'].name}", "ReportHeading"))
            story.append(table(["Aluno", "Base / parcial", "Recuperação", "Resultado", "Notas pend.",
                                "Não entregues", "Dispensas", "Situação"],
                               data, [.25, .10, .10, .10, .08, .09, .08, .20]))
            story.append(para(f"Frequência - {group['subject'].name}", "ReportHeading"))
            story.append(table(["Aluno", "Aulas no vínculo", "Com chamada", "Presenças", "Faltas",
                                "Justificadas", "Chamada pend.", "Frequência registrada"],
                               frequencies, [.25, .10, .10, .10, .09, .10, .10, .16]))
        for row in group["rows"]:
            g, f, pupil = row["grade"], row["frequency"], row["enrollment"]
            if individual:
                story.append(para(f"Matrícula: {pupil.get_status_display()} | Entrada: {date_text(pupil.starts_on) or 'Não informada'} | "
                                  f"Saída: {date_text(pupil.ends_on) or 'Não informada'}"))
                story.append(para(f"Base / parcial: {number(g['original']) or '—'} | "
                                  f"Recuperação: {number(g['recovery']) or '—'} | "
                                  f"Resultado: {number(g['final']) or '—'} | {row['status']}"))
                story.append(para(f"Aulas no vínculo: {f['total']} | Com chamada: {f['recorded']} | "
                                  f"Presenças: {f['present']} | Faltas: {f['absences']} | Justificadas: {f['justified']} | "
                                  f"Pendentes: {f['pending']} | Frequência: {number(f['percentage']) + '%' if f['percentage'] is not None else 'Sem chamada'}"))
                story.append(para("Avaliações e observações", "ReportHeading"))
                story.append(table(["Data / avaliação", "Situação", "Nota / valor", "Observação"], [
                    [f"{date_text(item['assessment'].date)}\n{item['assessment'].title}",
                     item["status"], f"{number(item['score']) or '—'} / {number(item['assessment'].maximum)}", item["note"]]
                    for item in row["assessments"]], [.30, .20, .16, .34]))
                story.append(para("Aulas e frequência", "ReportHeading"))
                story.append(table(["Data / aulas", "Conteúdo", "Faltas / justificadas", "Justificativa"], [
                    [f"{date_text(item['lesson'].date)}\n{item['lesson'].quantity} aula(s)", item["lesson"].content,
                     f"{item['record'].absences} / {item['record'].justified_absences}" if item["record"] else "Chamada pendente",
                     item["record"].justification if item["record"] else ""]
                    for item in row["attendance"]], [.17, .43, .18, .22]))
            elif row["pending_items"] or row["observations"]:
                story.append(para(str(pupil.student), "ReportHeading"))
                for text in row["pending_items"]:
                    story.append(para("Pendente: " + text))
                for text in row["observations"]:
                    story.append(para(text))
        story.append(Spacer(1, 4 * mm))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(GREEN)
        canvas.line(15 * mm, 14 * mm, pagesize[0] - 15 * mm, 14 * mm)
        canvas.setFont("Diario", 7)
        canvas.setFillColor(GRAY)
        canvas.drawString(15 * mm, pagesize[1] - 11 * mm,
                          f"{room.name} | {term.name} | {room.academic_year.year}"[:100])
        canvas.drawString(15 * mm, 10 * mm, "Diário do Professor | Acompanhamento pedagógico")
        canvas.drawRightString(pagesize[0] - 15 * mm, 10 * mm, f"Página {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return stream.getvalue()
