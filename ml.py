from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
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

    if 'quantidade_vendida' not in df.columns:
        raise Exception("A coluna 'quantidade_vendida' não existe na tabela.")

    if 'preco' not in df.columns:
        raise Exception("A coluna 'preco' não existe na tabela.")

    # Preprocessar os dados
    df['preco'] = df['preco'].str.replace('.', '').str.replace(',', '.').astype(float)
    df['preco'] = np.round(df['preco'], 2)
    df['data'] = pd.to_datetime(df['data'])
    df = df[['data', 'quantidade_vendida', 'preco']]

    # Resample para total mensal de vendas e preço médio mensal
    df = df.set_index('data').resample('M').agg({'quantidade_vendida': 'sum', 'preco': 'mean'}).interpolate()

    # Adicionar variáveis "lag" para a quantidade e o preço
    df['quantidade_lag1'] = df['quantidade_vendida'].shift(1)
    df['quantidade_lag2'] = df['quantidade_vendida'].shift(2)
    df['preco_lag1'] = df['preco'].shift(1)
    df['preco_lag2'] = df['preco'].shift(2)
    df = df.dropna()

    df['year'] = df.index.year
    df['month'] = df.index.month

    # Previsão de Quantidade Vendida
    X_quantity = df[['year', 'month', 'quantidade_lag1', 'quantidade_lag2']]
    y_quantity = df['quantidade_vendida']

    # Previsão de Preço
    X_price = df[['year', 'month', 'preco_lag1', 'preco_lag2']]
    y_price = df['preco']

    # Validação cruzada temporal para ambos os modelos
    tscv = TimeSeriesSplit(n_splits=5)
    model_quantity = RandomForestRegressor(n_estimators=100, random_state=42)
    model_price = RandomForestRegressor(n_estimators=100, random_state=42)
    mae_scores_quantity = []
    mae_scores_price = []

    # Treinamento e validação cruzada para quantidade vendida
    for train_index, test_index in tscv.split(X_quantity):
        X_train_quantity, X_test_quantity = X_quantity.iloc[train_index], X_quantity.iloc[test_index]
        y_train_quantity, y_test_quantity = y_quantity.iloc[train_index], y_quantity.iloc[test_index]

        scaler_quantity = StandardScaler()
        X_train_quantity_scaled = scaler_quantity.fit_transform(X_train_quantity)
        X_test_quantity_scaled = scaler_quantity.transform(X_test_quantity)

        model_quantity.fit(X_train_quantity_scaled, y_train_quantity)
        y_pred_quantity = model_quantity.predict(X_test_quantity_scaled)
        mae_scores_quantity.append(mean_absolute_error(y_test_quantity, y_pred_quantity))

    # Treinamento e validação cruzada para preço
    for train_index, test_index in tscv.split(X_price):
        X_train_price, X_test_price = X_price.iloc[train_index], X_price.iloc[test_index]
        y_train_price, y_test_price = y_price.iloc[train_index], y_price.iloc[test_index]

        scaler_price = StandardScaler()
        X_train_price_scaled = scaler_price.fit_transform(X_train_price)
        X_test_price_scaled = scaler_price.transform(X_test_price)

        model_price.fit(X_train_price_scaled, y_train_price)
        y_pred_price = model_price.predict(X_test_price_scaled)
        mae_scores_price.append(mean_absolute_error(y_test_price, y_pred_price))

    # Média dos MAEs das validações cruzadas
    mae_quantity = np.mean(mae_scores_quantity)
    mae_price = np.mean(mae_scores_price)

    # Prever demanda e preços futuros
    future_years = [(df.index[-1] + pd.DateOffset(months=i)).year for i in range(1, period + 1)]
    future_months_only = [(df.index[-1] + pd.DateOffset(months=i)).month for i in range(1, period + 1)]

    last_quantity_lag1 = df['quantidade_vendida'].iloc[-1]
    last_quantity_lag2 = df['quantidade_lag1'].iloc[-1]
    last_price_lag1 = df['preco'].iloc[-1]
    last_price_lag2 = df['preco_lag1'].iloc[-1]

    future_lagged_quantities = [last_quantity_lag1, last_quantity_lag2]
    future_lagged_prices = [last_price_lag1, last_price_lag2]

    future_quantities = []
    future_prices = []

    # Previsão iterativa de demanda e preços
    for i in range(period):
        # Previsão de quantidade vendida
        future_features_quantity = [[future_years[i], future_months_only[i], future_lagged_quantities[-1], future_lagged_quantities[-2]]]
        future_features_quantity_scaled = scaler_quantity.transform(future_features_quantity)
        pred_quantity = model_quantity.predict(future_features_quantity_scaled)[0]
        future_quantities.append(pred_quantity)
        future_lagged_quantities.append(pred_quantity)

        # Previsão de preço
        future_features_price = [[future_years[i], future_months_only[i], future_lagged_prices[-1], future_lagged_prices[-2]]]
        future_features_price_scaled = scaler_price.transform(future_features_price)
        pred_price = model_price.predict(future_features_price_scaled)[0]
        future_prices.append(pred_price)
        future_lagged_prices.append(pred_price)

    # Plotar o resultado
    fig, ax = plt.subplots(2, 1, figsize=(10, 8))

    # Previsão de Quantidade Vendida
    ax[0].plot(df.index, df['quantidade_vendida'], label='Histórico de Quantidade Vendida')
    future_dates = pd.date_range(df.index[-1] + pd.DateOffset(months=1), periods=period, freq='M')
    ax[0].plot(future_dates, future_quantities, label='Previsão de Quantidade', linestyle='--')
    ax[0].set_title('Previsão de Demanda (Mensal)')
    ax[0].set_xlabel('Data')
    ax[0].set_ylabel('Quantidade Vendida')
    ax[0].legend()

    # Previsão de Preço
    ax[1].plot(df.index, df['preco'], label='Histórico de Preço')
    ax[1].plot(future_dates, future_prices, label='Previsão de Preço', linestyle='--')
    ax[1].set_title('Previsão de Preço (Média Mensal)')
    ax[1].set_xlabel('Data')
    ax[1].set_ylabel('Preço Médio')
    ax[1].legend()

    # Salvar o gráfico como imagem em um diretório temporário
    if not os.path.exists(TEMP_IMAGE_DIR):
        os.makedirs(TEMP_IMAGE_DIR)

    image_path = f'static/images/forecast_{produto}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    plt.tight_layout()
    plt.savefig(image_path)
    plt.close(fig)

    # Criar DataFrame com previsões
    forecast_df = pd.DataFrame({
        'Data': future_dates,
        'Previsão de Quantidade': np.round(future_quantities, 2),
        'Previsão de Preço': np.round(future_prices, 2)
    })

    # Retornar o caminho da imagem e outras informações
    return {
        'image_path': image_path,  # Caminho da imagem salva
        'forecast': forecast_df,
        'mae_quantity': round(mae_quantity, 2),
        'mae_price': round(mae_price, 2)
    }
