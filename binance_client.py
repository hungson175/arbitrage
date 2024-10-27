import json
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from typing import List, NamedTuple, Dict, Optional, Any
from binance_graph import BinanceGraph, EdgeAlreadyExistsError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
DEBUG_CNT = 1
RAW_TICKERS_FILE = './raw_tickers.json'

class BinanceTickerPair(NamedTuple):
    symbol: str
    priceChange: float
    priceChangePercent: float
    weightedAvgPrice: float
    prevClosePrice: float
    lastPrice: float
    lastQty: float
    bidPrice: float
    bidQty: float
    askPrice: float
    askQty: float
    openPrice: float
    highPrice: float
    lowPrice: float
    volume: float
    quoteVolume: float
    openTime: int
    closeTime: int
    firstId: int
    lastId: int
    count: int

class BinanceClient:
    def __init__(self):
        self.client = Client()
        self.symbol_info = self._load_symbol_info()

    def _load_symbol_info(self) -> Dict[str, Dict[str, str]]:
        try:
            exchange_info = self.client.get_exchange_info()
            return {symbol['symbol']: {
                'baseAsset': symbol['baseAsset'],
                'quoteAsset': symbol['quoteAsset']
            } for symbol in exchange_info['symbols']}
        except (BinanceAPIException, BinanceRequestException) as e:
            print(f"Error loading symbol info: {e}")
            return {}

    def parse_symbol(self, symbol: str) -> Optional[Dict[str, str]]:
        if symbol in self.symbol_info:
            return self.symbol_info[symbol]
        else:
            print(f"Symbol {symbol} not found")
            return None

    def get_all_trading_pairs(self) -> List[BinanceTickerPair]:
        try:
            tickers = self.client.get_ticker()
            list = []
            for ticker in tickers:
                pt = BinanceClient._parseTicker(ticker)
                if pt is not None:
                    list.append(pt)
            return list
        except BinanceAPIException as e:
            print(f"Binance API Exception: {e}")
        except BinanceRequestException as e:
            print(f"Binance Request Exception: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        return []


    def _parseTicker(ticker):
        try: 
            return BinanceTickerPair(
                symbol=ticker['symbol'],
                priceChange=float(ticker['priceChange']),
                priceChangePercent=float(ticker['priceChangePercent']),
                weightedAvgPrice=float(ticker['weightedAvgPrice']),
                prevClosePrice=float(ticker['prevClosePrice']),
                lastPrice=float(ticker['lastPrice']),
                lastQty=float(ticker['lastQty']),
                bidPrice=float(ticker['bidPrice']),
                bidQty=float(ticker['bidQty']),
                askPrice=float(ticker['askPrice']),
                askQty=float(ticker['askQty']),
                openPrice=float(ticker['openPrice']),
                highPrice=float(ticker['highPrice']),
                lowPrice=float(ticker['lowPrice']),
                volume=float(ticker['volume']),
                quoteVolume=float(ticker['quoteVolume']),
                openTime=int(ticker['openTime']),
                closeTime=int(ticker['closeTime']),
                firstId=int(ticker['firstId']),
                lastId=int(ticker['lastId']),
                count=int(ticker['count'])
            )
        except Exception as e:
            print(f"Error parsing ticker: {e}")
            return None
        
    def print_binance_sample_ticker_info(tickers, sample_size):
        print(f"Number of tickers: {len(tickers)}")
        for ticker in tickers[:sample_size]:
            print(f"Symbol: {ticker.symbol}")
            print(f"Last Price: {ticker.lastPrice}")
            print(f"Bid Price: {ticker.bidPrice}")
            print(f"Ask Price: {ticker.askPrice}")
            print(f"24h Change: {ticker.priceChangePercent}%")
            print("---")

    def get_all_listed_cryptos(self) -> List[str]:
        try:
            exchange_info = self.client.get_exchange_info()
            symbols = exchange_info['symbols']
            
            # Extract base assets (cryptocurrencies) from trading pairs
            cryptos = set()
            for symbol in symbols:
                cryptos.add(symbol['baseAsset'])
            
            # Convert set to sorted list
            return sorted(list(cryptos))
        except BinanceAPIException as e:
            print(f"Binance API Exception: {e}")
        except BinanceRequestException as e:
            print(f"Binance Request Exception: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        return []

    def is_valid_ticker(self, ticker: BinanceTickerPair) -> bool:
        return (
            ticker.lastPrice != 0 and
            ticker.bidPrice != 0 and
            ticker.askPrice != 0 and
            ticker.volume != 0 and
            ticker.count != 0
        )

    def create_weighted_graph(self, save_raw_data=False) -> BinanceGraph:
        graph = BinanceGraph()
        tickers = self.get_all_trading_pairs()
        cntDebug = 0
        
        valid_tickers = []
        
        for ticker in tickers:
            symbol_info = self.parse_symbol(ticker.symbol)
            if symbol_info is None:
                continue
            
            base_asset = symbol_info['baseAsset']
            quote_asset = symbol_info['quoteAsset']
            
            if not self.is_valid_ticker(ticker):
                cntDebug += 1
                if cntDebug <= DEBUG_CNT:
                    logger.debug(f"Skipping invalid ticker: {ticker.symbol}")
                    logger.debug(json.dumps(ticker._asdict(), indent=4))
                continue

            valid_tickers.append(ticker)

            try:
                # Add edge from base to quote (e.g., BTC to USDT)
                graph.add_edge(base_asset, quote_asset, ticker.bidPrice, direction=1)
                
                # Add edge from quote to base (e.g., USDT to BTC)
                if ticker.askPrice != 0:
                    graph.add_edge(quote_asset, base_asset, 1.0 / ticker.askPrice, direction=-1)
                    
                # print ticker ETHBTC or BTCETH
                if ticker.symbol == 'ETHBTC' or ticker.symbol == 'BTCETH':
                    logger.debug(f"Ticker info for {ticker.symbol}:")
                    logger.debug(json.dumps(ticker._asdict(), indent=4))
            except EdgeAlreadyExistsError as e:
                logger.warning(str(e))

        if save_raw_data:
            self._save_raw_tickers(valid_tickers)

        return graph

    def _save_raw_tickers(self, tickers: List[BinanceTickerPair]):
        """
        Save the raw ticker data to a JSON file.
        
        :param tickers: List of valid BinanceTickerPair objects
        """
        raw_data = [ticker._asdict() for ticker in tickers]
        
 
        with open(RAW_TICKERS_FILE, 'w') as f:
            json.dump(raw_data, f, indent=2)
        
        logger.info(f"Raw ticker data for {len(tickers)} valid tickers saved to raw_tickers.json")
        
    def get_order_book(self, symbol: str, limit: int = 100) -> Dict[str, Any]:
        return self.client.get_order_book(symbol=symbol, limit=limit)


if __name__ == "__main__":
    bc = BinanceClient()
    order_book = bc.get_order_book('BTCUSDT', 5)
    print(order_book)