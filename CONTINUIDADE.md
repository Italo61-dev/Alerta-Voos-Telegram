# ✈️ Contexto do Projeto e Guia de Continuidade

> **Para o assistente de IA:** Este documento contém o histórico completo de desenvolvimento, arquitetura, configurações ativas, padrões adotados e pendências do projeto.
> **Regra do Usuário:** Quando o usuário disser *"atualize o continuidade"*, atualize este arquivo com todas as mudanças recentes e o estado atual do projeto para que qualquer nova sessão em qualquer máquina leia e entenda imediatamente o contexto.

---

## 1. Visão Geral do Projeto
* **Nome:** Bot de Alerta de Passagens Telegram + Google Flights com IA (Agente Autônomo).
* **Linguagem:** Python 3.12 (Tipagem estática, Dataclasses, Clean Architecture).
* **Hospedagem:** Heroku / Render / VPS (rodando como `worker` via `Procfile` 24/7).
* **Banco de Dados:** **Turso Cloud (libSQL / SQLite em nuvem)** com fallback automático para SQLite local (`alertas.db`).
* **Consulta de Preços:** `fast-flights` (Google Flights scraping em BRL sem custos de API, suporte nacional e internacional).
* **Cérebro de IA:** **Google Gemini** (`gemini-3.5-flash-lite` nativo, com fallback de resiliência para `gemini-3.7-flash` e `gemini-3.6-flash`), utilizando **Function Calling Nativo (Caminho A)** para execução de ferramentas reais no banco e no Google Flights.
* **Controle de Acesso:** Bot privado com moderação e aprovação interativa pelo Administrador (ID configurado via `ADMIN_ID`).

---

## 2. Arquitetura Modular Profissional (`src/`)

O projeto adota padrões estritos de engenharia de software (Clean Architecture, SOLID, Repository Pattern, Context Managers, Function Calling):

```text
alerta-voos-telegram/
├── src/
│   ├── config.py                 # Configurações tipadas (Config dataclass) e carregamento de .env
│   ├── models/                   # Entidades de Domínio (Dataclasses)
│   │   ├── alerta.py             # Modelo Alerta (com apenas_direto, datas, teto, ultimo_preco)
│   │   ├── usuario.py            # Modelo Usuario
│   │   ├── voo.py                # Modelo Voo (preço, companhia, escalas)
│   │   └── historico.py          # Modelo RegistroHistorico e EstatisticasTrecho
│   ├── database/                 # Camada de Persistência (Repository Pattern)
│   │   ├── connection.py         # DatabaseManager com context manager para Turso / SQLite
│   │   ├── schema.py             # Inicialização de tabelas, índices e migrações automáticas seguras
│   │   ├── alerta_repository.py  # Operações SQL de Alertas
│   │   ├── usuario_repository.py # Operações SQL de Usuários e Permissões
│   │   └── historico_repository.py # Operações SQL de Histórico de Cotações e Estatísticas
│   ├── services/                 # Regras de Negócio e Serviços Especializados
│   │   ├── airport_service.py    # Dicionário de cidades brasileiras/mundiais e resolução IATA
│   │   ├── date_service.py       # Conversões de datas em padrão brasileiro e fuso de Brasília
│   │   ├── flight_service.py     # Scraping via fast-flights e gerador de links com filtros (non-stop)
│   │   ├── notifier_service.py   # Formatação de cards e notificações ricas em Markdown
│   │   ├── opportunity_service.py# Termômetro de Oportunidades (Super Promoção, Preço Excelente, Na Meta)
│   │   ├── ai_service.py         # Camada legada de IA (preservada para fallback)
│   │   └── travel_agent.py       # Agente Conversacional Autônomo com Function Calling nativo Gemini
│   └── bot/                      # Interface Telegram Desacoplada
│       ├── middlewares.py        # Decorators (@requer_autorizacao, @requer_admin)
│       ├── server.py             # Servidor HTTP de Health Check
│       ├── scheduler.py          # AlertScheduler (Loop periódico em background com histórico e termômetro)
│       ├── app.py                # Montagem da Application do Telegram e injeção de dependências
│       └── handlers/
│           ├── user_handlers.py  # /start, /ajuda, /alerta, /listar, /remover, /testar
│           ├── admin_handlers.py # /usuarios, /aprovar, /bloquear
│           ├── wizard_handlers.py# /novo (Wizard passo a passo)
│           ├── ai_handlers.py    # Atendimento autônomo por texto e áudio via TravelAgent
│           └── callbacks.py      # Botões inline [✅ Aprovar], [🔄 Checar Agora], [🗑️ Excluir]
├── main.py                       # Ponto de entrada oficial da aplicação
├── bot.py                        # Wrapper retrocompatível (delega para main.py)
├── .env.example                  # Molde de variáveis de ambiente
├── .python-version               # Versão do runtime Python fixada para o Heroku (3.12)
├── Procfile                      # Execução no Heroku (worker: python bot.py)
├── requirements.txt              # Dependências do projeto
├── README.md                     # Documentação completa
└── CONTINUIDADE.md               # Este arquivo de contexto contínuo
```

