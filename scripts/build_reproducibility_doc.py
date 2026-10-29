#!/usr/bin/env python3
"""Build the reproducibility protocol for the Miguilim preservation and OJS survey."""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = (
    ROOT
    / "outputs"
    / "miguilim-preservacao-2026-10-29"
    / "documentacao"
    / "protocolo_reprodutibilidade_preservacao_ojs_2026-10-29.docx"
)

NAVY = "1F4E78"
PALE_BLUE = "DDEBF7"
PALE_GRAY = "F2F2F2"
BORDER = "D9D9D9"
BLACK = RGBColor(0, 0, 0)
GRAY = RGBColor(89, 89, 89)


def set_cell_shading(cell, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), color)


def set_cell_border(cell, color: str = BORDER, size: str = "6") -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_borders = tc_pr.first_child_found_in("w:tcBorders")
    if tc_borders is None:
        tc_borders = OxmlElement("w:tcBorders")
        tc_pr.append(tc_borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = tc_borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            tc_borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), size)
        element.set(qn("w:color"), color)


def set_cell_margins(cell, top: int = 90, start: int = 110, bottom: int = 90, end: int = 110) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = tr_pr.find(qn("w:cantSplit"))
    if cant_split is None:
        cant_split = OxmlElement("w:cantSplit")
        cant_split.set(qn("w:val"), "true")
        tr_pr.append(cant_split)


def set_col_width(cell, width: float) -> None:
    cell.width = Inches(width)
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width * 1440)))
    tc_w.set(qn("w:type"), "dxa")


def keep_with_next(paragraph) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    keep = p_pr.find(qn("w:keepNext"))
    if keep is None:
        keep = OxmlElement("w:keepNext")
        p_pr.append(keep)


def add_table(doc: Document, headers: list[str], rows: list[list[str]], widths: list[float]):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    header = table.rows[0]
    set_repeat_table_header(header)
    for index, text in enumerate(headers):
        cell = header.cells[index]
        set_col_width(cell, widths[index])
        set_cell_shading(cell, NAVY)
        set_cell_border(cell)
        set_cell_margins(cell)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.bold = True
        run.font.color.rgb = RGBColor(255, 255, 255)
        run.font.size = Pt(9)

    for row_index, values in enumerate(rows):
        row = table.add_row()
        prevent_row_split(row)
        for col_index, text in enumerate(values):
            cell = row.cells[col_index]
            set_col_width(cell, widths[col_index])
            set_cell_border(cell)
            set_cell_margins(cell)
            if row_index % 2:
                set_cell_shading(cell, PALE_GRAY)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            paragraph = cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.05
            run = paragraph.add_run(str(text))
            run.font.size = Pt(9)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return table


def add_bullet(doc: Document, text: str, level: int = 0) -> None:
    style = "List Bullet" if level == 0 else "List Bullet 2"
    paragraph = doc.add_paragraph(style=style)
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.add_run(text)


def add_number(doc: Document, text: str, level: int = 0) -> None:
    style = "List Number" if level == 0 else "List Number 2"
    paragraph = doc.add_paragraph(style=style)
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.add_run(text)


def add_numbered_items(doc: Document, items: list[str]) -> None:
    for index, text in enumerate(items, 1):
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.left_indent = Inches(0.28)
        paragraph.paragraph_format.first_line_indent = Inches(-0.22)
        paragraph.paragraph_format.space_after = Pt(4)
        paragraph.add_run(f"{index}. ")
        paragraph.add_run(text)


