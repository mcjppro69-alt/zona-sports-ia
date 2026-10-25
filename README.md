# Zona Sports AI

Bot Discord em Python para consultar agenda de futebol europeu e NBA e publicar uma agenda diária.

## Incluído nesta versão
- Comandos slash `/ajuda`, `/jogos` e `/sobre`.
- Agenda de NBA, Premier League, La Liga, Bundesliga, Serie A, Ligue 1 e Champions League.
- Horários convertidos para Luanda.
- Publicação diária até 10 jogos às 09:00, se o processo estiver ligado.
- Não inventa estatísticas ou probabilidades.

## Configuração
1. Instala Python 3.11 ou superior.
2. Instala dependências: `pip install -r requirements.txt`
3. Define as variáveis de ambiente `DISCORD_TOKEN` e `CHANNEL_ID`.
4. Opcional: `TIMEZONE=Africa/Luanda`, `POST_HOUR=9`, `MAX_DAILY_GAMES=10`.
5. Executa `python bot.py`.

`CHANNEL_ID` é o ID numérico do canal `#sinais`. Para o copiar no Discord, ativa o Modo de Programador nas definições e usa Copiar ID do canal.

**Nunca publiques o token secreto**, nem o coloques em `bot.py`, no README ou em capturas de ecrã. Se o token for exposto, regenera-o no Discord Developer Portal.

## Importante
O bot consulta agendas públicas da ESPN; a cobertura e disponibilidade podem mudar. Esta versão não prevê resultados nem dá probabilidades quantitativas, porque isso exige dados estatísticos fiáveis e um método de cálculo testável.

GitHub Codespaces é um ambiente de desenvolvimento com limites gratuitos e não garante execução 24/7. A publicação automática funciona apenas enquanto o bot estiver ligado.
