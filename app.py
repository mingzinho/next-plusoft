from flask import Flask, render_template, redirect, url_for, request, jsonify, session, send_file, flash, json, send_from_directory
from sqlalchemy import create_engine, inspect, text
from math import ceil
import pandas as pd
from datetime import datetime
import os
import requests
import io
from scraping import scrape_amazon, scrape_mercadolivre
from ml import perform_machine_learning

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# Pegar string de conexão do ambiente
connection_string = os.getenv('DB_CONNECTION_STRING')

# Ajuste a string de conexão para SQLAlchemy
engine = create_engine(f'mssql+pyodbc:///?odbc_connect={connection_string}')

# Função para verificar autenticação do usuário
def is_user_authenticated(email):
    with engine.connect() as connection:
        query = text("SELECT 1 FROM usuarios WHERE email = :email")
        result = connection.execute(query, {"email": email}).fetchone()
    return result is not None

@app.route('/')
def index():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user_email']
    if not is_user_authenticated(user_email):
        return redirect(url_for('unauthorized'))
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    tables = [table for table in tables if table.lower() != 'usuarios']
    return render_template('index.html', tables=tables)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        if is_user_authenticated(email):
            session['user_email'] = email
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Acesso negado. Email não autorizado.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('login'))

@app.route('/unauthorized')
def unauthorized():
    return render_template('unauthorized.html'), 403

# Funções auxiliares para manipulação de tabelas
def get_columns(table_name):
    inspector = inspect(engine)
    columns = [column['name'] for column in inspector.get_columns(table_name)]
    columns = [column for column in columns if column not in ['data_criacao', 'ultima_atualizacao']]
    return columns

def get_unique_indexes(table_name):
    inspector = inspect(engine)
    indexes = inspector.get_indexes(table_name)
    unique_indexes = [index['column_names'] for index in indexes if index['unique']]
    return unique_indexes

# Rota para visualizar uma tabela específica
@app.route('/table/<table_name>', methods=['GET', 'POST'])
def view_table(table_name):
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user_email']
    if not is_user_authenticated(user_email):
        return redirect(url_for('unauthorized'))

    if request.method == 'POST':
        # Lógica para upload de dados
        return upload_dados(table_name)

    # Obter dados da tabela
    query = f'SELECT * FROM {table_name}'
    df = pd.read_sql_query(query, engine)

    # Remover colunas desnecessárias
    df.drop(columns=['data_criacao', 'ultima_atualizacao'], inplace=True, errors='ignore')

    # Total de linhas
    total_rows = len(df)

    # Filtro de busca
    search_query = request.args.get('search', '')  # Obtenha o termo de busca do usuário
    if search_query:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

    # Ordenação
    sort_column = request.args.get('sort', df.columns[0])  # Coluna padrão para ordenar
    sort_order = request.args.get('order', 'asc')  # Ordem de classificação (asc ou desc)
    if sort_order == 'asc':
        df = df.sort_values(by=[sort_column], ascending=True)
    else:
        df = df.sort_values(by=[sort_column], ascending=False)

    # Configuração da paginação
    page = request.args.get('page', 1, type=int)  # Página atual (valor padrão é 1)
    per_page = 10  # Número de itens por página
    total_items = len(df)
    total_pages = ceil(total_items / per_page)

    # Calcular páginas para exibir
    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)

    # Fatiando os dados do DataFrame para obter os itens da página atual
    start = (page - 1) * per_page
    end = start + per_page
    items_paginados = df.iloc[start:end]

    # Criar dicionário com os dados a serem passados para o template
    dados = {col: items_paginados[col].tolist() for col in items_paginados.columns}

    return render_template(
        'table.html',
        table_name=table_name,
        dados=dados,  # Passando os dados em formato de colunas
        columns=items_paginados.columns.tolist(),  # Passando os nomes das colunas
        page=page,
        zip=zip,
        total_pages=total_pages,
        start_page=start_page,
        end_page=end_page,
        total_rows=total_rows,  # Total de linhas
        search_query=search_query,  # Query de busca
        sort_column=sort_column,  # Coluna para ordenar
        sort_order=sort_order  # Ordem de classificação
    )


