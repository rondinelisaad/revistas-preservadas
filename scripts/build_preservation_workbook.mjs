import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "/Users/rondinelisaad/Downloads/repo-scielo/pablo-sos";
const outputDir = `${root}/outputs/miguilim-preservacao-2026-10-29`;
const detail = JSON.parse(
  await fs.readFile(`${root}/data/revistas_preservacao_detalhe_2026-10-29.json`, "utf8"),
);
const summary = JSON.parse(
  await fs.readFile(`${root}/data/revistas_preservacao_resumo_2026-10-29.json`, "utf8"),
);

detail.sort((a, b) => {
  const agencyDelta = b.quantidade_agencias - a.quantidade_agencias;
  if (agencyDelta !== 0) return agencyDelta;
  const statusDelta = a.situacao.localeCompare(b.situacao, "pt-BR");
  if (statusDelta !== 0) return statusDelta;
  return a.titulo.localeCompare(b.titulo, "pt-BR");
});

const workbook = Workbook.create();
const resumo = workbook.worksheets.add("Resumo");
const revistas = workbook.worksheets.add("Revistas");
const fontFamily = "Arial";
const dark = "#1F4E78";
const mid = "#5B9BD5";
const lightBlue = "#DDEBF7";
const lightGreen = "#E2F0D9";
const darkGreen = "#2E7D32";
const lightRed = "#FCE4D6";
const darkRed = "#C00000";
const lightAmber = "#FFF2CC";
const gray = "#666666";

// Summary sheet
resumo.showGridLines = false;
resumo.tabColor = dark;
resumo.getRange("A2:N2").format.font = { name: fontFamily, size: 14, bold: true, color: "#1F1F1F" };
resumo.getRange("A2").values = [["Preservação e uso de OJS nas revistas científicas brasileiras"]];
resumo.getRange("A3").values = [["Miguilim, Keepers Registry e análise técnica dos sites. Consulta em 29/10/2026."]];
resumo.getRange("A3:N3").format.font = { name: fontFamily, size: 10, italic: true, color: gray };
resumo.getRange("A4:N4").format.borders = { bottom: { style: "thin", color: "#A6A6A6" } };

const headlineRows = [
  ["Indicador", "Valor"],
  ["Revistas no Miguilim", summary.total_revistas],
  ["Com registro em agência no Keepers", summary.com_registro_keepers],
  ["Sem registro em agência no Keepers", summary.sem_registro_keepers],
  ["Cobertura no Keepers", summary.percentual_com_registro],
  ["Com duas ou mais agências", summary.com_duas_ou_mais_agencias],
];
resumo.getRange("A6:B11").values = headlineRows;

const statusRows = [
  ["Situação", "Total", "Com Keepers", "Sem Keepers", "% com Keepers"],
  ...summary.status_summary.map((row) => [
    row.situacao,
    row.total,
    row.com_registro_keepers,
    row.sem_registro_keepers,
    row.percentual_com_registro,
  ]),
];
resumo.getRange("D6:H8").values = statusRows;

const distributionRows = [
  ["Quantidade de agências", "Revistas"],
  ...summary.agency_count_distribution.map((row) => [row.quantidade_agencias, row.revistas]),
];
resumo.getRange(`A14:B${13 + distributionRows.length}`).values = distributionRows;

const agencyRows = [
  ["Agência", "Revistas do Miguilim"],
  ...summary.agency_coverage.map((row) => [row.agencia, row.revistas_miguilim]),
];
resumo.getRange(`D14:E${13 + agencyRows.length}`).values = agencyRows;

const ojsUseRows = [
  ["Resultado da análise OJS", "Revistas"],
  ...summary.ojs_summary.analysis_status.map((row) => [row.status, row.revistas]),
];
resumo.getRange(`J6:K${5 + ojsUseRows.length}`).values = ojsUseRows;

const ojsVerificationRows = [
  ["Verificação de versão", "Revistas"],
  ...summary.ojs_summary.verification_status.map((row) => [row.status, row.revistas]),
];
resumo.getRange(`M6:N${5 + ojsVerificationRows.length}`).values = ojsVerificationRows;

