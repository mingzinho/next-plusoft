from flask import Flask, render_template, redirect, url_for, request, jsonify, session, send_file, flash, json, send_from_directory
from sqlalchemy import create_engine, inspect, text
import pandas as pd
from datetime import datetime
import os
import requests
import io
from scraping import scrape_amazon, scrape_mercadolivre
from ml import perform_machine_learning

app = Flask(__name__)
app.secret_key = 'ming123456'  # Chave secreta para sessões

# Configuração do banco de dados
connection_string = (
    'Driver={ODBC Driver 18 for SQL Server};'
    'Server=tcp:bancoming.database.windows.net,1433;'
    'Database=bancoplusoft;'
    'Uid=mingplusoft;'
    'Pwd=Ming@123;'
    'Encrypt=yes;'
    'TrustServerCertificate=no;'
    'Connection Timeout=30;'
)

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
    df.drop(columns=['data_criacao', 'ultima_atualizacao'], inplace=True, errors='ignore')
    data_html = df.to_html(classes='data', header="true", index=False)
    return render_template('table.html', table_name=table_name, data_html=data_html, columns=get_columns(table_name))

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
            status_code = response.status_code
            response_text = response.text
            print(f"Status Code: {status_code}")  # Debug
            print(f"Response Text: {response_text}")  # Debug

            if status_code != 200:
                flash('Erro ao buscar dados da API da Amazon.', 'error')
                return redirect(url_for('consumir_api_amazon'))

            # Capturar a resposta completa da API
            data = response.json()
            print(f"Response JSON: {data}")  # Debug

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

            # Adicionar colunas obrigatórias e preencher valores faltantes
            df['status'] = 'OK'
            df['request_id'] = 'unique_request_id'  # Substitua por um valor único gerado ou apropriado
            df['data_criacao'] = datetime.now()
            df['ultima_atualizacao'] = datetime.now()

            # Garantir que não haja valores nulos nas colunas obrigatórias
            required_columns = ['asin', 'product_title', 'product_url']
            for col in required_columns:
                if col not in df.columns:
                    df[col] = ''
                df[col] = df[col].fillna('')  # Preencher valores nulos com string vazia

            # Tratar colunas adicionais, se existentes
            df['product_star_rating'] = pd.to_numeric(df.get('product_star_rating', pd.Series()), errors='coerce')
            df['product_num_ratings'] = pd.to_numeric(df.get('product_num_ratings', pd.Series()), errors='coerce')
            df['product_num_offers'] = pd.to_numeric(df.get('product_num_offers', pd.Series()), errors='coerce')
            df['is_best_seller'] = df.get('is_best_seller', pd.Series()).astype(bool, errors='ignore')
            df['is_amazon_choice'] = df.get('is_amazon_choice', pd.Series()).astype(bool, errors='ignore')
            df['is_prime'] = df.get('is_prime', pd.Series()).astype(bool, errors='ignore')
            df['climate_pledge_friendly'] = df.get('climate_pledge_friendly', pd.Series()).astype(bool, errors='ignore')
            df['has_variations'] = df.get('has_variations', pd.Series()).astype(bool, errors='ignore')

            # Remover as colunas 'data' e 'parameters'
            if 'data' in df.columns:
                df = df.drop(columns=['data'])
            if 'parameters' in df.columns:
                df = df.drop(columns=['parameters'])

            # Inserir dados no banco de dados usando pd.to_sql
            df.to_sql('ProdutosConsumidosAPI', con=engine, if_exists='append', index=False)

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
    
    # Gerar HTML dos dados
    data_html = df.to_html(classes='data', header="true", index=False)

    return render_template('produtos_consumidos_api.html', data_html=data_html)


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
        periodo = int(request.form.get('period', 30))  # Período padrão de 30 dias se não fornecido

        # Passar o produto selecionado para a função de machine learning
        resultado = perform_machine_learning(engine, produto=produto_selecionado, period=periodo)
        if resultado is None:
            resultado = {'forecast': pd.DataFrame(), 'mae': None, 'fig': None}
        return render_template('ml_result.html', 
                               resultados=resultado, 
                               selected_period=periodo,
                               products=produtos,
                               selected_product=produto_selecionado)

    # Se o método for GET, exibir o formulário com produtos e período padrão
    return render_template('ml_result.html', 
                           resultados={'forecast': pd.DataFrame(), 'mae': None, 'fig': None},
                           selected_period=30,
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

    # Converter o DataFrame para HTML
    data_html = df.to_html(classes='table table-striped', header="true", index=False)

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

