# ✈️ Contexto do Projeto e Guia de Continuidade

> **Para o assistente de IA:** Este documento contém o histórico completo de desenvolvimento, arquitetura, configurações ativas, padrões adotados e pendências do projeto.
> **Regra do Usuário:** Quando o usuário disser *"atualize o continuidade"*, atualize este arquivo com todas as mudanças recentes e o estado atual do projeto para que qualquer nova sessão em qualquer máquina leia e entenda imediatamente o contexto.

---

## 1. Visão Geral do Projeto
* **Nome:** Bot de Alerta de Passagens Telegram + Google Flights.
* **Linguagem:** Python 3.10+ (Tipagem estática, Dataclasses, Clean Architecture).
* **Hospedagem:** Heroku / Render / VPS (rodando como `worker` via `Procfile`).
* **Banco de Dados:** **Turso Cloud (libSQL / SQLite em nuvem)** com fallback automático para SQLite local (`alertas.db`).
* **Consulta de Preços:** `fast-flights` (Google Flights scraping em BRL sem custos de API, suporte nacional e internacional).
* **Controle de Acesso:** Bot privado com painel e aprovação interativa pelo Administrador (ID configurado via `ADMIN_ID`).

---

## 2. Arquitetura Modular Profissional (`src/`)

O projeto foi totalmente refatorado para eliminar scripts monolíticos e adotar padrões de engenharia de software (Clean Architecture, SOLID, Repository Pattern, Context Managers):

```text
alerta-voos-telegram/
├── src/
│   ├── config.py                 # Configurações tipadas (Config dataclass) e carregamento de .env
│   ├── models/                   # Entidades de Domínio (Dataclasses)
│   │   ├── alerta.py             # Modelo Alerta
│   │   ├── usuario.py            # Modelo Usuario
│   │   └── voo.py                # Modelo Voo (preço, companhia, escalas)
│   ├── database/                 # Camada de Persistência (Repository Pattern)
│   │   ├── connection.py         # DatabaseManager com context manager (with) para Turso / SQLite
│   │   ├── schema.py             # Inicialização de tabelas e registro do Admin
│   │   ├── alerta_repository.py  # Operações SQL de Alertas
│   │   └── usuario_repository.py # Operações SQL de Usuários e Permissões
│   ├── services/                 # Regras de Negócio e Serviços Externos
│   │   ├── flight_service.py     # Scraping isolado via fast-flights e gerador de links
│   │   └── notifier_service.py   # Formatação de mensagens Markdown para o Telegram
│   └── bot/                      # Interface Telegram Desacoplada
│       ├── middlewares.py        # Decorators (@requer_autorizacao, @requer_admin)
│       ├── server.py             # Servidor HTTP de Health Check (Thread gerenciada)
│       ├── scheduler.py          # AlertScheduler (Loop periódico assíncrono em background)
│       ├── app.py                # Montagem da Application do Telegram e injeção de dependências
│       └── handlers/
│           ├── user_handlers.py  # /start, /ajuda, /alerta, /listar, /remover, /testar
│           ├── admin_handlers.py # /usuarios, /aprovar, /bloquear
│           └── callbacks.py      # Botões inline [✅ Aprovar] e [❌ Recusar]
├── main.py                       # Ponto de entrada oficial da aplicação
├── bot.py                        # Wrapper retrocompatível (delega para main.py)
├── .env.example                  # Molde de variáveis de ambiente sem segredos
├── .python-version               # Versão do runtime Python fixada para o Heroku (3.12)
├── Procfile                      # Execução no Heroku (worker: python bot.py)
├── iniciar.sh                    # Script bash para rodar localmente
├── requirements.txt              # Dependências do projeto (python-telegram-bot, fast-flights, libsql, typing_extensions)
├── README.md                     # Documentação completa
└── CONTINUIDADE.md               # Este arquivo de contexto contínuo
```

---

## 3. Histórico de Mudanças e Decisões Técnicas

1. **Segurança do Token:** Removido qualquer token fixo do código. O token é carregado exclusivamente de variáveis de ambiente ou `.env`.
2. **Banco Turso Cloud com Fallback:** Suporte a `libsql://` com token de autenticação, evitando perda de dados no filesystem efêmero do Heroku/Render, mantendo SQLite local como fallback de desenvolvimento.
3. **Controle de Acesso Privado com Botões Inline:**
   - Usuário não cadastrado envia `/start`: acesso bloqueado, mensagem amigável enviada ao usuário e notificação interativa com botões `[✅ Aprovar]` e `[❌ Recusar]` enviada ao Admin.
   - Admin clica no botão: usuário é autorizado e notificado imediatamente no Telegram.
