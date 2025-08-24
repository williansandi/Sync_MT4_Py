# ui/components/news_scraper.py

import urllib.request
from bs4 import BeautifulSoup
from datetime import datetime
from tabulate import tabulate
import logging

def fetch_structured_news():
    """Busca as notícias e retorna uma lista de dicionários estruturados."""
    url = 'https://br.investing.com/economic-calendar/'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    news_list = []
    
    try:
        with urllib.request.urlopen(req) as response:
            soup = BeautifulSoup(response.read(), "html.parser")
            table = soup.find('table', {"id": "economicCalendarData"})
            if not table:
                logging.warning("Tabela de notícias não encontrada no site Investing.com.")
                return []
            
            for tr in table.find("tbody").findAll('tr', {"class": "js-event-item"}):
                try:
                    time_str = datetime.strptime(tr.attrs.get('data-event-datetime', ''), '%Y/%m/%d %H:%M:%S').strftime("%H:%M")
                    currency = tr.find('td', {"class": "flagCur"}).text.strip()
                    impact_tag = tr.find('td', {"class": "sentiment"})
                    impact = len(impact_tag.findAll("i", {"class": "grayFullBullishIcon"})) if impact_tag else 0
                    event_name = tr.find('td', class_="event").text.strip()
                    
                    if impact >= 2: # Apenas notícias de 2 ou 3 touros
                        news_list.append({
                            "time": time_str,
                            "currency": currency,
                            "impact": impact,
                            "event": event_name
                        })
                except Exception:
                    # Ignora linhas mal formatadas ou sem todos os dados
                    continue 
    except Exception as e:
        logging.error(f"Ocorreu um erro ao buscar notícias estruturadas: {e}")
        return []
        
    return news_list

def get_formatted_news():
    """Usa os dados estruturados para criar uma tabela de texto formatada para a UI."""
    structured_news = fetch_structured_news()
    if not structured_news:
        return "Nenhuma notícia de impacto encontrada ou falha na conexão."
        
    display_data = []
    for news in structured_news:
        display_data.append([news['time'], "★" * news['impact'], news['currency'], news['event']])
        
    return tabulate(display_data, headers=['HORA', "IMPACTO", "MOEDA", "EVENTO"], tablefmt="grid")