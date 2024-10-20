import itertools
import logging
import networkx as nx

logger = logging.getLogger(__name__)

class LogicPuzzle:
    def __init__(self, categories):
        self._items = categories
        self._all_items = []
        for v in categories.values():
            self._all_items += v
        
        self._G = nx.Graph()
        for k, v in categories.items():
            self._G.add_nodes_from(v, label=k)
        
        # Add edges
        lists = [v for v in categories.values()]
        
        # Add edges between nodes from different lists, but no edges within the same list
        for i, list1 in enumerate(lists):
            for j, list2 in enumerate(lists):
                if i < j:  # To avoid edges within the same list and duplicating edges
                    for node1, node2 in itertools.product(list1, list2):
                        self._G.add_edge(node1, node2)

        self._rules = []

    @property
    def edge_count(self):
        return self._G.number_of_edges()

    def mark_false(self, node1, node2) -> bool:
        assert node1 in self._all_items
        assert node2 in self._all_items
        try:
            self._G.remove_edge(node1, node2)
            print(f"Removed {node1}<->{node2}")
            return True
        except nx.NetworkXError:
            return False

    def add_rule(self, fxn):
        self._rules.append(fxn)

    def execute_rules(self):
        current_edge_count = 1e9
        while current_edge_count > self.edge_count:
            current_edge_count = self.edge_count
            
            print("--- Begin Rules ---")
            print(f"--- Edges: {self.edge_count}")
            for i, f in enumerate(self._rules):
                print(f"+ Rule {i+1}")
                f(self)

            print(f"---- Edges: {self.edge_count}")
            print("---- End Rules ----")
            self._reduce_graph()

        print(f"\nEdges: {self.edge_count}")

    def _reduce_graph(self):
        for t, vs in self._items.items():
            for v in vs:
                for ot in self._items.keys():
                    if ot == t:
                        continue
                    # print(f"Checking {v} for {ot} edges")
                    if self._has_one_edge(v, ot):
                        n1 = v
                        n2 = self.neighbors(v, ot)[0]
                        print(f"{n1} has a single '{ot}' edge with {n2}")
                        assert n1 in self._items[t]
                        assert n2 in self._items[ot]
                        self.mark_true(n1, n2)
                        self._share_info(n1, n2)

    def _category(self, node):
        for category, values in self._items.items():
            if node in values:
                return category

    def neighbors(self, node, category = None):
        if category:
            assert node not in self._items[category]
            return [node for node in self._G.adj[node] if node in self._items[category]]
        else:
            return [node for node in self._G.neighbors(node)]

    def neighbors_by_type(self, node):
        this_category = self._category(node)
        adj = {}  # A dictionary of adjacent nodes by type
        for category in self._items.keys():
            if category == this_category:
                continue
            adj[category] = self.neighbors(node, category)
        return adj

    def count_edges_per_type(self, node):
        adj = self.neighbors_by_type(node)
        return { k : len(v) for k,v in adj.items()}

    def _has_one_edge(self, node, category):
        # print(f"Checking edge count on {node} of type '{category}'")
        count = self.count_edges_per_type(node)
        # For debugging purposes - hopefully this is never hit
        if count[category] == 0:
            print(node, self.neighbors_by_type(node))
        assert count[category] != 0
        return count[category] == 1

    def _share_info(self, node1, node2):
        print(f"Sharing info between {node1} & {node2}")
        node1_type = self._category(node1)
        node2_type = self._category(node2)
        # for the categories that aren't this category, we want to get neighbors,
        # find the symmetric difference, and eliminate those edges from each other
        for t in self._items.keys():
            if t == node1_type:
                unique_v_of_t = set([node1]).symmetric_difference(self.neighbors(node2, t))
            elif t == node2_type:
                unique_v_of_t = set(self.neighbors(node1, t)).symmetric_difference([node2])
            else:
                unique_v_of_t = set(self.neighbors(node1, t)).symmetric_difference(self.neighbors(node2, t))
            # print(f"unique '{t}' values: ", unique_v_of_t)
            for v in unique_v_of_t:
                if t != node1_type:
                    self.mark_false(node1, v)
                if t != node2_type:
                    self.mark_false(node2, v)

    def mark_true(self, node1, node2):
        # There's a guaranteed edge between node1 and node2
        # Eliminate all type(node1) edges that are not node1 from node2
        # Eliminate all type(node2) edges that are not node2 from node1
        type1 = self._category(node1)
        type2 = self._category(node2)
        assert node1 in self._items[type1]
        assert node2 in self._items[type2]
        not_node1 = set(self._items[type1]).difference([node1])
        # print(f"'{type1}' node: {node1}, not node: {not_node1}")
        for n in not_node1:
            self.mark_false(n, node2)
        not_node2 = set(self._items[type2]).difference([node2])
        # print(f"'{type2}' node: {node2}, not node: {not_node2}")
        for n in not_node2:
            self.mark_false(n, node1)


