# Previsão do fechamento do Bitcoin

Atividade ponderada do M7: tentar adivinhar o fechamento do Bitcoin em USD no dia seguinte usando os ultimos sete fechamento diario. A ideia foi fazer um caminho direto e sem complicacao: CSV → treino → arquivo do modelo → API → cliente.

**Como esta o projeto agora:** modelo treinado e exportado no notebook que eu rodei, API e o cliente testado localmente no meu computador. A execucao do backend no container esta travada porque o Docker Desktop nao quis subir no meu Windows por causa de um erro de socket. Nao mandei os commits para o GitHub ainda. AVISO: essa previsao e so um experimento para a materia da faculdade, nao use isso como recomendacao para investir dinheiro.

## Apoio de IA

O projeto teve uma ajuda do Codex para puxar os dados, arrumar uns scripts e estruturar as coisas como ja falei la no devlog.

## Porque escolhi cada coisa

| Escolha | Porque escolhi isso |
| --- | --- |
| CSV no projeto | Para nao ter que ficar baixando preco da internet na hora de apresentar para o professor. |
| pandas | Para ler, ordenar, conferir os dados e montar as janelas sem passar raiva. |
| Regressão linear do scikit-learn | Porque e rapida e simples de explicar em uma primeira solucao. |
| Joblib | Para salvar o modelo treinado em um arquivo e outro processo carregar depois. |
| FastAPI | Recebe JSON com facilidade, valida as entradas e ja cria o `/docs` para testar. |
| Dois containers | Um container para treinar e finalizar, e outro da API para ficar rodando direto. |
| Cliente Python | Para provar que a API funciona via HTTP sem precisar inventar interface visual. |

Não usei normalizador porque as sete variaveis sao todas precos na mesma moeda (USD) e e uma regressao linear simples. Nao fiquei testando muitos algoritmos nem regulando parametros. Se for colocar normalizacao depois, tem que ajustar so no treino e salvar junto com o modelo para nao estragar o teste.

## Os dados e o treino