def add_code(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph(style="Code")
    paragraph.paragraph_format.left_indent = Inches(0.35)
    paragraph.paragraph_format.right_indent = Inches(0.2)
    paragraph.paragraph_format.space_before = Pt(2)
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.add_run(text)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_char_1 = OxmlElement("w:fldChar")
    fld_char_1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char_2 = OxmlElement("w:fldChar")
    fld_char_2.set(qn("w:fldCharType"), "end")
    run._r.extend([fld_char_1, instr_text, fld_char_2])
    run.font.size = Pt(9)
    run.font.color.rgb = GRAY


def style_document(doc: Document) -> None:
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Arial"
    normal._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    normal.font.size = Pt(11)
    normal.font.color.rgb = BLACK
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.12

    title = styles["Title"]
    title.font.name = "Arial"
    title._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    title._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    title.font.size = Pt(24)
    title.font.bold = True
    title.font.color.rgb = BLACK
    title.paragraph_format.space_after = Pt(14)
    title_ppr = title._element.get_or_add_pPr()
    title_border = title_ppr.find(qn("w:pBdr"))
    if title_border is not None:
        title_ppr.remove(title_border)

    subtitle = styles["Subtitle"]
    subtitle.font.name = "Arial"
    subtitle._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
    subtitle._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
    subtitle.font.size = Pt(12)
    subtitle.font.color.rgb = GRAY
    subtitle.paragraph_format.space_after = Pt(8)

    for name, size, before, after in (
        ("Heading 1", 16, 16, 7),
        ("Heading 2", 13, 12, 5),
        ("Heading 3", 11, 9, 4),
    ):
        style = styles[name]
        style.font.name = "Arial"
        style._element.rPr.rFonts.set(qn("w:ascii"), "Arial")
        style._element.rPr.rFonts.set(qn("w:hAnsi"), "Arial")
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = BLACK
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True

    code = styles.add_style("Code", 1)
    code.font.name = "Courier New"
    code._element.rPr.rFonts.set(qn("w:ascii"), "Courier New")
    code._element.rPr.rFonts.set(qn("w:hAnsi"), "Courier New")
    code.font.size = Pt(9)
    code.font.color.rgb = BLACK
    code.paragraph_format.line_spacing = 1.0


def main() -> None:
    doc = Document()
    style_document(doc)
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.8)
    section.bottom_margin = Inches(0.75)
    section.left_margin = Inches(0.85)
    section.right_margin = Inches(0.85)

    footer = section.footer
    add_page_number(footer.paragraphs[0])

    # Cover
    doc.add_paragraph().paragraph_format.space_after = Pt(42)
    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.add_run("Protocolo de reprodutibilidade do levantamento de preservação e uso de OJS em revistas brasileiras")
    subtitle = doc.add_paragraph(style="Subtitle")
    subtitle.add_run("Fontes Miguilim e Keepers Registry")
    date_line = doc.add_paragraph(style="Subtitle")
    date_line.add_run("Data de referência 29 de outubro de 2026")
    version_line = doc.add_paragraph(style="Subtitle")
    version_line.add_run("Versão 1.0")
    doc.add_paragraph().paragraph_format.space_after = Pt(42)
    opening = doc.add_paragraph()
    opening.paragraph_format.space_after = Pt(10)
    run = opening.add_run(
        "Este protocolo permite reproduzir o cruzamento de 5.379 revistas científicas brasileiras "
        "com o estado de preservação registrado no Keepers Registry e a análise de uso e versão do "
        "Open Journal Systems. O procedimento conserva snapshots, caches e evidências por instalação "
        "para evitar consultas repetidas aos serviços externos."
    )
    run.font.size = Pt(12)
    run.bold = True
    doc.add_page_break()

    # 1
    doc.add_heading("1 Objetivo e escopo", level=1)
    doc.add_paragraph(
        "O levantamento cobre revistas vigentes e descontinuadas presentes no snapshot do Miguilim. "
        "Para cada revista, o procedimento registra a situação editorial, os identificadores ISSN e "
        "ISSN L, a presença em agências de preservação, a quantidade de agências, o software editorial "
        "declarado e o resultado da análise técnica de OJS."
    )
    doc.add_paragraph(
        "A unidade principal é a revista. As consultas técnicas aos sites são deduplicadas por instalação "
        "para reduzir carga. Os resultados por instalação são depois propagados às revistas associadas, "
        "com distinção explícita entre declaração, confirmação técnica e inferência."
    )

    doc.add_heading("2 Resultado de referência", level=1)
    add_table(
        doc,
        ["Indicador", "Resultado em 29 de outubro de 2026"],
        [
            ["Revistas no Miguilim", "5.379"],
            ["Revistas vigentes", "4.969"],
            ["Revistas descontinuadas", "410"],
            ["Com registro em agência no Keepers", "2.531"],
            ["Sem registro em agência no Keepers", "2.848"],
            ["Com duas ou mais agências", "599"],
            ["OJS declarado no Miguilim", "1.919"],
            ["OJS confirmado tecnicamente sem declaração", "779"],
            ["OJS provável por instalação compartilhada", "850"],
            ["OJS provável por assinaturas técnicas", "24"],
            ["Revistas com versão OJS identificada", "2.880"],
        ],
        [4.75, 1.8],
    )
    doc.add_paragraph(
        "Esses números funcionam como controle de reprodução exata. Uma coleta feita em outra data pode "
        "produzir valores diferentes porque os registros do Miguilim, do Keepers Registry e os sites das "
        "revistas são dinâmicos."
    )

    doc.add_page_break()
    doc.add_heading("3 Fontes e snapshots", level=1)
    add_table(
        doc,
        ["Fonte", "Uso", "Snapshot ou endereço"],
        [
            [
                "Miguilim",
                "Universo de revistas e metadados editoriais",
                "data/miguilim_revistas_2026-10-29.csv\nhttps://miguilim.ibict.br/simple-search",
            ],
            [
                "Keepers Registry",
                "Archival Status e agências de preservação",
                "data/keepers_brazil_agencies_2026-10-29.csv\nhttps://keepers.issn.org/advancedsearch",
            ],
            [
                "Sites das revistas",
                "Assinaturas públicas de OJS, versão e erros de acesso",
                "Caches JSON em data/ojs_detection_cache e data/ojs_undeclared_scan_cache",
            ],
        ],
        [1.45, 2.15, 2.95],
    )
    doc.add_paragraph(
        "O CSV do Miguilim é o snapshot inicial desta reprodução. O repositório atual não contém um "
        "coletor que gere esse arquivo a partir do portal. Para repetir exatamente o levantamento, deve-se "
        "usar o arquivo com o hash informado no apêndice. Para atualizar o estudo, deve-se exportar novamente "
        "a coleção Revistas científicas preservando os mesmos campos e registrar a nova data de referência."
    )

    doc.add_heading("4 Ambiente de execução", level=1)
    add_table(
        doc,
        ["Componente", "Versão usada", "Finalidade"],
        [
            ["Python", "3.12.14", "Coleta, cache, classificação e consolidação"],
            ["Node.js", "24.19.0", "Geração da planilha final"],
            ["Biblioteca de planilhas", "@oai/artifact-tool 2.8.58 ou superior", "Exportação XLSX e verificação"],
            ["Sistema de arquivos", "UTF 8", "Leitura e escrita dos CSV e JSON"],
        ],
        [1.55, 2.0, 3.0],
    )
    doc.add_paragraph(
        "Os coletores usam apenas módulos da biblioteca padrão do Python. A reprodução da planilha exige "
        "a dependência Node indicada. Os comandos abaixo devem ser executados na raiz do projeto."
    )

    doc.add_heading("5 Estrutura dos arquivos", level=1)
    add_table(
        doc,
        ["Caminho", "Papel no fluxo"],
        [
            ["data/miguilim_revistas_2026-10-29.csv", "Entrada principal com 5.379 revistas"],
            ["data/keepers_cache", "Páginas do Keepers mantidas para evitar novas consultas"],
            ["data/ojs_detection_cache", "Uma resposta por instalação OJS declarada"],
            ["data/ojs_undeclared_scan_cache", "Uma resposta por instalação sem declaração"],
            ["data/revistas_preservacao_detalhe_2026-10-29.json", "Tabela consolidada usada pela planilha"],
            ["data/revistas_preservacao_resumo_2026-10-29.json", "Totais e distribuições de controle"],
        ],
        [3.65, 2.9],
    )

    doc.add_heading("6 Procedimento de reprodução", level=1)
    doc.add_heading("6 1 Preservação no Keepers Registry", level=2)
    doc.add_paragraph(
        "O coletor consulta as facetas públicas por país e agência. Ele usa páginas de 100 registros, mantém "
        "cache local e respeita intervalo de 10,5 segundos, superior ao Crawl delay de 10 segundos observado. "
        "As duas facetas do programa chinês são reunidas sob um único nome canônico."
    )
    add_code(doc, "python3 scripts/collect_keepers_brazil.py")
    doc.add_paragraph(
        "As contagens esperadas das facetas estão registradas no script. Em uma atualização futura, essas "
        "contagens devem ser lidas novamente no portal e atualizadas antes da execução. Uma divergência encerra "
        "o processo para evitar a publicação de um resultado incompleto."
    )

    doc.add_heading("6 2 Versões das revistas que declaram OJS", level=2)
    doc.add_paragraph(
        "O campo de software do Miguilim identifica 1.919 revistas que declaram Open Journal Systems ou OJS. "
        "Esses registros são agrupados em 560 instalações. Cada instalação recebe uma única consulta representativa."
    )
    add_code(doc, "python3 scripts/collect_ojs_versions.py")
    doc.add_paragraph(
        "A versão é extraída principalmente do elemento meta generator. O coletor também registra a URL final, "
        "o código HTTP, a evidência textual e o erro de rede quando a resposta não é concluída."
    )

    doc.add_heading("6 3 Revalidação das falhas", level=2)
    doc.add_paragraph(
        "As 73 instalações que falharam na primeira consulta são verificadas uma segunda vez. Essa etapa registra "
        "HTTP, DNS, timeout, certificado TLS, conexão recusada e outras categorias sem tentar repetidamente o mesmo site."
    )
    add_code(doc, "python3 scripts/revalidate_ojs_access_errors.py")

    doc.add_heading("6 4 Análise das revistas sem software declarado", level=2)
    doc.add_paragraph(
        "Primeiro, a análise passiva associa revistas à mesma chave de instalação das revistas que declaram OJS. "
        "Depois, as instalações ainda não classificadas recebem uma consulta técnica controlada."
    )
    add_code(doc, "python3 scripts/analyze_undeclared_ojs.py")
    add_code(doc, "python3 scripts/scan_undeclared_ojs_sites.py")

    doc.add_heading("6 5 Consolidação e geração da planilha", level=2)
    add_code(doc, "python3 scripts/prepare_miguilim_preservation.py")
    add_code(doc, "node scripts/build_preservation_workbook.mjs")
    doc.add_paragraph(
        "A primeira etapa cruza os ISSNs, propaga os resultados por instalação e produz os arquivos detalhado e "
        "resumo. A segunda gera a planilha com as abas Resumo e Revistas, aplica os formatos e executa verificações "
        "de conteúdo e erros de fórmula antes da exportação."
    )

    doc.add_heading("7 Chaves de correspondência", level=1)
    doc.add_heading("7 1 Preservação", level=2)
    doc.add_paragraph(
        "O cruzamento com o Keepers Registry usa o ISSN do campo dc.identifier.issn do Miguilim em letras "
        "maiúsculas. Uma revista é marcada como preservada quando esse ISSN aparece em pelo menos uma agência. "
        "A quantidade corresponde ao número de agências distintas."
    )
    doc.add_heading("7 2 Instalação OJS", level=2)
    doc.add_paragraph(
        "A chave de instalação combina o host em letras minúsculas com o prefixo do caminho anterior a "
        "/index.php/. Quando o marcador não existe, a chave usa somente o host. Essa regra reduz consultas, mas "
        "pode agrupar instalações diferentes que compartilham host e não expõem o marcador."
    )

    doc.add_heading("8 Regras de classificação de OJS", level=1)
    add_table(
        doc,
        ["Categoria", "Critério", "Interpretação"],
        [
            ["OJS declarado no Miguilim", "Campo Software utilizado contém Open Journal Systems ou OJS", "Declaração da fonte"],
            ["OJS confirmado tecnicamente", "Meta generator, texto Open Journal Systems ou OJS acompanhado de versão", "Evidência direta na página"],
            ["OJS provável por instalação compartilhada", "Mesma chave de instalação de revista com declaração explícita", "Inferência de alta confiança"],
            ["OJS provável por assinaturas técnicas", "Ao menos duas assinaturas públicas, ou cookie OJSSID", "Indício técnico sem declaração direta"],
            ["OJS não identificado", "Página respondeu sem evidência suficiente", "Não confirma ausência de OJS"],
            ["Consulta técnica não concluída", "Erro HTTP, DNS, TLS, timeout ou conexão", "Resultado indeterminado"],
            ["Sem URL válida", "URL ausente ou sem host", "Análise técnica impossível"],
        ],
        [2.15, 2.8, 1.6],
    )
    doc.add_paragraph(
        "A versão só é preenchida quando aparece em evidência pública ou quando a revista compartilha uma instalação "
        "cuja versão foi observada. Padrões de URL, aparência visual e nome do domínio não são usados isoladamente "
        "para afirmar uso ou versão de OJS."
    )

    doc.add_heading("9 Política de acesso responsável", level=1)
    add_table(
        doc,
        ["Etapa", "Escopo", "Concorrência", "Timeout", "Retries", "Limite de resposta"],
        [
            ["Keepers", "Páginas de faceta", "Sequencial", "60 s", "Até 3", "Página completa"],
            ["OJS declarado", "560 instalações", "6 workers", "20 s", "0", "2 MB"],
            ["Revalidação", "73 instalações", "3 workers", "25 s", "0", "64 KiB"],
            ["OJS não declarado", "1.788 instalações em 1.755 hosts", "3 hosts", "20 s", "0", "1 MB"],
        ],
        [1.2, 1.75, 0.85, 0.65, 0.55, 1.05],
    )
    add_bullet(doc, "Todos os coletores gravam cache e reutilizam respostas existentes.")
    add_bullet(doc, "Instalações do mesmo host são processadas sequencialmente, com intervalo de 1,5 segundo na varredura sem declaração.")
    add_bullet(doc, "Os coletores OJS não fazem retries automáticos.")
    add_bullet(doc, "O User Agent usado foi Mozilla/5.0 preservation-research/1.0.")

    doc.add_heading("10 Controles de qualidade", level=1)
    add_numbered_items(
        doc,
        [
            "Confirmar que o snapshot do Miguilim contém 5.379 linhas de dados.",
            "Verificar que 4.969 registros são vigentes e 410 são descontinuados.",
            "Reconciliar 2.531 revistas com Keepers e 2.848 sem Keepers.",
            "Reconciliar todas as categorias OJS em 5.379 revistas sem duplicação.",
            "Confirmar 2.880 revistas com versão OJS preenchida.",
            "Examinar códigos HTTP e erros de rede sem convertê-los em ausência de OJS.",
            "Inspecionar a planilha exportada e procurar erros de fórmula como REF, DIV 0, VALUE e NAME.",
            "Renderizar as abas alteradas para verificar legibilidade, cabeçalhos e colunas.",
        ],
    )

    doc.add_heading("11 Limitações", level=1)
    add_bullet(doc, "O snapshot do Miguilim depende de uma exportação externa ao pipeline atual.")
    add_bullet(doc, "O Archival Status pode mudar depois da data de referência.")
    add_bullet(doc, "Sites inacessíveis permanecem indeterminados, inclusive quando o erro é temporário.")
    add_bullet(doc, "Algumas instalações não expõem a versão no meta generator.")
    add_bullet(doc, "A correlação por host pode agrupar portais diferentes quando a URL não contém /index.php/.")
    add_bullet(doc, "A classificação OJS provável não deve ser apresentada como declaração formal da revista.")
    add_bullet(doc, "As versões 3.4.6.2 e 3.3.9.9 foram mantidas porque apareceram no meta generator dos sites; não foram normalizadas para uma versão oficial presumida.")

    doc.add_heading("12 Atualização do levantamento", level=1)
    doc.add_paragraph(
        "Uma atualização deve ser publicada em uma nova pasta de data, sem sobrescrever os snapshots anteriores. "
        "Antes da coleta, registre a data, atualize as contagens das facetas do Keepers e mantenha os caches antigos "
        "como evidência. Depois da execução, compare os totais com a edição anterior e investigue variações abruptas "
        "antes de divulgar o novo arquivo."
    )
    add_numbered_items(
        doc,
        [
            "Exportar um novo snapshot do Miguilim com o mesmo esquema de campos.",
            "Atualizar nomes de arquivos e datas constantes nos scripts.",
            "Revisar as facetas e contagens esperadas do Keepers.",
            "Executar os scripts na ordem apresentada na seção 6.",
            "Gerar novos hashes SHA 256 e anexá-los à documentação da nova edição.",
        ],
    )

    doc.add_heading("Apêndice A Comandos em ordem", level=1)
    commands = [
        "python3 scripts/collect_keepers_brazil.py",
        "python3 scripts/collect_ojs_versions.py",
        "python3 scripts/revalidate_ojs_access_errors.py",
        "python3 scripts/analyze_undeclared_ojs.py",
        "python3 scripts/scan_undeclared_ojs_sites.py",
        "python3 scripts/prepare_miguilim_preservation.py",
        "node scripts/build_preservation_workbook.mjs",
    ]
    for command in commands:
        add_code(doc, command)

    doc.add_heading("Apêndice B Arquivos finais", level=1)
    add_bullet(doc, "outputs/miguilim-preservacao-2026-10-29/preservacao_revistas_brasileiras_2026-10-29.xlsx")
    add_bullet(doc, "data/revistas_preservacao_detalhe_2026-10-29.csv")
    add_bullet(doc, "data/ojs_access_revalidation_2026-10-29.csv")
    add_bullet(doc, "data/ojs_undeclared_active_scan_2026-10-29.csv")

    doc.add_heading("Apêndice C Hashes SHA 256", level=1)
    hashes = [
        ("data/miguilim_revistas_2026-10-29.csv", "c37234cf0687531ca4164ed0845e1a1d428ee89ebc6fa72bafb66919dfd7a5da"),
        ("data/keepers_brazil_agencies_2026-10-29.csv", "451655469147c7b42fa910b11db4edb816fbc24e8eb1f6eecacd4f0e161d80e9"),
        ("data/ojs_instance_detection_2026-10-29.json", "47280469a3dccc49a0dc53de1dd33b9611b160f661b7607e1300856ff194c9a4"),
        ("data/ojs_access_revalidation_2026-10-29.json", "917dc0c0431c4a843c73fb04874794ce5ae67ffe3a81d09c19c2f0cd56c0de4c"),
        ("data/ojs_undeclared_active_scan_2026-10-29.json", "8463ad794df87ab03db5d6c85f75bbb5e602f2ac613eba6dc99f7cf3936dc905"),
        ("data/revistas_preservacao_resumo_2026-10-29.json", "2a98d7d62572963dfcf52d7680084586fb75b96ffb6caa4044890a97148f3a7e"),
        ("scripts/collect_keepers_brazil.py", "ee727fb146f2813b13ae31d8efa7486890305ebf0b7ce8104416d4f8e94ef56b"),
        ("scripts/collect_ojs_versions.py", "f298d5bb06bc49e7ef8790fcf651c6301ee791583e4d8469d2006702a9a040f9"),
        ("scripts/revalidate_ojs_access_errors.py", "c2ce15a6d151e2b358f79cf172b5a9f7c2362ee1b1f9d5b1e3ceec4161fdd60d"),
        ("scripts/analyze_undeclared_ojs.py", "e3c4a559096bd5c102bb8bcd647238a04c8b7958b0f38987433850b532905fe8"),
        ("scripts/scan_undeclared_ojs_sites.py", "f744e3a8e48cb979ceff008f09efe921a91d4f0e1693edf5f447daf163b21836"),
        ("scripts/prepare_miguilim_preservation.py", "b1283072e3616c16bed800259671e57db786e9b9b8960b628539564f78e9af78"),
        ("scripts/build_preservation_workbook.mjs", "68c84ada9ce20f380c7010d815e1a942a1d0830b82e6f67648cad5d22ef70d3c"),
    ]
    add_table(doc, ["Arquivo", "SHA 256"], [[path, digest] for path, digest in hashes], [3.25, 3.3])

    # Keep headings with the content that follows and remove accidental empty trailing paragraphs.
    for paragraph in doc.paragraphs:
        if paragraph.style.name.startswith("Heading"):
            keep_with_next(paragraph)

    doc.core_properties.title = "Protocolo de reprodutibilidade do levantamento de preservação e uso de OJS em revistas brasileiras"
    doc.core_properties.subject = "Método, fontes, comandos, controles e limitações"
    doc.core_properties.keywords = "Miguilim, Keepers Registry, OJS, preservação digital, reprodutibilidade"
    doc.core_properties.author = ""
    doc.core_properties.last_modified_by = ""

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()