4. **Comandos de Admin:** `/usuarios` (painel geral), `/aprovar <ID>`, `/bloquear <ID>`.
5. **Checagem em Background Otimizada:** O agendador consulta apenas alertas pertencentes a usuários com acesso ativo.
6. **Refatoração para Clean Architecture:** Código modularizado em `src/`, com repositórios, serviços desacoplados e decorators para controle de acesso.

---

## 4. Variáveis de Ambiente Necessárias

Configurar no painel do Heroku (`Config Vars`) ou no `.env` local:

```env
TELEGRAM_TOKEN=seu_token_gerado_no_botfather
ADMIN_ID=123456789
TURSO_DATABASE_URL=libsql://seu-banco-turso.io
TURSO_AUTH_TOKEN=seu_token_gerado_no_turso
CHECK_INTERVAL_HOURS=3
PORT=8080
```

---

## 5. Roadmap de Sprints no GitHub (Issues e Milestones)

* **🏃‍♂️ Sprint 1: UX Interativa, Dicionário IATA & Datas BR (Milestone 1) - [CONCLUÍDA E MERGEADA NA MAIN]**
  - [#1](https://github.com/Italo61-dev/alerta-voos-telegram/issues/1): `feat(ux)` Ações rápidas com 1 clique nas listagens e notificações (implementado).
  - [#2](https://github.com/Italo61-dev/alerta-voos-telegram/issues/2): `feat(iata)` Dicionário inteligente de cidades para códigos IATA (implementado via `AirportService`).
  - [#3](https://github.com/Italo61-dev/alerta-voos-telegram/issues/3): `feat(ux)` Wizard conversacional guiado para criação de alerta (`/novo` implementado via `ConversationHandler`).
  - `feat(ux)` Suporte nativo ao formato de data brasileiro (`DD/MM/AAAA` e `DD/MM`) via `DateService`.

* **🤖 Sprint 2: IA com Google Gemini (Milestone 2) - [CONCLUÍDA NA BRANCH]**
  - [#4](https://github.com/Italo61-dev/alerta-voos-telegram/issues/4): `feat(ai)` Criação de alertas por linguagem natural (texto livre com confirmação).
  - [#5](https://github.com/Italo61-dev/alerta-voos-telegram/issues/5): `feat(ai)` Transcrição e extração de alertas a partir de áudios do Telegram.
  - [#6](https://github.com/Italo61-dev/alerta-voos-telegram/issues/6): `feat(ai)` Consultor de viagens inteligente para dicas de turismo e épocas baratas.
  - [#13](https://github.com/Italo61-dev/alerta-voos-telegram/issues/13): `feat(ai)` Rate limit amigável e aviso de retorno quando atingir limite da IA (reset timer).
  - [#14](https://github.com/Italo61-dev/alerta-voos-telegram/issues/14): `feat(flights)` Pesquisa instantânea de voos com top 3 opções via IA.
  - `feat(ai)` Memória conversacional contínua multi-turno (acumula dados entre mensagens sem esquecer).
  - `feat(ai)` Priorização de criação de alerta quando há teto estipulado, com prévia do menor preço e top 3 ofertas ao vivo antes da confirmação.

* **📈 Sprint 3: Inteligência de Preços & Histórico (Milestone 3) - [PRÓXIMA SPRINT]**
  - [#7](https://github.com/Italo61-dev/alerta-voos-telegram/issues/7): `feat(data)` Histórico de preços por trecho persistido no banco.
  - [#8](https://github.com/Italo61-dev/alerta-voos-telegram/issues/8): `feat(intelligence)` Termômetro de oportunidade (badges de super promoção).
  - [#9](https://github.com/Italo61-dev/alerta-voos-telegram/issues/9): `feat(flights)` Filtro de voos diretos vs voos com conexão.

* **👑 Sprint 4: Painel Admin & Transmissão Global (Milestone 4)**
  - [#10](https://github.com/Italo61-dev/alerta-voos-telegram/issues/10): `feat(admin)` Comando /broadcast para envio de promoções globais aos usuários.
  - [#11](https://github.com/Italo61-dev/alerta-voos-telegram/issues/11): `feat(admin)` Painel de estatísticas e métricas do bot (/stats).
  - [#12](https://github.com/Italo61-dev/alerta-voos-telegram/issues/12): `feat(fair-use)` Limite de alertas simultâneos por perfil de usuário.

---

## 6. Próxima Etapa de Desenvolvimento
* Fazer merge da branch `feature/sprint-2-gemini-ai` para `main` (disparando o deploy no Heroku).
* Iniciar a **Sprint 3 (Inteligência de Preços & Histórico)**: branch `feature/sprint-3-price-intelligence`.
