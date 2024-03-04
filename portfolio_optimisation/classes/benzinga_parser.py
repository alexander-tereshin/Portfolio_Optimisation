import concurrent.futures
import warnings
from typing import List, Optional
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
import pandas as pd
from benzinga import news_data
import ast
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

class BenzingaNewsParser:
    def __init__(
        self,
        api_key: str,
        tickers: List[str],
        start_date: str,
        end_date: str,
        log: bool = False,
    ):
        self.paper = news_data.News(api_key, log=log)
        self.tickers = tickers
        self.start_date = start_date
        self.end_date = end_date
        self.main_df = pd.DataFrame()

    @staticmethod
    def remove_html_tags(text: str) -> str:
        soup = BeautifulSoup(text, "html.parser")
        return soup.get_text()

    def get_ticker_news(self, ticker: str, page: int) -> Optional[pd.DataFrame]:
        if not isinstance(ticker, str):
            ticker = ",".join(ticker)
        news = self.paper.news(
            company_tickers=ticker,
            display_output="full",
            date_from=self.start_date,
            date_to=self.end_date,
            page=page,
            pagesize=100,
        )
        if len(news) == 0:
            return None
        df = pd.DataFrame(news)
        df["teaser"] = df["teaser"].apply(self.remove_html_tags)
        df["body"] = df["body"].apply(self.remove_html_tags)
        return df


    def get_df_news(self) -> pd.DataFrame:
        if self.main_df is None:
            self.run_concurrent()
        
        return self.main_df

    def save_dataset(self, filename: str = "datasets/news_sp_500.csv") -> None:
        self.main_df.to_csv(filename, index=False)

    def run_concurrent(self, max_workers: int = 10) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(self.get_ticker_news, ticker, 0)
                for ticker in self.tickers
            ]
            for future in concurrent.futures.as_completed(futures):
                news_df = future.result()
                if news_df is not None:
                    news_df["stocks"] = news_df["stocks"].apply(eval).apply(lambda x: [entry["name"] for entry in x])
                    news_df = news_df.explode("stocks")
                    news_df["updated"] = pd.to_datetime(news_df["updated"]).dt.tz_localize(None).dt.date

                    self.main_df = pd.concat([self.main_df, news_df], ignore_index=True)
                    self.main_df = self.main_df.drop_duplicates(subset=["id"])
