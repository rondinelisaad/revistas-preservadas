# Protocolo de reprodutibilidade do levantamento de preservação e uso de OJS em revistas brasileiras

**Fontes:** Miguilim e Keepers Registry  
**Data de referência:** 29 de outubro de 2026  
**Versão:** 1.0

Este protocolo permite reproduzir o cruzamento de 5.379 revistas científicas brasileiras com o estado de preservação registrado no Keepers Registry e a análise de uso e versão do Open Journal Systems. O procedimento conserva snapshots, caches e evidências por instalação para evitar consultas repetidas aos serviços externos.

## 1. Objetivo e escopo

O levantamento cobre revistas vigentes e descontinuadas presentes no snapshot do Miguilim. Para cada revista, o procedimento registra a situação editorial, os identificadores ISSN e ISSN-L, a presença em agências de preservação, a quantidade de agências, o software editorial declarado e o resultado da análise técnica de OJS.

A unidade principal é a revista. As consultas técnicas aos sites são deduplicadas por instalação para reduzir carga. Os resultados por instalação são depois propagados às revistas associadas, com distinção explícita entre declaração, confirmação técnica e inferência.

## 2. Resultado de referência

| Indicador | Resultado em 29 de outubro de 2026 |
|---|---:|
| Revistas no Miguilim | 5.379 |
| Revistas vigentes | 4.969 |
| Revistas descontinuadas | 410 |
| Com registro em agência no Keepers | 2.531 |
| Sem registro em agência no Keepers | 2.848 |
| Com duas ou mais agências | 599 |
| OJS declarado no Miguilim | 1.919 |
| OJS confirmado tecnicamente sem declaração | 779 |
| OJS provável por instalação compartilhada | 850 |
| OJS provável por assinaturas técnicas | 24 |
| Revistas com versão OJS identificada | 2.880 |

### Preservação entre as revistas identificadas como OJS

Considerando as categorias OJS declarado, confirmado tecnicamente e provável, **2.050 das 3.572 revistas estão preservadas**, o equivalente a **57,4%**.

| Classificação OJS | Total | Preservadas | % preservadas | Com 2+ agências |
|---|---:|---:|---:|---:|
| OJS declarado no Miguilim | 1.919 | 1.161 | 60,5% | 305 |
| OJS confirmado tecnicamente | 779 | 335 | 43,0% | 75 |
| OJS provável por instalação compartilhada | 850 | 551 | 64,8% | 118 |
| OJS provável por assinaturas técnicas | 24 | 3 | 12,5% | 1 |
| **Total identificado como OJS** | **3.572** | **2.050** | **57,4%** | **499** |
| **Critério estrito: declarado + confirmado** | **2.698** | **1.496** | **55,4%** | — |

Entre as 2.050 revistas identificadas como OJS e preservadas, 1.551 aparecem em uma agência e 499 em duas ou mais agências.

Esses números funcionam como controle de reprodução exata. Uma coleta feita em outra data pode produzir valores diferentes porque os registros do Miguilim, do Keepers Registry e os sites das revistas são dinâmicos.

## 3. Fontes e snapshots

| Fonte | Uso | Snapshot ou endereço |
|---|---|---|
| Miguilim | Universo de revistas e metadados editoriais | `data/miguilim_revistas_2026-10-29.csv`<br><https://miguilim.ibict.br/simple-search> |
| Keepers Registry | *Archival Status* e agências de preservação | `data/keepers_brazil_agencies_2026-10-29.csv`<br><https://keepers.issn.org/advancedsearch> |
| Sites das revistas | Assinaturas públicas de OJS, versão e erros de acesso | Caches JSON em `data/ojs_detection_cache` e `data/ojs_undeclared_scan_cache` |

O CSV do Miguilim é o snapshot inicial desta reprodução. O repositório atual não contém um coletor que gere esse arquivo a partir do portal. Para repetir exatamente o levantamento, deve-se usar o arquivo com o hash informado no apêndice. Para atualizar o estudo, deve-se exportar novamente a coleção **Revistas científicas**, preservando os mesmos campos, e registrar a nova data de referência.

