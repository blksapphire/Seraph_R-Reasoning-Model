import requests
from transformers import pipeline
import logging

class FundamentalAnalyzer:
    def __init__(self, config):
        self.config = config['fundamental_parameters']
        self.api_key = self.config.get('news_api_key')
        self.sentiment_pipeline = None
        if self.api_key and self.api_key != "YOUR_NEWSAPI_KEY":
            try:
                model_name = self.config['news_sentiment_model']
                self.sentiment_pipeline = pipeline('sentiment-analysis', model=model_name)
                logging.info(f"Sentiment analysis model '{model_name}' loaded.")
            except Exception as e:
                logging.error(f"Failed to load NLP model. FA will be disabled. Error: {e}")

    def get_news_sentiment_for_pair(self, symbol: str) -> dict:
        if not self.sentiment_pipeline:
            return {'score': 0, 'narrative': 'Fundamental analysis disabled (no API key or model).'}
        
        base_curr, quote_curr = symbol[:3], symbol[3:]
        base_score, base_count = self._get_sentiment_for_currency(base_curr)
        quote_score, quote_count = self._get_sentiment_for_currency(quote_curr)

        base_avg = base_score / base_count if base_count > 0 else 0
        quote_avg = quote_score / quote_count if quote_count > 0 else 0
        
        # If base is bullish (positive score) and quote is bearish (negative score), overall is strongly bullish
        final_score = base_avg - quote_avg
        narrative = f"{base_curr} sentiment score: {base_avg:.2f}; {quote_curr} score: {quote_avg:.2f}."
        
        return {'score': max(-1.0, min(1.0, final_score)), 'narrative': narrative}

    def _get_sentiment_for_currency(self, currency: str):
        total_score, article_count = 0, 0
        if currency not in self.config['currencies_of_interest']:
            return 0, 0
        
        try:
            url = f"https://newsapi.org/v2/everything?q={currency}&apiKey={self.api_key}&language=en&sortBy=publishedAt&pageSize=10"
            response = requests.get(url)
            response.raise_for_status()
            articles = response.json().get('articles', [])
            
            for article in articles:
                sentiment = self.sentiment_pipeline(article['title'])[0]
                if sentiment['label'] == 'positive': total_score += sentiment['score']
                elif sentiment['label'] == 'negative': total_score -= sentiment['score']
                article_count += 1
        except requests.exceptions.RequestException as e:
            logging.error(f"News API request failed for {currency}: {e}")
        
        return total_score, article_count