const ojsFamilyRows = [
  ["Família OJS", "Revistas"],
  ...summary.ojs_summary.version_families.map((row) => [row.familia, row.revistas]),
];
resumo.getRange(`J18:K${17 + ojsFamilyRows.length}`).values = ojsFamilyRows;

const ojsVersionRows = [
  ["Versão OJS detectada", "Revistas"],
  ...summary.ojs_summary.versions.slice(0, 15).map((row) => [row.versao, row.revistas]),
];
resumo.getRange(`M18:N${17 + ojsVersionRows.length}`).values = ojsVersionRows;

for (const header of ["A6:B6", "D6:H6", "A14:B14", "D14:E14", "J6:K6", "M6:N6", "J18:K18", "M18:N18"]) {
  resumo.getRange(header).format = {
    fill: dark,
    font: { name: fontFamily, size: 10, bold: true, color: "#FFFFFF" },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    borders: { preset: "outside", style: "thin", color: dark },
  };
}

resumo.getRange("A7:H30").format.font = { name: fontFamily, size: 10, color: "#1F1F1F" };
resumo.getRange("J7:N34").format.font = { name: fontFamily, size: 10, color: "#1F1F1F" };
resumo.getRange("A14:B14").format.font = { name: fontFamily, size: 10, bold: true, color: "#FFFFFF" };
resumo.getRange("D14:E14").format.font = { name: fontFamily, size: 10, bold: true, color: "#FFFFFF" };
resumo.getRange("A7:A11").format.fill = lightBlue;
resumo.getRange("B7:B11").format.font = { name: fontFamily, size: 11, bold: true, color: dark };
resumo.getRange("B7:B9").format.numberFormat = "#,##0";
resumo.getRange("B10").format.numberFormat = "0.0%";
resumo.getRange("B11").format.numberFormat = "#,##0";
resumo.getRange("E7:G8").format.numberFormat = "#,##0";
resumo.getRange("H7:H8").format.numberFormat = "0.0%";
resumo.getRange(`A15:B${13 + distributionRows.length}`).format.verticalAlignment = "center";
resumo.getRange(`B15:B${13 + distributionRows.length}`).format.numberFormat = "#,##0";
resumo.getRange(`E15:E${13 + agencyRows.length}`).format.numberFormat = "#,##0";
resumo.getRange(`K7:K${5 + ojsUseRows.length}`).format.numberFormat = "#,##0";
resumo.getRange(`N7:N${5 + ojsVerificationRows.length}`).format.numberFormat = "#,##0";
resumo.getRange(`K19:K${17 + ojsFamilyRows.length}`).format.numberFormat = "#,##0";
resumo.getRange(`N19:N${17 + ojsVersionRows.length}`).format.numberFormat = "#,##0";
resumo.getRange("A6:B11").format.borders = { preset: "outside", style: "thin", color: "#B4C7E7" };
resumo.getRange("D6:H8").format.borders = { preset: "outside", style: "thin", color: "#B4C7E7" };
resumo.getRange(`A14:B${13 + distributionRows.length}`).format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
resumo.getRange(`D14:E${13 + agencyRows.length}`).format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
resumo.getRange(`J6:K${5 + ojsUseRows.length}`).format.borders = { preset: "outside", style: "thin", color: "#B4C7E7" };
resumo.getRange(`M6:N${5 + ojsVerificationRows.length}`).format.borders = { preset: "outside", style: "thin", color: "#B4C7E7" };
resumo.getRange(`J18:K${17 + ojsFamilyRows.length}`).format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };
resumo.getRange(`M18:N${17 + ojsVersionRows.length}`).format.borders = { preset: "outside", style: "thin", color: "#D9E2F3" };

resumo.getRange("A36").values = [["Definição"]];
resumo.getRange("A36").format.font = { name: fontFamily, size: 10, bold: true, color: dark };
resumo.getRange("A37").values = [[`${summary.method.definition} ${summary.method.ojs_definition}`]];
resumo.getRange("A37").format = { font: { name: fontFamily, size: 10, color: "#1F1F1F" }, wrapText: true };
resumo.getRange("A39").values = [["Fontes"]];
resumo.getRange("A39").format.font = { name: fontFamily, size: 10, bold: true, color: dark };
resumo.getRange("A40").values = [["Miguilim: https://miguilim.ibict.br/simple-search (coleção Revistas científicas)"]];
resumo.getRange("A41").values = [["Keepers Registry: https://keepers.issn.org/advancedsearch (Country: Brazil; The Keepers: yes)"]];
resumo.getRange("A42").values = [["Sites das revistas: uma requisição por instalação, até três hosts simultâneos, cache e sem retries."]];
resumo.getRange("A40:A42").format.font = { name: fontFamily, size: 9, color: gray };

