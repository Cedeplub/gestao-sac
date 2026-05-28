# Gestão SAC — Contexto do Projeto

## Stack

- **Backend**: FastAPI + SQLAlchemy 2.x + Oracle (oracledb thick mode)
- **Frontend**: Jinja2 + Tailwind (CDN Play) + HTMX 2.0 + Alpine.js 3.x (defer)
- **Auth**: JWT via python-jose + passlib bcrypt; sessão web via cookie `gsac_session`
- **Banco leitura**: `read_engine` → schema CEDEP (Oracle) — somente leitura de notas fiscais
- **Banco escrita**: `write_engine` → schema `gestao_sac` (Oracle)

## Estrutura de diretórios

```
app-sac-gestao/
  backend/                          ← raiz do servidor FastAPI (uvicorn)
    app/
      main.py                       # monta routers web (raiz) + lifespan + seed admin
      core/
        database.py                 # read_engine + write_engine + get_write_db
        security.py                 # JWT encode/decode
        config.py                   # Settings (lê .env)
        permissions.py
      models/
        ocorrencia.py               # Ocorrencia (tabela principal)
        ocorrencia_item.py          # OcorrenciaItem
        ocorrencia_evento.py        # OcorrenciaEvento (audit log)
        usuario.py                  # Usuario
        anexo.py                    # Anexo
      schemas/
        ocorrencia.py               # Pydantic schemas + requests de transição
        usuario.py
      services/
        ocorrencia_service.py       # CRUD + máquina de estados
        evento_service.py           # registra eventos no audit log
        carregamento_service.py     # consulta NF no CEDEP (read_engine)
        user_service.py
        anexo_service.py
      web/
        routes/
          ocorrencias.py            # rotas web HTML (GET/POST)
          usuarios.py               # rotas web HTML (GET/POST)
          dashboard.py
          auth.py
        dependencies.py             # get_current_web_user
        templates_config.py         # Jinja2Templates apontando para ../frontend/templates
        session.py
      utils/
        enums.py                    # todos os enums e dicts de labels PT-BR
    sql/                            # migrations numeradas — executar como gestao_sac_dev
      00_instalacao_completa.sql    # instalação do zero (snapshot atualizado)
      10_reabrir_finalizado.sql     # adiciona evento REABERTA ao CHECK
      11_remover_colunas_obsoletas.sql  # drop de colunas descontinuadas
      12_motivo_razao_social.sql    # adiciona RAZAO_SOCIAL_DESACORDO ao CHECK de motivo
      13_tipo_ocorrencia_reposicao.sql  # adiciona REPOSICAO_CEDEP e REPOSICAO_BONIFICADA
      15_remover_status_encaminhado.sql # remove ENCAMINHADO do CHECK de status
      16_anexo_removido.sql         # adiciona ANEXO_REMOVIDO ao CHECK de tipo_evento

  frontend/                         ← templates e assets (separado do backend)
    templates/
      base/
        base.html                   # carrega HTMX 2.0, Alpine 3.x (defer), Tailwind CDN, Lucide
        authenticated.html          # layout sidebar + header com {% block header_actions %}
      pages/
        auth/login.html
        dashboard/home.html
        ocorrencias/
          list.html                 # listagem com KPIs e filtros avançados
          create.html               # criação (busca NF via HTMX + seleção de itens Alpine)
          view.html                 # visualização + timeline + modais de transição
          edit.html                 # edição (apenas EM_TRATAMENTO)
        usuarios/
          list.html
          create.html
          edit.html
      partials/
        badge_status.html           # badge colorido por status
        timeline_evento.html        # linha do tempo de eventos
        nota_info.html              # resultado HTMX ao buscar NF
    static/                         ← CSS e JS customizados (se houver)
```

## Modelos de banco (schema gestao_sac)

### Ocorrencia
Colunas: `id`, `numero_nota_fiscal`, `id_carregamento`, snapshot NF (`cliente`, `motorista`, `vendedor`, `transportadora`, `valor_total`, `data_faturamento`, `data_saida_carregamento`), `motivo`, `tipo_ocorrencia`, `causa_raiz`, `responsavel_tipo`, `observacoes`, `motivo_pendencia`, `resolucao_final`, `detalhes_especificos` (CLOB/JSON), `status`, `criado_por_id`, `atribuido_a_id`, `aprovado_por_id`, `aprovado_em`, `created_at`, `updated_at`.

> **Nomes Python = nomes de coluna no DB** (sem alias via `Column('nome_db', ...)`).

> **`detalhes_especificos`**: JSON livre para dados extras. Usado atualmente para `motivo_outro` (quando `motivo == 'OUTRO'`) e `causa_outro` (quando `causa_raiz == 'OUTRO'`). Exibidos na view.html abaixo do campo correspondente.

> **NF duplicada**: a criação bloqueia se já existir qualquer ocorrência com o mesmo `numero_nota_fiscal`. Erro `NF_DUPLICADA:{id}` levantado no service; web route redireciona para `/ocorrencias/nova?nf_dup_id={id}` com banner amarelo e link para a ocorrência existente.

## Enums (`app/utils/enums.py`)