## 4. Ambiente de execução

| Componente | Versão usada | Finalidade |
|---|---|---|
| Python | 3.12.14 | Coleta, cache, classificação e consolidação |
| Node.js | 24.19.0 | Geração da planilha final |
| Biblioteca de planilhas | `@oai/artifact-tool` 2.8.58 ou superior | Exportação XLSX e verificação |
| Sistema de arquivos | UTF-8 | Leitura e escrita dos CSV e JSON |

Os coletores usam apenas módulos da biblioteca padrão do Python. A reprodução da planilha exige a dependência Node indicada. Os comandos devem ser executados na raiz do projeto.

## 5. Estrutura dos arquivos

| Caminho | Papel no fluxo |
|---|---|
| `data/miguilim_revistas_2026-10-29.csv` | Entrada principal com 5.379 revistas |
| `data/keepers_cache` | Páginas do Keepers mantidas para evitar novas consultas |
| `data/ojs_detection_cache` | Uma resposta por instalação OJS declarada |
| `data/ojs_undeclared_scan_cache` | Uma resposta por instalação sem declaração |
| `data/revistas_preservacao_detalhe_2026-10-29.json` | Tabela consolidada usada pela planilha |
| `data/revistas_preservacao_resumo_2026-10-29.json` | Totais e distribuições de controle |

## 6. Procedimento de reprodução

### 6.1. Preservação no Keepers Registry

O coletor consulta as facetas públicas por país e agência. Ele usa páginas de 100 registros, mantém cache local e respeita intervalo de 10,5 segundos, superior ao *crawl delay* de 10 segundos observado. As duas facetas do programa chinês são reunidas sob um único nome canônico.

```bash
python3 scripts/collect_keepers_brazil.py
```

As contagens esperadas das facetas estão registradas no script. Em uma atualização futura, essas contagens devem ser lidas novamente no portal e atualizadas antes da execução. Uma divergência encerra o processo para evitar a publicação de um resultado incompleto.

### 6.2. Versões das revistas que declaram OJS

O campo de software do Miguilim identifica 1.919 revistas que declaram Open Journal Systems ou OJS. Esses registros são agrupados em 560 instalações. Cada instalação recebe uma única consulta representativa.

```bash
python3 scripts/collect_ojs_versions.py
```

A versão é extraída principalmente do elemento `meta generator`. O coletor também registra a URL final, o código HTTP, a evidência textual e o erro de rede quando a resposta não é concluída.

### 6.3. Revalidação das falhas

As 73 instalações que falharam na primeira consulta são verificadas uma segunda vez. Essa etapa registra HTTP, DNS, timeout, certificado TLS, conexão recusada e outras categorias sem tentar repetidamente o mesmo site.

```bash
python3 scripts/revalidate_ojs_access_errors.py
```

### 6.4. Análise das revistas sem software declarado

Primeiro, a análise passiva associa revistas à mesma chave de instalação das revistas que declaram OJS. Depois, as instalações ainda não classificadas recebem uma consulta técnica controlada.

```bash
python3 scripts/analyze_undeclared_ojs.py
python3 scripts/scan_undeclared_ojs_sites.py
```

### 6.5. Consolidação e geração da planilha

```bash
python3 scripts/prepare_miguilim_preservation.py
node scripts/build_preservation_workbook.mjs
```

A primeira etapa cruza os ISSNs, propaga os resultados por instalação e produz os arquivos detalhado e resumo. A segunda gera a planilha com as abas **Resumo** e **Revistas**, aplica os formatos e executa verificações de conteúdo e erros de fórmula antes da exportação.

## 7. Chaves de correspondência

### 7.1. Preservação

O cruzamento com o Keepers Registry usa o ISSN do campo `dc.identifier.issn` do Miguilim em letras maiúsculas. Uma revista é marcada como preservada quando esse ISSN aparece em pelo menos uma agência. A quantidade corresponde ao número de agências distintas.

