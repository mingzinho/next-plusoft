from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler
import matplotlib
matplotlib.use('Agg')  # Uso do backend 'Agg' para ambientes sem interface gráfica
import matplotlib.pyplot as plt
import io
import os
import pandas as pd
import numpy as np
from datetime import datetime
# from azure.storage.blob import BlobServiceClient  # Descomentar se for usar o Azure Blob Storage

def perform_machine_learning(engine, produto, period=30):
    # Carregar os dados do produto específico
    query = f"SELECT * FROM ProdutosSustentaveis WHERE produto = '{produto}'"
    df = pd.read_sql_query(query, engine)

    if df.empty:
        raise Exception(f"Nenhum dado encontrado para o produto: {produto}")

    if 'preco' not in df.columns:
        raise Exception("A coluna 'preço' não existe na tabela.")

    # Preprocessar os dados
    df['preco'] = df['preco'].str.replace('.', '').str.replace(',', '.').astype(float)
    df['preco'] = np.round(df['preco'], 2)
    df['data'] = pd.to_datetime(df['data'])
    df = df[['data', 'preco']]
    df = df.set_index('data').resample('D').mean().interpolate()

    # Adicionar features temporais
    df['days'] = np.arange(len(df))
    df['month'] = df.index.month
    df['day_of_week'] = df.index.dayofweek

    # Variáveis independentes
    X = df[['days', 'month', 'day_of_week']]
    y = df['preco']

    # Dividir os dados em conjuntos de treino e teste
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Normalizar os dados
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Treinar o modelo com RandomForest
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train_scaled, y_train)

    # Prever os preços no conjunto de teste
    y_pred = model.predict(X_test_scaled)

    # Calcular o erro médio absoluto (MAE)
    mae = mean_absolute_error(y_test, y_pred)

    # Fazer previsões para o futuro
    future_days = np.arange(len(df), len(df) + period)
    future_months = [(df.index[-1] + pd.Timedelta(days=i)).month for i in range(1, period + 1)]
    future_dow = [(df.index[-1] + pd.Timedelta(days=i)).dayofweek for i in range(1, period + 1)]
    future_features = np.column_stack((future_days, future_months, future_dow))

    # Escalar os dados futuros
    future_features_scaled = scaler.transform(future_features)

    # Fazer previsões para o período especificado
    forecast = model.predict(future_features_scaled)
    forecast = np.round(forecast, 2)

    # Plotar o resultado
    fig, ax = plt.subplots()
    ax.plot(df.index, df['preco'], label='Histórico de Preços')
    future_dates = pd.date_range(df.index[-1], periods=period + 1, freq='D')[1:]
    ax.plot(future_dates, forecast, label='Previsão', linestyle='--')
    plt.title('Previsão de Preços')
    plt.xlabel('Data')
    plt.ylabel('Preço')
    plt.legend()

    # Criar o diretório, se não existir (usando o diretório permitido pelo Azure)
    output_dir = '/home/static/'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Gerar um nome de arquivo único com timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_name = f'ml_plot_{timestamp}.png'
    file_path = os.path.join(output_dir, file_name)

    # Salvar o gráfico no caminho permitido no Azure
    try:
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        with open(file_path, 'wb') as f:
            f.write(buf.getvalue())
    except Exception as e:
        raise Exception(f"Erro ao salvar a imagem: {e}")

    # Criar DataFrame com previsões
    forecast_df = pd.DataFrame({'Data': future_dates, 'Previsão': forecast})

    # Fechar a figura para liberar recursos
    plt.close(fig)

    return {
        'fig': file_name,
        'forecast': forecast_df,
        'mae': round(mae, 2)
    }

# Função para upload no Azure Blob Storage (opcional, descomentar se for usar)
"""
def upload_to_blob(file_path, blob_name):
    # Conectar ao serviço de Blob Storage
    blob_service_client = BlobServiceClient.from_connection_string('AZURE_STORAGE_CONNECTION_STRING')
    container_client = blob_service_client.get_container_client('meu-container')

    # Fazer upload do arquivo
    with open(file_path, "rb") as data:
        container_client.upload_blob(name=blob_name, data=data, overwrite=True)

# Exemplo de uso
# upload_to_blob(file_path, file_name)
"""