# A collection of logical blocks often found in a logic puzzle:
def either_or(graph, obj, pair):
    # Example:
    #   node1 == (node2 ^ node3)
    # If node1 only has the node2 edge, then it can't have the node3 edge
    # If node1 only has the node3 edge, then it can't have the node2 edge
    # Also:
    # If node2 has only one edge to type(node1) and not node1, then
    #   node3 belongs to node1. All other edges of type(node3) can be removed
    # If node3 has only one edge to type(node1) and not node1, then
    #   node2 belongs to node1. All other edges of type(node2) can be removed

    assert len(pair) == 2
    obj_adj = graph.neighbors_by_type(obj)
    obj_type = graph._category(obj)
    p1, p2 = pair
    p1_adj = graph.neighbors_by_type(p1)
    p1_type = graph._category(p1)
    p2_adj = graph.neighbors_by_type(p2)
    p2_type = graph._category(p2)
    
    # Check if p1 is a neighbor of obj. If not, then p2 belongs to obj.
    # Remove all edges that are not p2 of type(p2) from obj
    if p1 not in obj_adj[p1_type]:
        print(f"+ {p1} not in neighbors of {obj} -> {obj} belongs to {p2}")
        graph.mark_true(obj, p2)
    # Check if p2 is a neighbor of obj. If not, then p1 belongs to obj.
    # Remove all edges that are not p1 of type(p1) from obj
    if p2 not in obj_adj[p2_type]:
        print(f"+ {p2} not in neighbors of {obj} -> {obj} belongs to {p1}")
        graph.mark_true(obj, p1)

    ## TODO: There's a bug here if p1_type and p2_type are the same!
    # # Check if obj has one edge of type(p1) and is p1
    # obj_p1_type_neighbors = obj_adj[p1_type]
    # if len(obj_p1_type_neighbors) == 1 and p1 in obj_p1_type_neighbors:
    #     print(f"++ {obj} has 1 '{p1_type}' neighbor ({obj_p1_type_neighbors}) -> {obj} eliminated from {p2}")
    #     graph.mark_false(obj, p2)
    # # Check if obj has one edge of type(p2) and is p2
    # obj_p2_type_neighbors = obj_adj[p2_type]
    # if len(obj_p2_type_neighbors) == 1 and p1 in obj_p2_type_neighbors:
    #     print(f"++ {obj} has 1 '{p2_type}' neighbor ({obj_p2_type_neighbors}) -> {obj} eliminated from {p1}")
    #     graph.mark_false(obj, p1)

    # if p1 has one neighbor of type(obj) and not obj, then
    #   p2 belongs to obj
    p1_neighbors = p1_adj[obj_type]
    if len(p1_neighbors) == 1 and obj not in p1_neighbors:
        print(f"+ {p1} has only one {obj_type} neighbor ({p1_neighbors}) -> {obj} belongs to {p2}")
        graph.mark_true(obj, p2)
    # if p2 has one neighbor of type(obj) and not obj, then
    #   p1 belongs to obj
    p2_neighbors = p2_adj[obj_type]
    if len(p2_neighbors) == 1 and obj not in p2_neighbors:
        print(f"+ {p2} has only one {obj_type} neighbor ({p2_neighbors}) -> {obj} belongs to {p1}")
        graph.mark_true(obj, p1)

def pairs(graph, pair1, pair2):
    assert len(pair1) == 2
    assert len(pair2) == 2
    a, b = pair1
    c, d = pair2
    graph.mark_false(a, b)
    graph.mark_false(c, d)
    either_or(graph, a, pair2)
    either_or(graph, b, pair2)
    either_or(graph, c, pair1)
    either_or(graph, d, pair1)


def delta_comparison(graph, lesser, greater, delta, category):
    assert delta >= 0
    logger.info(f"\n\nSIZE_DELTA({lesser=}, {greater=}, {delta=})")
    graph.mark_false(lesser, greater)
    numeric = graph._items[category]
    cat_neighbors = lambda x: graph.neighbors(x, category)
    # lesser can't be the max size, greater can't be the min size
    graph.mark_false(greater, min(numeric))
    graph.mark_false(lesser, max(numeric))
    for p in numeric:
        p_plus_delta = p + delta
        p_minus_delta = p - delta
        logger.info(f"++ {p=}, {p_plus_delta=}, {p_minus_delta}")
        logger.debug(f"++ {min(cat_neighbors(lesser))=}")
        logger.debug(f"++ {max(cat_neighbors(greater))=}")

        if p not in cat_neighbors(lesser) and p_plus_delta in numeric:
            logger.debug(f"+++ {p} not a neighbor of {lesser}, so {p_plus_delta} removed from {greater}")
            graph.mark_false(greater, p_plus_delta)
        if p not in cat_neighbors(greater) and p_minus_delta in numeric:
            logger.debug(f"+++ {p} not a neighbor of {greater}, so {p_minus_delta} removed from {lesser}")
            graph.mark_false(lesser, p_minus_delta)


        if p < min(cat_neighbors(lesser)) + delta:
            logger.info(f"++++ {p=} < {min(cat_neighbors(lesser)) + delta=}")
            graph.mark_false(greater, p)
        if p > max(cat_neighbors(greater)) - delta:
            logger.info(f"++++ {p=} > {max(cat_neighbors(greater)) - delta=}")
            graph.mark_false(lesser, p)
        if delta > 0:
            # if p - delta isn't in lesser, then p can't be in greater
            if p_minus_delta in numeric and p_minus_delta not in cat_neighbors(lesser):
                logger.info(f"+++++ {p_minus_delta=} not in {lesser} - removing {p} from {greater}")
                graph.mark_false(greater, p)
            # if p + delta isn't in greater, then p can't be in lesser
            if p_plus_delta in numeric and p_plus_delta not in cat_neighbors(greater):
                logger.info(f"+++++ {p_plus_delta=} not in {greater} - removing {p} from {lesser}")
                graph.mark_false(lesser, p)
                