### 7.2. Instalação OJS

A chave de instalação combina o host em letras minúsculas com o prefixo do caminho anterior a `/index.php/`. Quando o marcador não existe, a chave usa somente o host. Essa regra reduz consultas, mas pode agrupar instalações diferentes que compartilham host e não expõem o marcador.

## 8. Regras de classificação de OJS

| Categoria | Critério | Interpretação |
|---|---|---|
| OJS declarado no Miguilim | Campo **Software utilizado** contém Open Journal Systems ou OJS | Declaração da fonte |
| OJS confirmado tecnicamente | `meta generator`, texto Open Journal Systems ou OJS acompanhado de versão | Evidência direta na página |
| OJS provável por instalação compartilhada | Mesma chave de instalação de revista com declaração explícita | Inferência de alta confiança |
| OJS provável por assinaturas técnicas | Ao menos duas assinaturas públicas, ou cookie `OJSSID` | Indício técnico sem declaração direta |
| OJS não identificado | Página respondeu sem evidência suficiente | Não confirma ausência de OJS |
| Consulta técnica não concluída | Erro HTTP, DNS, TLS, timeout ou conexão | Resultado indeterminado |
| Sem URL válida | URL ausente ou sem host | Análise técnica impossível |

A versão só é preenchida quando aparece em evidência pública ou quando a revista compartilha uma instalação cuja versão foi observada. Padrões de URL, aparência visual e nome do domínio não são usados isoladamente para afirmar uso ou versão de OJS.

## 9. Política de acesso responsável

| Etapa | Escopo | Concorrência | Timeout | Tentativas adicionais | Limite de resposta |
|---|---|---:|---:|---:|---:|
| Keepers | Páginas de faceta | Sequencial | 60 s | Até 3 | Página completa |
| OJS declarado | 560 instalações | 6 workers | 20 s | 0 | 2 MB |
| Revalidação | 73 instalações | 3 workers | 25 s | 0 | 64 KiB |
| OJS não declarado | 1.788 instalações em 1.755 hosts | 3 hosts | 20 s | 0 | 1 MB |

- Todos os coletores gravam cache e reutilizam respostas existentes.
- Instalações do mesmo host são processadas sequencialmente, com intervalo de 1,5 segundo na varredura sem declaração.
- Os coletores OJS não fazem tentativas adicionais automáticas.
- O User-Agent usado foi `Mozilla/5.0 preservation-research/1.0`.

## 10. Controles de qualidade

1. Confirmar que o snapshot do Miguilim contém 5.379 linhas de dados.
2. Verificar que 4.969 registros são vigentes e 410 são descontinuados.
3. Reconciliar 2.531 revistas com Keepers e 2.848 sem Keepers.
4. Reconciliar todas as categorias OJS em 5.379 revistas sem duplicação.
5. Confirmar 2.880 revistas com versão OJS preenchida.
6. Examinar códigos HTTP e erros de rede sem convertê-los em ausência de OJS.
7. Inspecionar a planilha exportada e procurar erros de fórmula como `REF`, `DIV 0`, `VALUE` e `NAME`.
8. Renderizar as abas alteradas para verificar legibilidade, cabeçalhos e colunas.

## 11. Limitações

- O snapshot do Miguilim depende de uma exportação externa ao pipeline atual.
- O *Archival Status* pode mudar depois da data de referência.
- Sites inacessíveis permanecem indeterminados, inclusive quando o erro é temporário.
- Algumas instalações não expõem a versão no `meta generator`.
- A correlação por host pode agrupar portais diferentes quando a URL não contém `/index.php/`.
- A classificação OJS provável não deve ser apresentada como declaração formal da revista.
- As versões 3.4.6.2 e 3.3.9.9 foram mantidas porque apareceram no `meta generator` dos sites; não foram normalizadas para uma versão oficial presumida.