# Rota para download de dados em Excel
@app.route('/download/<table_name>')
def download_table(table_name):
    if table_name.lower() == 'usuarios':
        return jsonify({'status': 'error', 'message': 'Você não tem permissão para acessar esta tabela.'})
    
    query = f'SELECT * FROM {table_name}'
    df = pd.read_sql_query(query, engine)
    
    # Remove as colunas de data e a coluna id
    columns_to_remove = ['data_criacao', 'ultima_atualizacao', 'id']
    df.drop(columns=[col for col in columns_to_remove if col in df.columns], inplace=True, errors='ignore')
    
    output_file = f'static/{table_name}.xlsx'
    df.to_excel(output_file, index=False, engine='openpyxl')
    return send_file(output_file, as_attachment=True)

@app.route('/upload/<string:table_name>', methods=['POST'])
def upload_dados(table_name):
    file = request.files.get('file')
    
    if table_name.lower() == 'usuarios':
        return jsonify({'status': 'error', 'message': 'Você não tem permissão para acessar esta tabela.'})
    
    confirm = request.form.get('confirm', 'false').lower() == 'true'
    
    if file:
        try:
            # Verificar o tipo de arquivo
            file_type = file.content_type
            if 'csv' in file_type:
                df = pd.read_csv(file)
            elif 'excel' in file_type or 'spreadsheetml' in file_type or file.filename.endswith('.xlsx'):
                df = pd.read_excel(file, engine='openpyxl')  # engine='openpyxl' para suportar xlsx
            else:
                return jsonify({'status': 'error', 'message': 'Tipo de arquivo não suportado. Apenas arquivos CSV e Excel são permitidos.'})
            
            expected_columns = get_columns(table_name)
            
            # Remover a coluna 'id' das colunas esperadas para a comparação
            if 'id' in expected_columns:
                expected_columns.remove('id')

            # Normalizar as colunas do arquivo e as esperadas para evitar problemas de case-sensitive
            file_columns = [col.lower() for col in df.columns]
            expected_columns = [col.lower() for col in expected_columns]

            # Comparar colunas esperadas (sem 'id') com as do arquivo
            if sorted(file_columns) != sorted(expected_columns):
                return jsonify({'status': 'error', 'message': f'As colunas do arquivo ({file_columns}) não correspondem às colunas esperadas na tabela ({expected_columns}). Verifique e tente novamente.'})

            if df.isnull().values.any() and not confirm:
                return jsonify({'status': 'warning', 'message': 'O arquivo contém campos não preenchidos. Deseja continuar com o upload?'})
            
            # Verificação e correção do formato da coluna de data
            date_columns = [col for col in expected_columns if 'data' in col]
            for date_col in date_columns:
                if date_col in df.columns:
                    df[date_col] = pd.to_datetime(df[date_col], errors='coerce').dt.strftime('%Y-%m-%d')
                    if df[date_col].isnull().any():
                        return jsonify({'status': 'error', 'message': f'A coluna {date_col} contém valores de data no formato incorreto. Por favor, insira no formato YYYY-MM-DD.'})

            # Atualização dos campos de data
            current_time = datetime.now()
            if 'data_criacao' not in df.columns:
                df['data_criacao'] = current_time
            if 'ultima_atualizacao' not in df.columns:
                df['ultima_atualizacao'] = current_time

            # Inserir dados no banco de dados
            df.to_sql(table_name, con=engine, if_exists='append', index=False)

            # Recuperar os dados atualizados da tabela para exibição
            updated_df = pd.read_sql(f'SELECT * FROM {table_name}', con=engine)
            updated_html = updated_df.to_html(classes='data', header=True, index=False)

            


            return jsonify({'status': 'success', 'message': 'Dados carregados com sucesso.', 'html': updated_html})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})
    
    return jsonify({'status': 'error', 'message': 'Nenhum arquivo foi enviado.'})

