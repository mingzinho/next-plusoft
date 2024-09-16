import requests
from bs4 import BeautifulSoup
import pandas as pd
import csv
from datetime import datetime

# Função para fazer scraping na Amazon
def scrape_amazon(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.85 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    products = soup.find_all('div', {'data-component-type': 's-search-result'})

    data = []
    current_date = datetime.now().strftime('%Y-%m-%d')

    for product in products:
        link = "https://www.amazon.com" + product.h2.a["href"]

        # Fazer uma requisição para a página do produto para pegar detalhes
        prod_response = requests.get(link, headers=headers)
        prod_soup = BeautifulSoup(prod_response.text, 'html.parser')

        name = prod_soup.find("span", id="productTitle").text.strip() if prod_soup.find("span", id="productTitle") else 'N/A'
        price = prod_soup.find("span", class_="a-price-whole").text.strip().replace(".", "").replace(",", "") if prod_soup.find("span", class_="a-price-whole") else 'N/A'
        price = int(price) if price.isdigit() else 'N/A'
        brand = prod_soup.find("a", id="bylineInfo").text.strip().replace("Visite a loja", "") if prod_soup.find("a", id="bylineInfo") else 'N/A'
        reviews = prod_soup.find("span", id="acrCustomerReviewText").text.strip().replace("avaliações de clientes", "").strip() if prod_soup.find("span", id="acrCustomerReviewText") else '0'
        rating = prod_soup.find("span", class_="a-icon-alt").text.strip().split()[0] if prod_soup.find("span", class_="a-icon-alt") else 'N/A'
        
        data.append([name, price, brand, reviews, rating, current_date])

    return data

# Função para fazer scraping no Mercado Livre
def scrape_mercadolivre(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    products = soup.find_all('li', {'class': 'ui-search-layout__item'})

    data = []
    current_date = datetime.now().strftime('%Y-%m-%d')

    for product in products:
        name = product.find('h2', {'class': 'ui-search-item__title'}).text if product.find('h2', {'class': 'ui-search-item__title'}) else 'N/A'
        price = product.find('span', {'class': 'andes-money-amount__fraction'}).text if product.find('span', {'class': 'andes-money-amount__fraction'}) else 'N/A'
        empresa = product.find('p', {'class': 'ui-search-item__group__element'})
        origem = product.find('span', {'class': 'ui-search-item__shipping'})
        avaliacao = product.find('span', {'class': 'ui-search-reviews__rating-number'})

        data.append([
            name,
            price,
            empresa.text if empresa else None,
            origem.text if origem else None,
            avaliacao.text if avaliacao else None,
            current_date
        ])
    
    return data

# Função para salvar os dados em CSV
def save_to_csv(data, filename):
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Nome do Produto', 'Preço', 'Marca/Empresa', 'Avaliações', 'Classificação', 'Data'])
        writer.writerows(data)

# Exemplo de uso
def main():
    urls_amazon = [
        # Insira as URLs da Amazon aqui
    ]

    urls_mercadolivre = [
        # Insira as URLs do Mercado Livre aqui
    ]

    # Scraping e salvamento dos dados
    for url in urls_amazon:
        amazon_data = scrape_amazon(url)
        save_to_csv(amazon_data, 'amazon_products.csv')

    for url in urls_mercadolivre:
        mercadolivre_data = scrape_mercadolivre(url)
        save_to_csv(mercadolivre_data, 'mercadolivre_products.csv')

if __name__ == "__main__":
    main()