Fonte: [CryptoDataDownload — BTC/USD diario da Bitstamp](https://www.cryptodatadownload.com/cdd/Bitstamp_BTCUSD_d.csv). O recorte em `data/btc_daily.csv` vai de **01/01/2023 ate 31/12/2025**, dando **1.096 dias**. A data UTC marca quando o candle abre e o `close` e o fechamento do dia na exchange.

O CSV original vinha com um link no topo e as datas todas invertidas. O `training/prepare_data.py` pula essa linha, converte os tipos, pega o periodo certo, ordena e ve se nao tem dia repetido ou faltando. Nao tinha nenhum dia faltando e a fonte estava limpa. Mantive so `date` e `close` sem inventar valores. O resumo esta em `data/source.json`.

Cada exemplo usa os fechamentos de **D-6 ate D** (do mais antigo para o mais recente) para prever **D+1**. Exemplo: usa de 01/01 a 07/01/2023 para prever o dia 08/01/2023. Como os seis primeiros dias nao tem historico para tras e o ultimo nao tem o dia seguinte no arquivo, sobrou **1.089 exemplos**.

| Parte | Quantidade de exemplos | Data dos alvos |
| --- | --- | --- |
| Treino (80% mais antigo) | 871 | 08/01/2023 ate 27/05/2025 |
| Teste (20% mais recente) | 218 | 28/05/2025 ate 31/12/2025 |

Nao misturei os dados para nao vazar o futuro no passado. O `features.py` usa a mesma ordem no treino e na API. O modelo salvo foi treinado so na parte de treino, sem olhar a parte de teste.

## O que deu no final (Resultado)

| Metodo | MAE (USD) | RMSE (USD) |
| --- | --- | --- |
| Regressão linear | 1.518,28 | 2.013,76 |
| Repetir o ultimo preco (Baseline) | 1.480,23 | 1.968,38 |

O MAE e o erro medio em dolar e o RMSE pesa mais os erros grandes. Quanto menor, melhor. **Nesse teste a regressao linear ficou um pouco pior do que so repetir o ultimo preco.** Nao da para sair dizendo que isso preve o mercado de verdade. Os arquivos de metricas e previsao estao todos salvos em `artifacts`.

## Arquitetura do sistema

O PlantUML e a imagem SVG estao la na pasta `docs`. O treino grava o `model.joblib`, os metadados e os resultados na pasta `artifacts` do computador. A API pega essa mesma pasta em `/app/artifacts` so para leitura (`:ro`), confere o hash e a ordem das variaveis e carrega o modelo quando inicia. Ela nao treina de novo.

Usei bind mount para ver o arquivo direto no projeto. O perfil `train` serve para nao rodar o treino toda vez que for subir a API.

## Como rodar isso no Docker

Precisa de Git, Docker Desktop funcionando no Linux e Python 3.12 para o cliente. O cliente nao usa nenhuma biblioteca diferente, so as nativas do Python.

No PowerShell do Windows:

```powershell
git clone https://github.com/v1t0rluc3n4/Ponderada-Murilo-.git
cd Ponderada-Murilo-
docker info
docker compose --profile train build
docker compose --profile train run --rm training
docker compose up -d --wait backend
docker compose ps
Invoke-RestMethod http://localhost:8000/health
python client/predict.py
python tests/smoke.py

```

Se ja estiver na pasta, comeca direto no `docker info`. Confirme que o treino acabou sem dar erro antes de ligar o backend. Da para testar no navegador abrindo [http://localhost:8000/docs](http://localhost:8000/docs).

Para testar se o modelo recarrega certo quando o container reinicia:

```powershell
docker compose restart backend
docker compose up -d --wait backend
python tests/smoke.py
docker compose logs --no-color backend
docker compose down

```

Se gerar outro modelo, reinicia a API. Se estiver rodando a API localmente, fecha ela antes de usar a porta 8000 no Docker. Os comandos para salvar evidencia estao em [docs/evidencias/STATUS.md](https://www.google.com/search?q=docs/evidencias/STATUS.md); a execucao no Docker local ainda nao foi confirmada por causa do problema.

## Entrada e resposta da API

`GET /health` manda HTTP 200 com `model_loaded: true` quando o modelo esta carregado. Se o modelo sumir ou o hash nao bater, a API nem inicia.

`POST /predict` exige exatamente sete precos positivos e validos na ordem do tempo e o `last_date` (data do ultimo candle). As datas tem que ser seguidas: o cliente confere isso no CSV, mas a API nao tem como adivinhar de onde veio o preco.

JSON de teste que usei localmente:

```json
{"prices": [87172, 87296, 87810, 87870, 87119, 88390, 87496], "last_date": "2025-12-31"}

```

A API respondeu HTTP 200 com `predicted_close: 87703.54`, em USD e a data `prediction_date: "2026-01-01"`. A data e sempre o dia seguinte da entrada, nao o dia de hoje do computador. O resultado completo esta em `docs/evidencias/cliente-local.txt`.

Se mandar menos ou mais de sete precos, valor negativo, texto, data errada ou campo extra, a API barra com erro HTTP 422.

## Testando sem Docker (Local no computador)

Ajuda a ver se o codigo esta bom, mas nao substitui a entrega do container que o professor pediu:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock.txt
.\.venv\Scripts\python.exe -m training.train
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000

```

Em outra janela do terminal:

```powershell
.\.venv\Scripts\python.exe client/predict.py
.\.venv\Scripts\python.exe tests/smoke.py

```

O CSV tratado ja esta pronto. Se quiser refazer do zero: `.\.venv\Scripts\python.exe -m training.prepare_data`.

## Treino no Notebook

O [training/treinamento.ipynb](https://www.google.com/search?q=training/treinamento.ipynb) esta rodado e com os resultados salvos la dentro. Ele chama o mesmo script de treino, gera o modelo e testa a recarga. Fiz isso porque o Docker deu problema no meu computador e o professor aceita notebook no enunciado.

Para rodar o notebook pela venv:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-notebook.txt
.\.venv\Scripts\python.exe -m training.run_notebook

```

Isso resolve a parte do treino, mas o backend ainda precisa ser mostrado rodando em container.

## Validar o Docker pelo GitHub

Criei o arquivo `.github/workflows/validar-docker.yml` para rodar tudo em um Linux la no GitHub Actions: ele monta os containers, treina, sobe a API, roda o cliente e testa tudo.

Quando eu fizer o push, e so abrir a aba **Actions**, clicar em **Validar containers** e baixar os logs em **evidencias-docker**. Isso vai provar que o Docker funciona no Linux mesmo com o meu Windows dando erro no socket.