const summaryWidths = { A: 42, B: 16, C: 3, D: 48, E: 18, F: 18, G: 18, H: 18, I: 3, J: 36, K: 15, L: 3, M: 44, N: 15 };
for (const [col, width] of Object.entries(summaryWidths)) resumo.getRange(`${col}:${col}`).format.columnWidth = width;
resumo.getRange("2:2").format.rowHeight = 24;
resumo.getRange("37:37").format.rowHeight = 60;

// Detail sheet
revistas.showGridLines = false;
revistas.getRange("A2").values = [["Revistas, estado de preservação e análise de OJS"]];
revistas.getRange("A2:Y2").format.font = { name: fontFamily, size: 14, bold: true, color: "#1F1F1F" };
revistas.getRange("A3:B4").values = [
  ["Fonte Miguilim", "https://miguilim.ibict.br/simple-search"],
  ["Critério Keepers", "ISSN presente em pelo menos uma agência no Archival Status"],
];
revistas.getRange("A3:A4").format.font = { name: fontFamily, size: 9, bold: true, color: dark };
revistas.getRange("B3:B4").format.font = { name: fontFamily, size: 9, color: gray };

const headers = [
  "Título",
  "ISSN",
  "ISSN-L",
  "Situação",
  "Estado de preservação",
  "Nº de agências",
  "Agências",
  "Estratégia declarada no Miguilim",
  "Software declarado no Miguilim",
  "OJS declarado no Miguilim?",
  "Resultado da análise OJS",
  "Versão OJS detectada",
  "Estado da verificação OJS",
  "Código/erro do site",
  "URL consultada para OJS",
  "Evidência da versão",
  "Instituição editora",
  "UF",
  "Cidade",
  "Ano de início",
  "Ano de fim",
  "URL Miguilim",
  "URL Archival Status",
  "Atualização no Miguilim",
  "ID Miguilim",
];
const rows = detail.map((row) => [
  row.titulo,
  row.issn,
  row.issn_l,
  row.situacao,
  row.estado_preservacao,
  row.quantidade_agencias,
  row.agencias,
  row.estrategia_declarada_miguilim,
  row.software_declarado_miguilim,
  row.usa_ojs,
  row.resultado_analise_ojs,
  row.versao_ojs_detectada,
  row.estado_verificacao_ojs,
  row.codigo_erro_site,
  row.url_consultada_ojs,
  row.evidencia_ojs,
  row.instituicao_editora,
  row.uf,
  row.cidade,
  row.ano_inicio,
  row.ano_fim,
  row.url_miguilim,
  row.url_archival_status,
  row.data_atualizacao_miguilim,
  row.id_miguilim,
]);
const dataStart = 7;
const dataEnd = dataStart + rows.length - 1;
revistas.getRange("A6:Y6").values = [headers];
revistas.getRange(`A${dataStart}:Y${dataEnd}`).values = rows;
const table = revistas.tables.add(`A6:Y${dataEnd}`, true, "RevistasPreservacao");
table.style = "TableStyleMedium2";
table.showBandedRows = true;
table.showFilterButton = true;

