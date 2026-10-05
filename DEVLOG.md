# Devlog da Ponderada

## 1. O q usei e a ideia do negocio

Usei o Codex pra me da umas ideia e me ajuda a puxar os dado, montar as estrutura do treino, criar os script e subir a API sem perde tempo reescrevendo codigo basico.

A ideia do projeto e bem direta: pegar o historico de fechamento do Bitcoin dos ultimos 7 dias (da janela de D-6 ate o dia D) pra tentar adivinhar qual vai ser o preço no dia seguinte (D+1). Escolhi essa janela de uma semana pq deixa o contrato da API bem simples de entender e explicar, nao pq e a formula magica de ficar rico no mercado.

---

## 2. Arrumando o ambiente de dev (14h28 as 14h35)

* **Estrutura:** A atividade pedi a integraçao completa entre o treino, arquivo do modelo salvo, backend Python rodando em container e uma aplicaçao cliente chamando as rota.
* **Ambiente Virtual:**
* O `python` do terminal do Windows tava me levando pra um erro do WindowsApps, ai usei o executavel direto da pasta do dev pra criar a `.venv` no Python 3.12 pra prejudicar o sistema misturando biblioteca de outros projeto.
* Salvei as biblioteca principais no `requirements.txt` com versao travada e depois rodei o `pip freeze` pra salvar o `requirements.lock.txt` com todas as dependencia indireta. Os Dockerfiles usam esse lock pra não dar erro de versão diferente entre quem treina e quem carrega o modelo.



---

## 3. Puxando e limpando os dado (14h35 as 14h50)

* Baixei o CSV diario de BTC/USD da Bitstamp direto do CryptoDataDownload usando o PowerShell pra não ter que fica fazendo requisição na internet toda vez que for rodar:
```powershell
Invoke-WebRequest -Uri https://www.cryptodatadownload.com/cdd/Bitstamp_BTCUSD_d.csv -OutFile btc_source.csv

```


* O arquivo original vinha com uma linha de link antes das coluna e tava invertido (do dia mais recente pro mais antigo).
* No `training/prepare_data.py` usei `skiprows=1`, arrumei os tipo de dados e ordenei por data.
* Recortei o periodo fixo entre **2023 e 2025** (deu 1.096 dias limpos, sem dia duplicado ou buraco no calendario). Descartei o candle aberto do dia do download.
* Mantive so as coluna `date` e `close`. Tirei volume pra não poluir a API sem necessidade. O CSV original ficou fora do Git, mas o CSV tratado e o `data/source.json` foram pra entrega.

---

## 4. Montando o treino e exportando (14h50 as 15h38)

* Separei as feature no `features.py` pra usar o mesmo codigo tanto no treino quanto na inferencia. Ele pega do `close_lag_6` ate o `close_lag_0` (do mais antigo pro mais novo). O alvo vem do `close.shift(-1)`.
* Com 7 preços por entrada, os 1.096 dias geraram 1.089 exemplo (os 6 primeiro dia nao tem historico pra tras e o ultimo nao tem o dia seguinte no CSV).
* Escolhi `LinearRegression` da scikit-learn por ser um modelo simples, rapido e facil de explicar na apresentaçao. Nao fiz normalizaçao nem tuning de hiperparametro pq e uma regressao linear sem regularizaçao e tudo ta na mesma moeda (USD).
* Cortei em 80% treino (871 exemplo) e 20% teste (218 exemplo) mantendo a ordem do tempo sem embaralhar, se nao vazava dado do futuro pro passado.
* **Resultado das metricas:**

| Metodo | MAE (USD) | RMSE (USD) |
| --- | --- | --- |
| **Regressao Linear** | **1.518,28** | **2.013,76** |
| Baseline (repetir o ultimo preço) | 1.480,23 | 1.968,38 |

*(A baseline de so repetir o ultimo dia deu um resultado um tiquinho melhor kkkk mas deixei registrado sem caçar desculpa, o objetivo aqui e provar a integraçao da arquitetura).*

* Na primeira rodada deu erro DLL do SciPy no Windows porque o Controle de Aplicativo bloqueou o arquivo. Mudei a permissao do ambiente e rodou de boa.
* Salvei o modelo usando `joblib` junto com metadados e o hash do arquivo pra API saber se esta lendo a versao certa.

---

## 5. API em FastAPI e os Testes (15h38 as 16h08)

* Fiz o backend em FastAPI porque e leve, trata JSON rapido e ja da a documentaçao no `/docs`. O modelo e carregado no inicio da API uma vez so, pra não ter que reabrir o arquivo em cada requisiçao HTTP.
* **Rotas:**
* `/predict`: Pede 7 preço positivo e finito mais o `last_date` (a data serve pra saber qual dia exato ta sendo previsto no futuro). Se mandar campo extra ou quantidade errada de dia, ele barra pra nao aceitar entrada cagada.
* `/health`: So da OK se a API iniciou com o modelo carregado e com hash batendo.


* No pip inicial o NumPy 2.5.3 e SciPy 1.18.1 tavam soltando warning de depreciaçao. Travei em NumPy 2.2.6 e SciPy 1.15.3 no lockfile e refiz o treino. Os avisos sumiram e o resultado continuou o mesmo.
* **Testes automatizados:**
```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

```


Os 6 testes passaram de primeira (testando alinhamento temporal, hash de integridade, erros de contrato como numero negativo, texto ou falta de dado, e se a resposta da API e identica ao modelo local).

---

## 6. Teste local e o pesadelo do Docker (16h08 as 16h28)

* Subi a API local no Uvicorn na porta 8000. O cliente chamou e recebeu HTTP 200 com a previsao de **USD 87.703,54** para **01/01/2026** (usando os fechamento de 25/12/2025 ate 31/12/2025). Os teste de smoke tb deram certo.
* Montei dois Dockerfiles e o `compose.yaml`. O container de treino salva em `/app/artifacts` e a API le essa pasta como `:ro` (read-only).
* **O B.O. do Docker:** Quando fui rodar o Compose, o Docker Desktop travou total antes do build. Deu erro de permissao no socket `sailor-ingest.sock` (WinError 1920). Tentei dar `docker desktop start`, tentei renomear o arquivo com ele parado mas o Windows não deixou mexer de jeito nenhum.
* Como nao deu pra rodar os containers na minha maquina por causa desse bug no Docker do Windows, registrei a treta toda no `docs/evidencias/STATUS.md` pra ficar transparente.
* Desenhei o diagrama UML da arquitetura no PlantUML e salvei a imagem PNG/SVG no README pra mostrar todo o fluxo do CSV ate o cliente HTTP.

---

## 7. Ajustes finais, Notebook e o CI/CD pra salvar a entrega

* Coloquei quebra de linha LF no `.gitattributes` pro Git não converter os final de linha do CSV no Windows e estragar o hash que e conferido nos teste.
* **Requisito do Notebook:** Como o enunciado aceitava notebook e o Docker local deu erro e eu não consegui contornar, criei o `training/treinamento.ipynb` usando o mesmo script no fundo pra nao duplicar codigo. Rodei ele via `run_notebook.py` com o kernel da `.venv`. Ele rodou certo e deu os mesmo 1.089 exemplo e os 1.518,28 de MAE (log salvo em `treino-notebook.txt`).
* **CI/CD no GitHub Actions:** Pra resolver o problema do Docker nao subir no meu PC, criei a action `.github/workflows/validar-docker.yml`. Ela sobe uma maquina Linux no GitHub, faz o build das imagem, roda o treino no container, sobe a API, chama o cliente e roda a bateria de teste completa na nuvem assim q eu mandar o push.