---

## 3. Histórico de Decisões e Conquistas Técnicas

1. **Segurança do Token:** Removido qualquer token fixo do código. O token é carregado exclusivamente de variáveis de ambiente ou `.env`.
2. **Banco Turso Cloud com Fallback:** Suporte a `libsql://` com token de autenticação, evitando perda de dados no filesystem efêmero do Heroku/Render, mantendo SQLite local como fallback de desenvolvimento.
3. **Controle de Acesso Privado com Botões Inline:**
   - Usuário não cadastrado envia `/start`: acesso bloqueado, mensagem amigável enviada ao usuário e notificação interativa com botões `[✅ Aprovar]` e `[❌ Recusar]` enviada ao Admin.
   - Admin clica no botão: usuário é autorizado e notificado imediatamente no Telegram.
4. **Agente Autônomo com Function Calling Nativo (Caminho A):**
   - Eliminados todos os `if/else` engessados de extração de JSON.
   - O `TravelAgent` possui 5 ferramentas Python reais executadas pelo Gemini:
     1. `buscar_voos_tempo_real(origem, destino, data_ida, data_volta, apenas_direto)`
     2. `cadastrar_alerta_preco(origem, destino, data_ida, teto, data_volta, apenas_direto)`
     3. `consultar_historico_precos(origem, destino, data_ida, preco_atual)`
     4. `listar_alertas_cadastrados()`
     5. `desativar_alerta(alerta_id)`
   - Mantém memória de conversa em turnos naturais (`client.chats.create`) e processa tanto **texto** quanto **áudios de voz** do Telegram.
5. **Histórico de Preços no Banco (`historico_precos`):**
   - Todas as cotações feitas pelo scheduler em background e pelos cliques manuais `[🔄 Checar Agora]` são salvas na tabela `historico_precos`.
   - Permite calcular o Menor Preço Já Visto e o Preço Médio Histórico de cada trecho.
6. **Termômetro de Oportunidades (`OpportunityService`):**
   - Classifica os voos em tempo real:
     - 🔥 **SUPER PROMOÇÃO**: Mais de 30% abaixo da média histórica.
     - 🟢 **PREÇO EXCELENTE**: 15% a 30% abaixo da média histórica.
     - 🟡 **NA META**: Preço atingiu ou ficou abaixo do teto solicitado.
     - ⏳ **ACIMA DA META**: Preço atual acima do orçamento.
7. **Filtro de Voos Diretos (`apenas_direto`):**
   - Campo `apenas_direto` na tabela `alertas`.
   - Se ativado, o buscador filtra apenas voos com 0 escalas e adiciona o termo `non-stop` no link do Google Flights.

---

## 4. Variáveis de Ambiente Necessárias

Configurar no painel do Heroku (`Config Vars`) ou no `.env` local:

```env
TELEGRAM_TOKEN=seu_token_gerado_no_botfather
ADMIN_ID=5599506814
GEMINI_API_KEY=sua_chave_do_google_ai_studio
TURSO_DATABASE_URL=libsql://seu-banco-turso.io
TURSO_AUTH_TOKEN=seu_token_gerado_no_turso
CHECK_INTERVAL_HOURS=1
PORT=8080
```

---

## 5. Roadmap de Sprints no GitHub (Status Atual)