revistas.getRange("A6:Y6").format = {
  fill: dark,
  font: { name: fontFamily, size: 10, bold: true, color: "#FFFFFF" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
};
revistas.getRange(`A${dataStart}:Y${dataEnd}`).format.font = { name: fontFamily, size: 9, color: "#1F1F1F" };
revistas.getRange(`A${dataStart}:Y${dataEnd}`).format.verticalAlignment = "center";
revistas.getRange(`B${dataStart}:C${dataEnd}`).format.numberFormat = "@";
revistas.getRange(`F${dataStart}:F${dataEnd}`).format.numberFormat = "0";
revistas.getRange(`F${dataStart}:F${dataEnd}`).format.horizontalAlignment = "center";
revistas.getRange(`D${dataStart}:F${dataEnd}`).format.horizontalAlignment = "center";
revistas.getRange(`J${dataStart}:N${dataEnd}`).format.horizontalAlignment = "center";

revistas.getRange(`F${dataStart}:F${dataEnd}`).conditionalFormats.add("cellIs", {
  operator: "greaterThan",
  formula: 0,
  format: { fill: lightGreen, font: { bold: true, color: darkGreen } },
});
revistas.getRange(`F${dataStart}:F${dataEnd}`).conditionalFormats.add("cellIs", {
  operator: "equal",
  formula: 0,
  format: { fill: lightRed, font: { color: darkRed } },
});
revistas.getRange(`D${dataStart}:D${dataEnd}`).conditionalFormats.add("containsText", {
  text: "Descontinuada",
  format: { fill: lightAmber, font: { color: "#7F6000" } },
});
revistas.getRange(`J${dataStart}:J${dataEnd}`).conditionalFormats.add("containsText", {
  text: "Sim",
  format: { fill: lightGreen, font: { bold: true, color: darkGreen } },
});
revistas.getRange(`K${dataStart}:K${dataEnd}`).conditionalFormats.add("containsText", {
  text: "confirmado",
  format: { fill: lightGreen, font: { bold: true, color: darkGreen } },
});
revistas.getRange(`K${dataStart}:K${dataEnd}`).conditionalFormats.add("containsText", {
  text: "não concluída",
  format: { fill: lightRed, font: { color: darkRed } },
});
revistas.getRange(`J${dataStart}:J${dataEnd}`).conditionalFormats.add("containsText", {
  text: "Não identificado",
  format: { fill: lightAmber, font: { color: "#7F6000" } },
});

const detailWidths = {
  A: 42,
  B: 12,
  C: 12,
  D: 16,
  E: 34,
  F: 12,
  G: 48,
  H: 36,
  I: 34,
  J: 22,
  K: 42,
  L: 18,
  M: 44,
  N: 28,
  O: 44,
  P: 36,
  Q: 42,
  R: 20,
  S: 20,
  T: 12,
  U: 12,
  V: 44,
  W: 44,
  X: 24,
  Y: 38,
};
for (const [col, width] of Object.entries(detailWidths)) revistas.getRange(`${col}:${col}`).format.columnWidth = width;
revistas.getRange("6:6").format.rowHeight = 34;
revistas.freezePanes.freezeRows(6);
revistas.freezePanes.freezeColumns(3);

workbook.recalculate();
await fs.mkdir(outputDir, { recursive: true });

const summaryCheck = await workbook.inspect({
  kind: "table",
  range: "Resumo!A2:N42",
  include: "values,formulas",
  tableMaxRows: 30,
  tableMaxCols: 10,
  maxChars: 12000,
});
console.log(summaryCheck.ndjson);

const detailCheck = await workbook.inspect({
  kind: "table",
  range: "Revistas!A2:Y16",
  include: "values,formulas",
  tableMaxRows: 16,
  tableMaxCols: 25,
  maxChars: 12000,
});
console.log(detailCheck.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const summaryPreview = await workbook.render({ sheetName: "Resumo", range: "A1:N42", scale: 1.05, format: "png" });
await fs.writeFile(`${outputDir}/preview_resumo.png`, new Uint8Array(await summaryPreview.arrayBuffer()));
const detailPreview = await workbook.render({ sheetName: "Revistas", range: "A1:Y18", scale: 0.75, format: "png" });
await fs.writeFile(`${outputDir}/preview_revistas.png`, new Uint8Array(await detailPreview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(workbook);
const outputPath = `${outputDir}/preservacao_revistas_brasileiras_2026-10-29.xlsx`;
await output.save(outputPath);
const savedWorkbook = await SpreadsheetFile.importXlsx(await FileBlob.load(outputPath));
const savedCheck = await savedWorkbook.inspect({
  kind: "sheet,table",
  maxChars: 5000,
  tableMaxRows: 3,
  tableMaxCols: 5,
});
console.log(savedCheck.ndjson);
console.log(`Workbook salvo com ${rows.length} revistas.`);