| Enum | Valores |
|------|---------|
| `StatusOcorrenciaEnum` | EM_TRATAMENTO, PENDENTE, CONCLUIDO, FINALIZADO |
| `MotivoEnum` | AVARIA, INVERSAO_MERCADORIA, FALTA_MERCADORIA, SOBRA_MERCADORIA, DEVOLUCAO_SOLICITADA, PEDIDO_TROCA, EXTRAVIO, ATRASO_ENTREGA, PEDIDO_DUPLICADO, PEDIDO_DESACORDO, **RAZAO_SOCIAL_DESACORDO**, OUTRO |
| `TipoOcorrenciaEnum` | DEVOLUCAO_TOTAL, DEVOLUCAO_PARCIAL, REENVIO, REPOSICAO, **REPOSICAO_CEDEP**, **REPOSICAO_BONIFICADA** |
| `CausaRaizEnum` | ERRO_EXPEDICAO, ERRO_VENDEDOR, ERRO_TRANSPORTADORA, ERRO_MOTORISTA, DEFEITO_FABRICA, DESISTENCIA_CLIENTE, ERRO_CLIENTE, FORA_ROTA, OUTRO |
| `ResponsavelTipoEnum` | CEDEP, VENDEDOR, TRANSPORTADORA, MOTORISTA, CLIENTE, FABRICANTE, NAO_APLICAVEL |
| `TipoEventoEnum` | CRIADA, EDITADA, COMENTARIO, MUDANCA_STATUS, ANEXO_ADICIONADO, **ANEXO_REMOVIDO**, ITEM_ADICIONADO, APROVADA, REPROVADA, ATRIBUICAO_ALTERADA, **REABERTA** |
| `ItemRoleEnum` | AFETADO, ENVIADO_INCORRETAMENTE, ITEM_CORRETO |
| `RoleEnum` | OPERADOR, GERENTE |

Labels PT-BR: `STATUS_LABELS`, `TIPO_LABELS`, `MOTIVO_LABELS`, `CAUSA_LABELS`, `RESPONSAVEL_LABELS`.

> `STATUS_LABELS["CONCLUIDO"]` = `"Aguardando aprovação"` (não "Concluído")

## Fluxo de status

```
EM_TRATAMENTO → PENDENTE (marcar pendente) | CONCLUIDO (enviar p/ aprovação)
PENDENTE      → EM_TRATAMENTO (reabrir)   | CONCLUIDO
CONCLUIDO     → FINALIZADO (gerente aprovar) | EM_TRATAMENTO (gerente reprovar)
FINALIZADO    → EM_TRATAMENTO (gerente reabrir — motivo obrigatório, evento REABERTA)
```

## Rotas web principais

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/ocorrencias` | listagem com KPIs e filtros |
| GET | `/ocorrencias/nova` | formulário de criação |
| POST | `/ocorrencias` | salva nova ocorrência (bloqueia NF duplicada) |
| GET | `/ocorrencias/buscar-nota` | HTMX partial — busca NF no CEDEP |
| GET | `/ocorrencias/{id}` | visualização + timeline |
| GET | `/ocorrencias/{id}/editar` | edição |
| POST | `/ocorrencias/{id}/atualizar` | salva edição |
| POST | `/ocorrencias/{id}/pendente` | transição: marcar pendente |
| POST | `/ocorrencias/{id}/concluir` | transição: enviar p/ aprovação |
| POST | `/ocorrencias/{id}/aprovar` | transição: aprovar e finalizar (GERENTE) |
| POST | `/ocorrencias/{id}/reprovar` | transição: reprovar (GERENTE) |
| POST | `/ocorrencias/{id}/reabrir` | transição: reabrir FINALIZADO → EM_TRATAMENTO (GERENTE) |
| GET/POST | `/usuarios` | listagem e criação |
| GET/POST | `/usuarios/{id}/editar` | edição de usuário |

## Layout (authenticated.html)

O header fixo (`h-16`) tem `{% block header_actions %}{% endblock %}` entre o título da página e o avatar/logout. **Todas as páginas** usam esse bloco para injetar botões ou links de volta — nenhuma página tem sub-header próprio dentro de `page_content`.

- `list.html` → "Nova Ocorrência" no header_actions
- `create.html` / `edit.html` / `view.html` → link "Voltar" no header_actions
- `view.html` também coloca o badge de status no header_actions; os botões de transição ficam no `page_content` (precisam do escopo Alpine `x-data`)

## Página /ocorrencias/nova (create.html)

1. Usuário digita NF e clica Buscar
2. HTMX faz `GET /ocorrencias/buscar-nota` e injeta `partials/nota_info.html` em `#nota-info`
3. `nota_info.html` renderiza um `<script id="nota-produtos-json" type="application/json">` com array de produtos + caixa verde com dados da nota
4. `htmx:afterSwap` handler lê o JSON e injeta no estado Alpine via `Alpine.$data(root)`
5. Usuário seleciona itens; o mapa `selecionadosMap` é serializado em `itens_json` (hidden input) em três pontos: `:value` reativo, `@submit`, e `enviarAprovacao()` antes do `.submit()`
6. Backend recebe `itens_json: str = Form("[]")` e faz parse
7. Se a NF já tiver ocorrência cadastrada, exibe banner amber com link para a ocorrência existente (sem permitir criação)

## Convenções obrigatórias

- **Sempre criar migration SQL** em `backend/sql/` (arquivo numerado sequencialmente) junto com qualquer alteração que afete o banco: constraints, colunas, tabelas, valores de CHECK, índices, etc.
- Migrations são executadas **manualmente** como usuário `gestao_sac_dev` no Oracle (`192.168.0.98/WINT`)
- Alterações puramente de Python ou templates não precisam de migration
