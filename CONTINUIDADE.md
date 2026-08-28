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
* **Controle de Acesso:** Bot privado com painel e aprovação interativa pelo Administrador (ID: `5599506814`).

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
ADMIN_ID=5599506814
TURSO_DATABASE_URL=libsql://seu-banco-turso.io
TURSO_AUTH_TOKEN=seu_token_gerado_no_turso
CHECK_INTERVAL_HOURS=3
PORT=8080
```

---

## 5. Próximos Passos Sugeridos

1. Fazer commit e push das melhorias arquiteturais para o GitHub/Heroku:
   ```bash
   git add .
   git commit -m "refactor: adota Clean Architecture com camadas desacopladas e Repository Pattern"
   git push origin main
   ```
2. Testar comandos no Telegram com sua conta de Admin.
3. Avaliar próximas melhorias de produto (auto-resolver de cidades para IATA, botões inline de exclusão direta na lista, etc.).