* **🏃‍♂️ Sprint 1: UX Interativa, Dicionário IATA & Datas BR (Milestone 1) - [100% CONCLUÍDA]**
  - [#1](https://github.com/Italo61-dev/alerta-voos-telegram/issues/1): `feat(ux)` Ações rápidas com 1 clique nas listagens e notificações.
  - [#2](https://github.com/Italo61-dev/alerta-voos-telegram/issues/2): `feat(iata)` Dicionário inteligente de cidades para códigos IATA (`AirportService`).
  - [#3](https://github.com/Italo61-dev/alerta-voos-telegram/issues/3): `feat(ux)` Wizard conversacional guiado para criação de alerta (`/novo`).
  - `feat(ux)` Suporte a datas brasileiras (`DD/MM/AAAA`) e timezone oficial de Brasília (`America/Sao_Paulo`).

* **🤖 Sprint 2: IA com Google Gemini & Agente com Function Calling (Milestone 2) - [100% CONCLUÍDA]**
  - [#4](https://github.com/Italo61-dev/alerta-voos-telegram/issues/4): `feat(ai)` Criação de alertas por linguagem natural.
  - [#5](https://github.com/Italo61-dev/alerta-voos-telegram/issues/5): `feat(ai)` Transcrição e extração de alertas a partir de áudios de voz do Telegram.
  - [#6](https://github.com/Italo61-dev/alerta-voos-telegram/issues/6): `feat(ai)` Consultor de viagens inteligente para dicas de turismo e épocas baratas.
  - [#13](https://github.com/Italo61-dev/alerta-voos-telegram/issues/13): `feat(ai)` Rate limit amigável e aviso de retorno quando atingir limite da IA.
  - [#14](https://github.com/Italo61-dev/alerta-voos-telegram/issues/14): `feat(flights)` Pesquisa instantânea de voos com top 3 opções via IA.
  - `feat(ai)` **Caminho A Implementado**: Agente Autônomo com Function Calling do Google Gemini (`TravelAgent`), executando buscas e salvamento no banco diretamente.

* **📈 Sprint 3: Inteligência de Preços & Histórico (Milestone 3) - [100% CONCLUÍDA]**
  - [#7](https://github.com/Italo61-dev/alerta-voos-telegram/issues/7): `feat(data)` Histórico de preços por trecho persistido no banco (`historico_precos`).
  - [#8](https://github.com/Italo61-dev/alerta-voos-telegram/issues/8): `feat(intelligence)` Termômetro de oportunidade (badges 🔥 Super Promoção, 🟢 Preço Excelente, 🟡 Na Meta).
  - [#9](https://github.com/Italo61-dev/alerta-voos-telegram/issues/9): `feat(flights)` Filtro de voos diretos vs voos com conexão (`apenas_direto`).

* **👑 Sprint 4: Painel Admin & Transmissão Global (Milestone 4) - [EM ANDAMENTO 🚀]**
  - [#10](https://github.com/Italo61-dev/alerta-voos-telegram/issues/10): `feat(admin)` Comando /broadcast para envio de promoções globais e novidades automáticas aos usuários [CONCLUÍDA ✅].
  - [#11](https://github.com/Italo61-dev/alerta-voos-telegram/issues/11): `feat(admin)` Painel de estatísticas e métricas do bot (/stats) e Central `/admin` com botões interativos [CONCLUÍDA ✅].
  - [#12](https://github.com/Italo61-dev/alerta-voos-telegram/issues/12): `feat(fair-use)` Limite de alertas simultâneos por perfil de usuário [PRÓXIMA TASK].

---

## 6. Próxima Etapa de Desenvolvimento
1. Criar a branch `feature/issue-12-fair-use-limits`.
2. Implementar a **[Issue #12](https://github.com/Italo61-dev/alerta-voos-telegram/issues/12)**:
   - Limite configurável de alertas ativos simultâneos por usuário (ex: padrão de 5 alertas para usuários comuns, ilimitado para o Administrador).
   - Bloqueio amigável no `/alerta`, no wizard `/novo` e no `TravelAgent` quando o limite for atingido, orientando a remover alertas antigos com `/listar`.
