from typing import List, Dict, Tuple
import json


class EdgeAlreadyExistsError(Exception):
    """Exception raised when trying to add an edge that already exists."""
    pass

class BinanceGraph:
    def __init__(self):
        self.nodes: List[str] = []
        self.edges: Dict[str, Dict[str, Tuple[float, int]]] = {}

    def add_node(self, node: str):
        if node not in self.nodes:
            self.nodes.append(node)
            self.edges[node] = {}

    def add_edge(self, from_node: str, to_node: str, weight: float, direction: int):
        self.add_node(from_node)
        self.add_node(to_node)
        
        # Check if the edge already exists
        if to_node in self.edges[from_node]:
            existing_weight, existing_direction = self.edges[from_node][to_node]
            raise EdgeAlreadyExistsError(
                f"Edge from {from_node} to {to_node} already exists. "
                f"Existing weight: {existing_weight}, direction: {existing_direction}, "
                f"New weight: {weight}, direction: {direction}"
            )
        
        # If the edge doesn't exist, add it
        self.edges[from_node][to_node] = (weight, direction)

    def print_graph_info(self):
        print(f"Number of nodes: {len(self.nodes)}")
        print(f"Number of edges: {sum(len(edges) for edges in self.edges.values())}")
        print("\nSample of edges:")
        for i, (from_node, edge_dict) in enumerate(self.edges.items()):
            cntEdges = 0
            for to_node, (weight, direction) in edge_dict.items():
                cntEdges += 1
                print(f"{from_node} -> {to_node}: weight = {weight}, direction = {direction}")
                if cntEdges >= 5:
                    break # print only 5 sample edges
            if i >= 4:  # Print only 5 sample nodes
                break

    def find_triangular_arbitrage(self, start_currency: str, min_profit: float = 1.0) -> List[Tuple[str, str, str, float]]:
        opportunities = []

        for mid_currency in self.edges.get(start_currency, {}):
            for end_currency in self.edges.get(mid_currency, {}):
                if end_currency in self.edges.get(start_currency, {}) and end_currency != start_currency:
                    # Calculate the total exchange rate
                    rate1, dir1 = self.edges[start_currency][mid_currency]
                    rate2, dir2 = self.edges[mid_currency][end_currency]
                    rate3, dir3 = self.edges[end_currency][start_currency]
                    
                    total_rate = rate1 * rate2 * rate3
                    
                    # If the total rate is greater than 1, there's a potential arbitrage opportunity
                    if total_rate > min_profit:
                        profit_percentage = (total_rate - 1) * 100
                        opportunities.append((start_currency, mid_currency, end_currency, profit_percentage))

        return opportunities

    def find_all_triangular_arbitrage(self, min_profit: float = 1.0) -> List[Tuple[str, str, str, float]]:
        all_opportunities = []
        for start_currency in self.nodes:
            opportunities = self.find_triangular_arbitrage(start_currency, min_profit)
            all_opportunities.extend(opportunities)
        # sort the opportunities by profit percentage
        all_opportunities.sort(key=lambda x: x[3], reverse=True)
        return all_opportunities
    
    def compute_pnl_arbitrage(self, path: List[str], amount: float, order_books: Dict[str, Dict]) -> float:
        """
        Compute the PnL of an arbitrage opportunity considering order book depth.
        
        Args:
            path: List of currencies in the arbitrage path (e.g., ['USDT', 'BTC', 'ETH', 'USDT'])
            amount: Initial amount of the first currency
            order_books: Dictionary mapping trading pairs to their order book data
        
        Returns:
            float: Profit/Loss percentage
        """
        current_amount = amount

        # Process each pair of currencies in the path
        for i in range(len(path) - 1):
            from_currency = path[i]
            to_currency = path[i + 1]
            
            # Get the edge details and determine symbol
            _, direction = self.edges[from_currency][to_currency]
            symbol = self._determine_symbol(from_currency, to_currency, direction)
            # print(f"Computing depth for symbol: {symbol}")
            
            # Execute the trade using order book
            current_amount = self._execute_trade_with_orderbook(
                symbol=symbol,
                direction=direction,
                amount=current_amount,
                order_book=order_books.get(symbol),
            )
            
            if current_amount <= 0:
                return 0.0  # Insufficient liquidity
        
        # Return the profit/loss percentage
        return (current_amount / amount - 1.0) * 100

    def _determine_symbol(self, from_currency: str, to_currency: str, direction: int) -> str:
        """
        Determine the correct symbol format based on the trade direction.
        
        Args:
            from_currency: Starting currency
            to_currency: Target currency
            direction: 1 for selling base currency, -1 for buying base currency
        
        Returns:
            str: Properly formatted symbol (e.g., 'BTCUSDT')
        """
        base_quote_pair = f"{from_currency}{to_currency}"
        quote_base_pair = f"{to_currency}{from_currency}"
        return base_quote_pair if direction == 1 else quote_base_pair

    def _execute_trade_with_orderbook(
        self,
        symbol: str,
        direction: int,
        amount: float,
        order_book: Dict,
    ) -> float:
        """
        Execute a trade using the order book data.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            direction: 1 for selling base currency, -1 for buying base currency
            amount: Amount of from_currency to trade
            order_book: Order book data for the symbol
        
        Returns:
            float: Amount of to_currency received
        """
        if not order_book:
            return -1
            # raise ValueError(f"Order book not found for symbol {symbol}")
        
        # Use bids if selling (direction = 1), asks if buying (direction = -1)
        orders = order_book['bids'] if direction == 1 else order_book['asks']
        
        # Pre-process orders based on direction
        processed_orders = []
        for price_str, qty_str in orders:
            price = float(price_str)
            qty = float(qty_str)
            if direction == 1:  # Selling base currency
                processed_orders.append((price, qty))  # Direct conversion rate
            else:  # Buying base currency
                processed_orders.append((1/price, qty*price))  # Inverse rate and adjusted quantity
                
        return self._process_orders(processed_orders, amount)

    def _process_orders(self, processed_orders: List[Tuple[float, float]], amount: float) -> float:
        """
        Process pre-processed orders to calculate the final amount.
        
        Args:
            processed_orders: List of (conversion_rate, available_amount) pairs
            amount: Amount to trade
        
        Returns:
            float: Amount received after the trade
        """
        remaining_amount = amount
        new_amount = 0.0
        
        for conversion_rate, available_amt in processed_orders:
            executable_amt = min(remaining_amount, available_amt)
            new_amount += executable_amt * conversion_rate
            remaining_amount -= executable_amt
            
            if remaining_amount <= 0:
                return new_amount
        
        # If we get here, there wasn't enough liquidity
        return 0.0

    def save_to_json(self, filename: str):
        """
        Save the graph to a JSON file.
        
        :param filename: The name of the file to save the graph to.
        """
        graph_data = {
            "nodes": self.nodes,
            "edges": {from_node: {to_node: {"weight": weight, "direction": direction} 
                                  for to_node, (weight, direction) in edges.items()} 
                      for from_node, edges in self.edges.items()}
        }
        
        with open(filename, 'w') as f:
            json.dump(graph_data, f, indent=2)
        
        print(f"Graph saved to {filename}")

    @classmethod
    def load_from_json(cls, filename: str):
        """
        Load a graph from a JSON file.
        
        :param filename: The name of the file to load the graph from.
        :return: A new BinanceGraph instance with the loaded data.
        """
        with open(filename, 'r') as f:
            graph_data = json.load(f)
        
        graph = cls()
        graph.nodes = graph_data["nodes"]
        graph.edges = {from_node: {to_node: (edge_data["weight"], edge_data["direction"]) 
                                   for to_node, edge_data in edges.items()} 
                       for from_node, edges in graph_data["edges"].items()}
        
        print(f"Graph loaded from {filename}")
        return graph