@app.route('/consumir_api_amazon', methods=['GET', 'POST'])
def consumir_api_amazon():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    user_email = session['user_email']
    if not is_user_authenticated(user_email):
        return redirect(url_for('unauthorized'))

    if request.method == 'POST':
        try:
            # Chamada à API da Amazon
            url = "https://real-time-amazon-data.p.rapidapi.com/products-by-category"
            querystring = {
                "category_id": "24000582011",
                "page": "1",
                "country": "US",
                "sort_by": "RELEVANCE",
                "product_condition": "ALL",
                "is_prime": "false"
            }
            headers = {
                "x-rapidapi-key": "f8ab92d4f4msh7cd359334023e09p1e2f2djsnca168ff28f37",  # Substitua por sua chave
                "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com"
            }
            response = requests.get(url, headers=headers, params=querystring)

            # Verificar o status da resposta
            if response.status_code != 200:
                flash('Erro ao buscar dados da API da Amazon.', 'error')
                return redirect(url_for('consumir_api_amazon'))

            # Capturar a resposta da API
            data = response.json()

            if 'data' not in data or 'products' not in data['data']:
                flash('Nenhum dado de produto encontrado na resposta da API.', 'warning')
                return redirect(url_for('consumir_api_amazon'))

            # Extrair os produtos da resposta
            products = data['data']['products']
            if not products:
                flash('Nenhum produto encontrado na resposta da API.', 'warning')
                return redirect(url_for('consumir_api_amazon'))

            # Converter os produtos para DataFrame
            df = pd.DataFrame(products)

            # Filtrar apenas as colunas desejadas
            colunas_desejadas = [
                'asin', 'product_price', 'product_title', 'product_original_price', 
                'product_star_rating', 'product_num_ratings', 'product_num_offers',
                'product_minimum_offer_price', 'is_best_seller', 'is_amazon_choice', 
                'is_prime', 'climate_pledge_friendly', 'sales_volume', 'delivery',
                'has_variations', 'product_availability'
            ]

            # Garantir que as colunas existam no DataFrame e filtrá-las
            df_filtrado = df[colunas_desejadas].copy()

            # Adicionar colunas obrigatórias e preencher valores faltantes
            df_filtrado['status'] = 'OK'
            df_filtrado['request_id'] = 'unique_request_id'  # Substitua por um valor único gerado ou apropriado
            df_filtrado['data_criacao'] = datetime.now()
            df_filtrado['ultima_atualizacao'] = datetime.now()

            # Preencher valores nulos nas colunas obrigatórias
            df_filtrado = df_filtrado.fillna('')

            # Inserir dados no banco de dados
            df_filtrado.to_sql('ProdutosConsumidosAPI', con=engine, if_exists='append', index=False)

            flash('Dados da API da Amazon inseridos com sucesso!', 'success')
            return redirect(url_for('consumir_api_amazon'))

        except Exception as e:
            flash(f'Ocorreu um erro: {str(e)}', 'error')
            return redirect(url_for('consumir_api_amazon'))

    return render_template('consumir_api_amazon.html')