## 12. Atualização do levantamento

Uma atualização deve ser publicada em uma nova pasta de data, sem sobrescrever os snapshots anteriores. Antes da coleta, registre a data, atualize as contagens das facetas do Keepers e mantenha os caches antigos como evidência. Depois da execução, compare os totais com a edição anterior e investigue variações abruptas antes de divulgar o novo arquivo.

1. Exportar um novo snapshot do Miguilim com o mesmo esquema de campos.
2. Atualizar nomes de arquivos e datas constantes nos scripts.
3. Revisar as facetas e contagens esperadas do Keepers.
4. Executar os scripts na ordem apresentada na seção 6.
5. Gerar novos hashes SHA-256 e anexá-los à documentação da nova edição.

## Apêndice A — Comandos em ordem

```bash
python3 scripts/collect_keepers_brazil.py
python3 scripts/collect_ojs_versions.py
python3 scripts/revalidate_ojs_access_errors.py
python3 scripts/analyze_undeclared_ojs.py
python3 scripts/scan_undeclared_ojs_sites.py
python3 scripts/prepare_miguilim_preservation.py
node scripts/build_preservation_workbook.mjs
```

## Apêndice B — Arquivos finais

- `outputs/miguilim-preservacao-2026-10-29/preservacao_revistas_brasileiras_2026-10-29.xlsx`
- `data/revistas_preservacao_detalhe_2026-10-29.csv`
- `data/ojs_access_revalidation_2026-10-29.csv`
- `data/ojs_undeclared_active_scan_2026-10-29.csv`

## Apêndice C — Hashes SHA-256

| Arquivo | SHA-256 |
|---|---|
| `data/miguilim_revistas_2026-10-29.csv` | `c37234cf0687531ca4164ed0845e1a1d428ee89ebc6fa72bafb66919dfd7a5da` |
| `data/keepers_brazil_agencies_2026-10-29.csv` | `451655469147c7b42fa910b11db4edb816fbc24e8eb1f6eecacd4f0e161d80e9` |
| `data/ojs_instance_detection_2026-10-29.json` | `47280469a3dccc49a0dc53de1dd33b9611b160f661b7607e1300856ff194c9a4` |
| `data/ojs_access_revalidation_2026-10-29.json` | `917dc0c0431c4a843c73fb04874794ce5ae67ffe3a81d09c19c2f0cd56c0de4c` |
| `data/ojs_undeclared_active_scan_2026-10-29.json` | `8463ad794df87ab03db5d6c85f75bbb5e602f2ac613eba6dc99f7cf3936dc905` |
| `data/revistas_preservacao_resumo_2026-10-29.json` | `77b4a67f1cedea3a17fe920391b8c78792da0b4f2e6535f92483bbb5cba0ef12` |
| `scripts/collect_keepers_brazil.py` | `ee727fb146f2813b13ae31d8efa7486890305ebf0b7ce8104416d4f8e94ef56b` |
| `scripts/collect_ojs_versions.py` | `f298d5bb06bc49e7ef8790fcf651c6301ee791583e4d8469d2006702a9a040f9` |
| `scripts/revalidate_ojs_access_errors.py` | `c2ce15a6d151e2b358f79cf172b5a9f7c2362ee1b1f9d5b1e3ceec4161fdd60d` |
| `scripts/analyze_undeclared_ojs.py` | `e3c4a559096bd5c102bb8bcd647238a04c8b7958b0f38987433850b532905fe8` |
| `scripts/scan_undeclared_ojs_sites.py` | `f744e3a8e48cb979ceff008f09efe921a91d4f0e1693edf5f447daf163b21836` |
| `scripts/prepare_miguilim_preservation.py` | `394ce318114f897491fbfaa37e510cd119795bfb4303282ee57d61e52f5aa13f` |
| `scripts/build_preservation_workbook.mjs` | `39627b24a677d70ea5e1853910d2cafff491800a6fa03f108e60903e88053e45` |
