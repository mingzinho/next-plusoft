# 🌍 SustenAI - Previsão Personalizada de Demanda em E-commerce Sustentável 🌱
![Status](https://img.shields.io/badge/STATUS-EM%20DESENVOLVIMENTO-yellow?style=for-the-badge)

> Aplicação de Inteligência Artificial e Análise de Dados para otimizar o mercado de produtos sustentáveis.

## 📌 Descrição do Projeto

**SustenAI** é uma plataforma inovadora que utiliza Inteligência Artificial e análise de dados para prever a demanda de produtos sustentáveis em e-commerce, oferecendo insights poderosos tanto para empresas quanto para consumidores. Através de funcionalidades como previsão de demanda e curadoria de produtos, o SustenAI visa melhorar a eficiência da cadeia de suprimentos e incentivar o consumo sustentável.

O projeto é focado em:

- Previsão personalizada de demanda.
- Curadoria automatizada de produtos sustentáveis.
- Simulação de cenários para decisões empresariais mais informadas.
- Incentivo ao consumo consciente e à sustentabilidade.

## 🎯 Objetivo

Fornecer uma solução robusta para e-commerces que lidam com produtos sustentáveis, aumentando a precisão de estratégias de marketing e promovendo um ecossistema de sustentabilidade. A plataforma permite que os gestores tomem decisões mais informadas, baseadas em dados e projeções, enquanto os consumidores têm acesso a produtos que promovem um futuro mais sustentável.

## 💡 Funcionalidades

- **Previsão de Demanda**: Algoritmos avançados de machine learning para prever a demanda de produtos com alta precisão.
- **Curadoria de Produtos Sustentáveis**: Filtragem e categorização de produtos conforme critérios de sustentabilidade.
- **Simulação de Cenários**: Possibilidade de simular diferentes cenários de vendas para apoiar estratégias empresariais.
- **Insights para Decisão**: Painel intuitivo com insights para a tomada de decisão estratégica.

## 🗂️ Estrutura do Projeto

### 📂 Pasta Static
- **scraped_data.csv:** Arquivo .csv vazio para permitir a inserção dos dados, gravação no banco e download.
- **scraped_data.xlsx:** Arquivo .xlsx vazio para permitir a inserção dos dados, gravação no banco e download.

### 📂 Pasta Templates
Pasta contendo todos os arquivos necessarios para interface de front-end, nela contemos arquivos .html, .css e .js.

### 📂 Pasta Plusoft
Pasta principal do projeto contendo os arquivos escritos em Python para rodar a aplicação, além do Procfile para o Azure reconhecer o arquivo main.

## 🛠️ Tecnologias Utilizadas

### 🔧 Ferramentas e Frameworks
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![MicrosoftSQLServer](https://img.shields.io/badge/Microsoft%20SQL%20Server-CC2927?style=for-the-badge&logo=microsoft%20sql%20server&logoColor=white)
![Azure](https://img.shields.io/badge/azure-%230072C6.svg?style=for-the-badge&logo=microsoftazure&logoColor=white)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)


### 📚 Bibliotecas e Ferramentas
- **Matplotlib** para a criação de gráficos.
- **scikit-learn** para o machine learning.
- **RandomForest** para gerar o machine learning.
- **Git** para controle de versão.

## 🚀 Como Executar o Projeto

Siga estas etapas para configurar e executar a aplicação localmente:

1. **Clone o repositório:**
   ```bash
   https://github.com/mingzinho/next-plusoft
   ```

2. **Navegue até o diretório do projeto:**
   ```bash
   cd plusoft
   ```

3. **Instale as dependências:**
   ```bash
   pip install requirements.txt
   ```

4. **Configure a string de conexão do banco e da API no `app.py`:**
   - Atualize a string de conexão para conectar ao seu banco de dados Azure e ao RapidAPI.
  
5. **Baixe driver obdc para conseguir fazer conexao com o banco de dados:**
   - https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server?view=sql-server-ver16

5. **Execute a aplicação:**
   ```bash
   python app.py
   ```

## 📊 Estrutura do site

- **Inicio**: Area inicial para acessar tabelas do banco.
- **Web Scraping**: Possibilita o usuario .
- **Arquivo**: Controla os metadados dos arquivos carregados pelos usuários.
- **Previsao**: Registra os resultados das previsões de demanda para cada produto.

## 💻 Requisitos

- [Python 3.12+](https://www.python.org/downloads/release/python-3120/)
- [Visual Studio Code](https://code.visualstudio.com/)
- [Git](https://git-scm.com)

## 📈 Roadmap

- Implementar notificações de previsão em tempo real.
- Adicionar integração com outras APIs de e-commerce.
- Criar um painel para visualização de métricas ambientais dos produtos.


## 🫂 Equipe de Desenvolvimento

| Nome                        | Função                                |
| ---------------------------- | ------------------------------------- |
| **[Rafaela](https://github.com/rafluuz)** | .NET & Banco de Dados |
| **[Ming](https://github.com/mingzinho)** | IA & DevOps Cloud Computing
| **[Clara](https://github.com/clarabcerq)** | Java |
| **[Guilherme](https://github.com/Guilherme379)** | Complience & Quality Assurance |
| **[Pedro Batista ](https://github.com/yoboypb)** | Mobile |

---

<a href="#top">Voltar ao topo</a>
