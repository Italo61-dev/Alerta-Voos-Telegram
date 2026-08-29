# ✈️ Bot de Alerta de Passagens Baratas (Telegram + Google Flights + IA)

[![CI/CD Quality & Security Gate](https://github.com/Italo61-dev/Alerta-Voos-Telegram/actions/workflows/ci.yml/badge.svg)](https://github.com/Italo61-dev/Alerta-Voos-Telegram/actions/workflows/ci.yml)
![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue?logo=python)
![Security: Bandit](https://img.shields.io/badge/security-bandit-brightgreen?logo=shield)
![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-black)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

Bot autônomo do Telegram desenvolvido em Python que monitora preços de passagens aéreas diretamente pelo **Google Flights** e notifica automaticamente quando o valor atinge a meta do viajante. Conta com **Agente Autônomo (Google Gemini)** para interação por texto e voz, histórico de inteligência de preços e painel administrativo completo.

---

## 🚀 Funcionalidades Principais

* **Scraping Real-Time (Google Flights):** Sem custos de APIs corporativas caras, buscando preços reais em Reais (BRL) para trechos nacionais e internacionais.
* **Agente de Viagens com IA (`Google Gemini`):**
  * Compreensão em linguagem natural para pesquisas e cadastro de alertas.
  * Transcrição desacoplada ultra-rápida de **mensagens de voz/áudio** do Telegram.
  * *Function Calling Nativo:* O modelo executa ferramentas reais de busca e persistência no banco.
* **Inteligência de Mercado & Histórico de Preços:**
  * Armazena cotações em segundo plano para calcular o **Menor Preço Já Visto** e a **Média Histórica**.
  * **Termômetro de Oportunidades:** Classifica ofertas como 🔥 *Super Promoção* (30% abaixo da média), 🟢 *Preço Excelente* (15% a 30% abaixo) ou 🟡 *Na Meta*.
* **Filtro de Voos Diretos:** Suporte a filtros de voos sem conexões (`non-stop`).
* **Banco de Dados em Nuvem (Turso Cloud / libSQL):** Persistência segura em nuvem que sobrevive a reinicializações em servidores efêmeros (Heroku/Render), com fallback automático para SQLite local.
* **Verificação em Background (Scheduler):** Varredura automática a cada 3 horas (configurável).
* **Controle de Acesso & Fair Use:**
  * Sistema de moderação onde novos usuários solicitam acesso e o Admin aprova com 1 clique.
  * Política de **Fair-Use configurável (padrão: 10 alertas ativos por usuário)**, evitando sobrecarga de scraping, com cota ilimitada para o Administrador.
* **Central de Controle do Administrador (`/admin`):**
  * Interface em botões inline para gestão sem poluir o chat de usuário.
  * Painel de métricas e estatísticas em tempo real (`/stats`).
  * Transmissão em massa para todos os usuários autorizados (`/broadcast` e `/broadcast_novidades`).

---

## 📋 Lista de Comandos

### 👤 Usuários Comuns:
* `/start` ou `/ajuda`: Mensagem de boas-vindas com instruções e menu interativo.
* `/novo`: Assistente conversacional guiado (passo a passo) para criar alertas sem precisar memorizar comandos.
* `/novidades`: Central de atualizações explicando os novos recursos do bot e exemplos de uso.
* `/alerta ORIGEM DESTINO TETO DATA_IDA [DATA_VOLTA]`: Criação rápida de alerta em linha única (aceita nomes de cidades ou códigos IATA).
* `/listar`: Exibe seus alertas ativos em cards visuais com botões de 1 clique:
  * `[ 🔄 Checar Agora ]`: Consulta o preço imediatamente no Google Flights.
  * `[ 🗑️ Excluir Alerta ]`: Desativa o monitoramento.
  * `[ 🔗 Ver no Google Flights ]`: Abre a rota no navegador já filtrada.
* `/remover ID`: Desativa um alerta específico pelo número de identificação.
* `/testar`: Força checagem imediata de todos os seus alertas cadastrados.
* **Conversa por Texto e Áudio com IA:** Envie mensagens como *"Quero ir de BSB para Salvador dia 15/11 pagando até 700"* ou mande um áudio no Telegram que o bot transcreve e atende o pedido!

### 👑 Administrador:
* `/admin`: Painel executivo interativo com botões para navegação rápida.
* `/stats`: Painel consolidado de métricas (total de usuários, alertas ativos, volume de cotações salvas e ranking dos trechos mais buscados).
* `/usuarios`: Lista de usuários cadastrados, status de autorização e IDs.
* `/aprovar ID`: Concede acesso a um usuário pendente.
* `/bloquear ID`: Revoga o acesso de um usuário.
* `/broadcast <mensagem>`: Transmite um comunicado customizado para todos os usuários autorizados.
* `/broadcast_novidades`: Dispara automaticamente o comunicado oficial com instruções de uso de novas funcionalidades.

---

## 📚 Manuais e Guias em PDF

O repositório inclui manuais ilustrados e formatados em PDF na pasta [`docs/`](docs/):

* **[📖 Guia Oficial de Comandos (User & Admin)](docs/Guia_Oficial_Comandos_Bot_Voos.pdf):** Manual de bolso com tabela detalhada de todos os comandos, exemplos de sintaxe, explicação das regras de fair-use e o termômetro de ofertas.
* **[🎓 Masterclass de Engenharia de IA, Áudio & Anti-Alucinação](docs/Masterclass_IA_Audio_Bots_Gemini.pdf):** Estudo de engenharia detalhando a arquitetura em duas camadas (transcrição desacoplada + agente cognitivo), como evitar o erro 400, mitigar alucinações com grounding e dominar os limites de cotas do Google Gemini.

---

## ⚙️ Variáveis de Ambiente

Configure as seguintes variáveis no arquivo `.env` local ou no painel do seu provedor (Heroku / Render / VPS):

| Variável | Obrigatória | Padrão | Descrição |
| :--- | :---: | :---: | :--- |
| `TELEGRAM_TOKEN` | **Sim** | - | Token de API gerado pelo [@BotFather](https://t.me/BotFather). |
| `ADMIN_ID` | **Sim** | - | Seu ID numérico no Telegram (obtido via [@userinfobot](https://t.me/userinfobot)). |
| `GEMINI_API_KEY` | Não | `None` | Chave de API do [Google AI Studio](https://aistudio.google.com/). |
| `TURSO_DATABASE_URL` | Não | `None` | URL do banco de dados Turso (ex: `libsql://meu-banco.turso.io`). |
| `TURSO_AUTH_TOKEN` | Não | `None` | Token de autenticação gerado no Turso CLI. |
| `CHECK_INTERVAL_HOURS`| Não | `3` | Intervalo em horas entre cada checagem automática. |
| `MAX_ALERTAS_POR_USUARIO` | Não | `10` | Quantidade máxima de alertas ativos por usuário comum. |
| `PORT` | Não | `8080` | Porta HTTP utilizada para o health check do servidor. |

> **Nota:** Se `TURSO_DATABASE_URL` não for informado, o bot utiliza automaticamente o SQLite local (`alertas.db`).

---

## 🛠️ Como Rodar Localmente

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/Italo61-dev/Alerta-Voos-Telegram.git
   cd Alerta-Voos-Telegram
   ```

2. **Crie e ative um ambiente virtual:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure as variáveis:**
   ```bash
   cp .env.example .env
   # Edite o .env com seu TELEGRAM_TOKEN e ADMIN_ID
   ```

5. **Execute a suíte de testes:**
   ```bash
   python3 -m unittest discover tests
   ```

6. **Inicie o bot:**
   ```bash
   python3 main.py
   ```

---

## ☁️ Deploy no Heroku

O projeto já inclui `Procfile` e `.python-version` configurados para rodar 24/7:

1. Defina as variáveis no painel do Heroku (`Settings > Config Vars`).
2. Garanta que o dyno de worker esteja ativado:
   ```bash
   heroku ps:scale worker=1 -a seu-app-telegram
   ```

---

## 🧪 Engenharia de Software, Qualidade & CI/CD

O repositório adota práticas rigorosas de engenharia de software e conta com um pipeline corporativo de **Integração Contínua (CI/CD)** via [GitHub Actions](.github/workflows/ci.yml), validando a estabilidade da aplicação a cada `push` ou `pull request`:

* **🎨 Linter & Code Standards (Ruff):** Auditoria estática ultra-rápida de sintaxe, formatação e conformidade com a PEP8.
* **🛡️ Segurança Estática (SAST com Bandit):** Varredura automática do código-fonte contra vulnerabilidades, vazamento de credenciais e injeção de comandos (aprovado com **0 vulnerabilidades**).
* **🧪 Testes em Matriz Multi-Versão:** Execução paralela da suíte completa de **18 testes automatizados** em **Python 3.11** e **Python 3.12**, garantindo compatibilidade entre diferentes versões do runtime.
* **📊 Cobertura de Código (Coverage.py):** Medição contínua da cobertura dos testes unitários sobre os módulos de banco, serviços de voos e regras de negócio.
* **🔒 Princípio de Menor Privilégio (Least Privilege):** Token de execução das Actions limitado estritamente a leitura (`contents: read`).
* **⚡ Concurrency Control & Caching:** Cancelamento automático de builds obsoletos na mesma branch e cache de dependências `pip` para execuções em menos de 30 segundos.

---

## 📄 Licença
Distribuído sob a licença MIT. Consulte `LICENSE` para mais detalhes.