# Rota para visualizar os dados da tabela ProdutosConsumidosAPI
@app.route('/produtos_consumidos_api')
def view_produtos_consumidos_api():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    user_email = session['user_email']
    if not is_user_authenticated(user_email):
        return redirect(url_for('unauthorized'))

    # Obter dados da tabela ProdutosConsumidosAPI
    query = 'SELECT * FROM ProdutosConsumidosAPI'
    df = pd.read_sql_query(query, engine)

    # Remover colunas desnecessárias
    df.drop(columns=['data_criacao', 'ultima_atualizacao'], inplace=True, errors='ignore')

    # Total de linhas
    total_rows = len(df)

    # Filtro de busca
    search_query = request.args.get('search', '')  # Obtenha o termo de busca do usuário
    if search_query:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]

    # Ordenação
    sort_column = request.args.get('sort', 'id')  # Coluna padrão para ordenar
    sort_order = request.args.get('order', 'desc')  # Ordem de classificação (asc ou desc)
    if sort_order == 'asc':
        df = df.sort_values(by=[sort_column], ascending=True)
    else:
        df = df.sort_values(by=[sort_column], ascending=False)

    # Configuração da paginação
    page = request.args.get('page', 1, type=int)  # Página atual (valor padrão é 1)
    per_page = 10  # Número de itens por página
    total_produtos = len(df)
    total_pages = ceil(total_produtos / per_page)

    # Calcular páginas para exibir
    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)

    # Fatiando os dados do DataFrame para obter os itens da página atual
    start = (page - 1) * per_page
    end = start + per_page
    produtos_paginados = df[start:end]

    # Criar dicionário com as colunas solicitadas
    dados = {
        'asin': produtos_paginados['asin'].tolist(),
        'product_price': produtos_paginados['product_price'].tolist(),
        'product_title': produtos_paginados['product_title'].tolist(),
        'product_original_price': produtos_paginados['product_original_price'].tolist(),
        'product_star_rating': produtos_paginados['product_star_rating'].tolist(),
        'product_num_ratings': produtos_paginados['product_num_ratings'].tolist(),
        'product_num_offers': produtos_paginados['product_num_offers'].tolist(),
        'product_minimum_offer_price': produtos_paginados['product_minimum_offer_price'].tolist(),
        'is_best_seller': produtos_paginados['is_best_seller'].tolist(),
        'is_amazon_choice': produtos_paginados['is_amazon_choice'].tolist(),
        'is_prime': produtos_paginados['is_prime'].tolist(),
        'climate_pledge_friendly': produtos_paginados['climate_pledge_friendly'].tolist(),
        'sales_volume': produtos_paginados['sales_volume'].tolist(),
        'delivery': produtos_paginados['delivery'].tolist(),
        'has_variations': produtos_paginados['has_variations'].tolist(),
        'product_availability': produtos_paginados['product_availability'].tolist()
    }

    return render_template(
        'produtos_consumidos_api.html',
        dados=dados,  # Passando os dados em formato de colunas
        page=page,
        zip=zip,
        total_pages=total_pages,
        start_page=start_page,
        end_page=end_page,
        total_rows=total_rows,  # Total de linhas
        search_query=search_query,  # Query de busca
        sort_column=sort_column,  # Coluna para ordenar
        sort_order=sort_order  # Ordem de classificação
    )


# Rota para Web Scraping
@app.route('/scrape', methods=['GET', 'POST'])
def scrape():
    if 'user_email' not in session:
        return redirect(url_for('login'))
    
    user_email = session['user_email']
    if not is_user_authenticated(user_email):
        return redirect(url_for('unauthorized'))
    
    if request.method == 'POST':
        platform = request.form.get('platform')  # Adicionar plataforma (Amazon ou Mercado Livre)
        url = request.form.get('url')
        
        if not url:
            return render_template('scrape.html', error="URL não fornecida.")
        
        try:
            # Escolher qual função de scraping chamar
            if platform == 'mercadolivre':
                data = scrape_mercadolivre(url)
            elif platform == 'amazon':
                data = scrape_amazon(url)
            else:
                return render_template('scrape.html', error="Plataforma inválida.")
            
            # Criar o DataFrame com os dados raspados
            df = pd.DataFrame(data, columns=['produto', 'preco', 'empresa', 'origem', 'avaliacao', 'data'])
            current_time = datetime.now()
            df['data_criacao'] = current_time
            df['ultima_atualizacao'] = current_time
            
            # Opção para download em Excel e CSV
            excel_output_file = 'static/scraped_data.xlsx'
            csv_output_file = 'static/scraped_data.csv'
            df.to_excel(excel_output_file, index=False, engine='openpyxl')
            df.to_csv(csv_output_file, index=False)

            # Inserir no banco de dados 'ProdutosSustentaveis'
            df.to_sql('ProdutosSustentaveis', con=engine, if_exists='append', index=False)

            # Retornar a tabela HTML e links de download
            data_html = df.to_html(classes='data', header="true", index=False)
            return render_template('scrape.html', success="Dados raspados e inseridos com sucesso!",
                                   data_html=data_html, excel_link=excel_output_file, csv_link=csv_output_file)
        except Exception as e:
            return render_template('scrape.html', error=str(e))
    
    return render_template('scrape.html')

