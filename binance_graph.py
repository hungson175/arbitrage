from typing import List, Dict, Tuple
import itertools
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
