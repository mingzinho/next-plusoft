from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
from sklearn.preprocessing import StandardScaler
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from datetime import datetime

matplotlib.use('Agg')  # Uso do backend 'Agg' para ambientes sem interface gráfica

# Diretório para salvar imagens temporárias
TEMP_IMAGE_DIR = './static/images'

def perform_machine_learning(engine, produto, period=12):
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

    # Resample para média mensal
    df = df.set_index('data').resample('M').mean().interpolate()

    # Adicionar variáveis "lag" e outras features temporais
    df['preco_lag1'] = df['preco'].shift(1)
    df['preco_lag2'] = df['preco'].shift(2)  # Preço de dois meses atrás
    df = df.dropna()

    df['year'] = df.index.year
    df['month'] = df.index.month

    X = df[['year', 'month', 'preco_lag1', 'preco_lag2']]
    y = df['preco']

    # Validação cruzada temporal para evitar overfitting em dados passados
    tscv = TimeSeriesSplit(n_splits=5)
    model = RandomForestRegressor(n_estimators=100, random_state=42)
    mae_scores = []

    for train_index, test_index in tscv.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y.iloc[train_index], y.iloc[test_index]

        # Normalizar os dados
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)

        model.fit(X_train_scaled, y_train)
        y_pred = model.predict(X_test_scaled)
        mae_scores.append(mean_absolute_error(y_test, y_pred))

    # Média dos MAEs da validação cruzada
    mae = np.mean(mae_scores)

    # Prever preços futuros
    future_months = np.arange(len(df), len(df) + period)
    future_years = [(df.index[-1] + pd.DateOffset(months=i)).year for i in range(1, period + 1)]
    future_months_only = [(df.index[-1] + pd.DateOffset(months=i)).month for i in range(1, period + 1)]

    last_price_lag1 = df['preco'].iloc[-1]
    last_price_lag2 = df['preco_lag1'].iloc[-1]

    future_lagged_prices = [last_price_lag1, last_price_lag2]

    # Prever os preços futuros iterativamente
    future_prices = []
    for i in range(period):
        future_features = [[future_years[i], future_months_only[i], future_lagged_prices[-1], future_lagged_prices[-2]]]
        future_features_scaled = scaler.transform(future_features)
        pred_price = model.predict(future_features_scaled)[0]
        future_prices.append(pred_price)
        future_lagged_prices.append(pred_price)

    # Plotar o resultado
    fig, ax = plt.subplots()
    ax.plot(df.index, df['preco'], label='Histórico de Preços')
    future_dates = pd.date_range(df.index[-1] + pd.DateOffset(months=1), periods=period, freq='M')
    ax.plot(future_dates, future_prices, label='Previsão', linestyle='--')
    plt.title('Previsão de Preços (Média Mensal)')
    plt.xlabel('Data')
    plt.ylabel('Preço Médio')
    plt.legend()

    # Salvar o gráfico como imagem em um diretório temporário
    if not os.path.exists(TEMP_IMAGE_DIR):
        os.makedirs(TEMP_IMAGE_DIR)
    
    image_path = f'static/images/forecast_{produto}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    plt.savefig(image_path)
    plt.close(fig)

    # Criar DataFrame com previsões
    forecast_df = pd.DataFrame({'Data': future_dates, 'Previsão': np.round(future_prices, 2)})

    # Retornar o caminho da imagem e outras informações
    return {
        'image_path': image_path,  # Caminho da imagem salva
        'forecast': forecast_df,
        'mae': round(mae, 2)
    }
