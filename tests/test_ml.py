# test_ml.py
import pytest
import pandas as pd
from sqlalchemy import create_engine
from ml import perform_machine_learning

# Configuração do SQLite para teste
@pytest.fixture(scope="module")
def setup_database():
    # Cria um banco de dados SQLite em memória
    engine = create_engine("sqlite:///:memory:")

    # Dados fictícios para o teste
    data = {
        'produto': ['ProdutoX'] * 24,
        'data': pd.date_range(start='2022-01-01', periods=24, freq='M'),
        'quantidade_vendida': [100 + i * 10 for i in range(24)],
        # Formato de string para 'preco' para simular a entrada esperada
        'preco': [f'{5.0 + (i % 3) * 0.5:.2f}' for i in range(24)]  # Convertendo para string com duas casas decimais
    }

    # Cria DataFrame e insere no banco de dados
    df = pd.DataFrame(data)
    df.to_sql('ProdutosSustentaveis', engine, index=False, if_exists='replace')
    return engine

# Teste principal
def test_perform_machine_learning(setup_database):
    engine = setup_database
    produto = 'ProdutoX'

    # Executa a função com dados de teste
    result = perform_machine_learning(engine, produto, period=12)

    # Verificações das saídas
    assert 'image_path' in result, "A chave 'image_path' está ausente no resultado."
    assert 'forecast' in result, "A chave 'forecast' está ausente no resultado."
    assert 'mae_quantity' in result, "A chave 'mae_quantity' está ausente no resultado."
    assert 'mae_price' in result, "A chave 'mae_price' está ausente no resultado."

    # Verifica se o DataFrame de previsão tem o número de períodos correto
    assert len(result['forecast']) == 12, "O DataFrame de previsão não tem o número correto de períodos."
    assert not result['forecast'].empty, "O DataFrame de previsão está vazio."

    # Verifica se os valores de MAE estão no formato correto
    assert isinstance(result['mae_quantity'], float), "MAE para quantidade não é do tipo float."
    assert isinstance(result['mae_price'], float), "MAE para preço não é do tipo float."
