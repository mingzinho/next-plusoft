from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler
import matplotlib
import matplotlib.pyplot as plt
import io
import pandas as pd
import numpy as np
from datetime import datetime


matplotlib.use('Agg')  # Uso do backend 'Agg' para ambientes sem interface gráfica
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

    # Transformar future_features em DataFrame para manter os nomes das colunas
    future_features_df = pd.DataFrame(future_features, columns=['days', 'month', 'day_of_week'])

    # Escalar os dados futuros
    future_features_scaled = scaler.transform(future_features_df)

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

    # Salvar o gráfico no buffer de memória (em vez de arquivo)
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)  # Resetar o ponteiro do buffer para o início

    # Fechar a figura para liberar recursos
    plt.close(fig)

    # Criar DataFrame com previsões
    forecast_df = pd.DataFrame({'Data': future_dates, 'Previsão': forecast})

    # Retornar o buffer contendo a imagem e outras informações
    return {
        'image_buffer': buf,  # Buffer contendo a imagem gerada
        'forecast': forecast_df,
        'mae': round(mae, 2)
    }