# Rota para Machine Learning
@app.route('/ml', methods=['GET', 'POST'])
def ml():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    user_email = session['user_email']
    if not is_user_authenticated(user_email):
        return redirect(url_for('unauthorized'))

    # Obter os produtos da tabela
    query = "SELECT DISTINCT produto FROM ProdutosSustentaveis"
    df = pd.read_sql_query(query, engine)
    produtos = df['produto'].tolist()

    if request.method == 'POST':
        produto_selecionado = request.form.get('product')
        # Período padrão de 12 meses se não fornecido
        periodo = int(request.form.get('period', 12))  # Agora estamos lidando com meses

        # Passar o produto selecionado para a função de machine learning
        resultado = perform_machine_learning(engine, produto=produto_selecionado, period=periodo)
        
        if resultado is None:
            resultado = {'forecast': pd.DataFrame(), 'mae': None, 'image_path': None}

        return render_template('ml_result.html', 
                               resultados=resultado, 
                               selected_period=periodo,
                               products=produtos,
                               selected_product=produto_selecionado)

    # Se o método for GET, exibir o formulário com produtos e período padrão de 12 meses
    return render_template('ml_result.html', 
                           resultados={'forecast': pd.DataFrame(), 'mae': None, 'image_path': None},
                           selected_period=12,  # Mudança aqui para refletir meses
                           products=produtos,
                           selected_product=None)



@app.route('/api_data', methods=['GET'])
def api_data():
    url = "https://real-time-amazon-data.p.rapidapi.com/products-by-category"
    querystring = {"category_id": "24000582011", "page": "1", "country": "US", "sort_by": "RELEVANCE", "product_condition": "ALL", "is_prime": "false"}
    headers = {
        "x-rapidapi-key": "f8ab92d4f4msh7cd359334023e09p1e2f2djsnca168ff28f37",
        "x-rapidapi-host": "real-time-amazon-data.p.rapidapi.com"
    }
    response = requests.get(url, headers=headers, params=querystring)
    data = response.json()

    # Depuração
    print("Dados da API:", data)

    # Transformar os dados em um DataFrame
    df = pd.json_normalize(data.get('products', []))  # Ajuste conforme a estrutura real do JSON

    # Especificar as colunas desejadas
    colunas_desejadas = ['asin', 'product_price', 'product_title', 'product_original_price', 'product_original_price', 'product_star_rating	', 'product_num_ratings', 'product_num_offers', 'product_minimum_offer_price', 'is_best_seller', 'is_amazon_choice', 'is_prime', 'climate_pledge_friendly', 'sales_volume', 'delivery', 'has_variations']  # Substitua pelos nomes corretos das colunas que você quer
    df_filtrado = df[colunas_desejadas]

    # Converter o DataFrame filtrado para HTML
    data_html = df_filtrado.to_html(classes='table table-striped', header="true", index=False)

    return render_template('api_data.html', data_html=data_html)

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('/home/site/wwwroot/static/', filename)

@app.route('/show_image/<product>/<int:period>')
def show_image(product, period):
    # Chamar a função que gera o gráfico
    result = perform_machine_learning(engine, produto=product, period=period)
    
    # Retornar a imagem a partir do buffer gerado
    return send_file(
        io.BytesIO(result['image_buffer'].getvalue()),  # Buffer da imagem
        mimetype='image/png',  # Tipo de conteúdo da resposta HTTP
        as_attachment=False,  # Não baixar automaticamente o arquivo
        attachment_filename=f'{product}_previsao.png'  # Nome sugerido da imagem
    )


if __name__ == '__main__':
    # Cria a pasta 'static' se não existir
    if not os.path.exists('static'):
        os.makedirs('static')
    app.run(debug=True, host='0.0.0.0', port =5000)

