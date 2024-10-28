import os
import time
import json
from binance_client import BinanceClient
from binance_graph import BinanceGraph
from typing import List

INFINITY = float('inf')
REFRESH_GRAPH_TIME = INFINITY
GRAPH_FILE = "./binance_graph.json"
RAW_TICKERS_FILE = "./raw_tickers.json"
ORDER_BOOKS_FILE = "./order_books.json"

def main():
    # bc = BinanceClient()
    # Create the weighted graph
    # graph = bc.create_weighted_graph()
    
    graph = BinanceGraph.load_from_json(GRAPH_FILE)

    
    # Print information about the graph
    # graph.print_graph_info()

    # Find triangular arbitrage opportunities starting from USDT
    # usdt_opportunities = graph.find_triangular_arbitrage("USDT", min_profit=1.001)  # 0.1% minimum profit
    # print("\nTriangular arbitrage opportunities starting from USDT:")
    # for opp in usdt_opportunities:
    #     print(f"{opp[0]} -> {opp[1]} -> {opp[2]} -> {opp[0]}: Profit = {opp[3]:.2f}%")
    #     show_arbitrage_tickers(graph, opp[:3])  # Pass the graph and the path to the new function

    # Find all triangular arbitrage opportunities
    all_opportunities = graph.find_all_triangular_arbitrage(min_profit=1.0001)  # 0.1% minimum profit
    print("\nAll triangular arbitrage opportunities:")
    for opp in all_opportunities[:10]:
        print(f"{opp[0]} -> {opp[1]} -> {opp[2]} -> {opp[0]}: Profit = {opp[3]:.2f}%")
    
    # show_arbitrage_tickers(graph, ['BTC', 'USDT', 'MXN'])

def create_graph_if_needed():
    if not os.path.exists(GRAPH_FILE) or time.time() - os.path.getmtime(GRAPH_FILE) > REFRESH_GRAPH_TIME:
        bc = BinanceClient()
        graph = bc.create_weighted_graph(save_raw_data=True)
        graph.save_to_json(GRAPH_FILE)

def show_arbitrage_tickers(graph: BinanceGraph, path: List[str]):
    with open(RAW_TICKERS_FILE, 'r') as f:
        raw_tickers = json.load(f)
    
    ticker_dict = {ticker['symbol']: ticker for ticker in raw_tickers}
    
    print(f"\nArbitrage path: {' -> '.join(path)}")
    for i in range(len(path)):
        from_currency = path[i]
        to_currency = path[(i + 1) % len(path)]
        
        symbol = f"{from_currency}{to_currency}"
        reverse_symbol = f"{to_currency}{from_currency}"
        
        # Print the graph edge value
        if to_currency in graph.edges[from_currency]:
            graph_weight = graph.edges[from_currency][to_currency]
            print(f"Graph edge {from_currency} -> {to_currency}: {graph_weight:.8f}")
        else:
            print(f"No edge found in graph for {from_currency} -> {to_currency}")
        
        # Print the ticker information
        if symbol in ticker_dict:
            ticker = ticker_dict[symbol]
            print(f"Ticker {from_currency} -> {to_currency}: (Symbol: {symbol})")
            print("Original ticker: ", json.dumps(ticker, indent=2))
        elif reverse_symbol in ticker_dict:
            ticker = ticker_dict[reverse_symbol]
            print(f"Ticker {from_currency} -> {to_currency}: (Symbol: {reverse_symbol}, reversed)")
            print("Original ticker: ", json.dumps(ticker, indent=2))
        else:
            print(f"No ticker found for {from_currency} -> {to_currency}")
        
        print()  # Add a blank line for readability

# if __name__ == "__main__":
#     create_graph_if_needed()
def debug_depth():
        # Initialize clients
    bc = BinanceClient()
    graph = BinanceGraph.load_from_json(GRAPH_FILE)
    
    # Example path
    # path = ['USDT', 'BTC', 'ETH', 'USDT']
    # path = ['USDT', 'ETH', 'PLN', 'USDT']
    path = ['USDT', 'BNB', 'ENA', 'USDT']
    initial_amount = 100  # 10000 USDT
    
    # Get and save order books
    order_books = bc.get_order_books_for_path(path, limit=100, file_path=ORDER_BOOKS_FILE)  # This will save to order_books.json
    
    # if not order_books:
    #     print("Failed to fetch order books")
    #     exit(1)
    
    # For debugging: Load from file
    loaded_data = bc.load_order_books(ORDER_BOOKS_FILE)
    if loaded_data:
        print("\nLoaded order books data:")
        print(f"Path: {loaded_data['path']}")
        print("\nOrder Books:")
        for symbol, book in loaded_data['order_books'].items():
            print(f"\n{symbol}:")
            print("Top 3 Bids:", book['bids'][:3])
            print("Top 3 Asks:", book['asks'][:3])
        
        # Calculate PnL using loaded order books
        pnl = graph.compute_pnl_arbitrage(path=path, amount=initial_amount, order_books=loaded_data['order_books'])
        print(f"\nExpected PnL: {pnl}%")

def find_profitable_arbitrage():
    """
    find all triangular arbitrage opportunities
    then try to compute pnl for each one
    """
    bc = BinanceClient()
    graph = bc.create_weighted_graph()
    opportunities = graph.find_all_triangular_arbitrage(min_profit=1.0001)
    for opp in opportunities:
        # print(f"{opp[0]} -> {opp[1]} -> {opp[2]} -> {opp[0]}: Profit = {opp[3]:.2f}%")
        # print(opp)
        # create a path with the last currency added to the beginning
        path = [*opp[:3], opp[0]]
        print("Path: ", path)
        print("Type of path: ", type(path))
        
        pnl = graph.compute_pnl_arbitrage(
            path=opp[:3]+opp[:0], 
            amount=1000, 
            order_books=bc.get_order_books_for_path([*opp[:3],opp[0]], limit=100, file_path=None))
        time.sleep(0.3)
        if pnl > 0:
            print("Opportunity found: ", opp[:3])
            print(f"PnL: {pnl}%")

if __name__ == "__main__":
    # debug_depth()
    find_profitable_arbitrage()

