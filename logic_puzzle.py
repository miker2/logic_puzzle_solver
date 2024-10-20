import itertools
import logging
import networkx as nx
import pprint

logger = logging.getLogger(__name__)

class LogicPuzzle:
    def __init__(self, categories):
        # Check that all categories have the same number of items:
        assert len(set([len(v) for v in categories.values()])) == 1, "All categories must have the same number of items."

        self._items = categories
        self._all_items = []
        self._answers = {}  # This will duplicate a lot of info, but we can come up with a more efficient way later.
        for k, v in categories.items():
            self._all_items += v

            cat_minus_k = set(categories.keys()).difference([k])
            for item in v:
                self._answers[item] = {e : None for e in cat_minus_k}

        # pprint.pprint(self._answers)

        self._G = nx.Graph()
        for k, v in categories.items():
            self._G.add_nodes_from(v, category=k)
        
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

    def add_comparative_relationship(self, lesser, greater):
        # This is a first-class citizen of the puzzle because we'll need to collect information
        # across multiple clues for some of the solution logic, e.g.
        #  a < b
        #  b < c
        #  therefore a < c
        #  and a != b , b != c & a != c
        pass

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
        # Fill in the answer info
        self._answers[node1][type2] = node2
        self._answers[node2][type1] = node1


# A collection of logical blocks often found in a logic puzzle:
def neither_nor(puzzle, obj, pair):
    pass

def either_or(puzzle, obj, pair):
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
    obj_adj = puzzle.neighbors_by_type(obj)
    obj_type = puzzle._category(obj)
    p1, p2 = pair
    p1_adj = puzzle.neighbors_by_type(p1)
    p1_type = puzzle._category(p1)
    p2_adj = puzzle.neighbors_by_type(p2)
    p2_type = puzzle._category(p2)
    puzzle.mark_false(p1, p2)
    
    # Check if p1 is a neighbor of obj. If not, then p2 belongs to obj.
    # Remove all edges that are not p2 of type(p2) from obj
    if p1 not in obj_adj[p1_type]:
        print(f"+ {p1} not in neighbors of {obj} -> {obj} belongs to {p2}")
        puzzle.mark_true(obj, p2)
    # Check if p2 is a neighbor of obj. If not, then p1 belongs to obj.
    # Remove all edges that are not p1 of type(p1) from obj
    if p2 not in obj_adj[p2_type]:
        print(f"+ {p2} not in neighbors of {obj} -> {obj} belongs to {p1}")
        puzzle.mark_true(obj, p1)

    ## TODO: There's a bug here if p1_type and p2_type are the same!
    if p1_type != p2_type:
        # Check if obj has one edge of type(p1) and is p1
        obj_p1_type_neighbors = obj_adj[p1_type]
        if len(obj_p1_type_neighbors) == 1 and p1 in obj_p1_type_neighbors:
            print(f"++ {obj} has 1 '{p1_type}' neighbor ({obj_p1_type_neighbors}) -> {obj} eliminated from {p2}")
            puzzle.mark_false(obj, p2)
        # Check if obj has one edge of type(p2) and is p2
        obj_p2_type_neighbors = obj_adj[p2_type]
        if len(obj_p2_type_neighbors) == 1 and p1 in obj_p2_type_neighbors:
            print(f"++ {obj} has 1 '{p2_type}' neighbor ({obj_p2_type_neighbors}) -> {obj} eliminated from {p1}")
            puzzle.mark_false(obj, p1)

    # if p1 has one neighbor of type(obj) and not obj, then
    #   p2 belongs to obj
    p1_neighbors = p1_adj[obj_type]
    if len(p1_neighbors) == 1 and obj not in p1_neighbors:
        print(f"+ {p1} has only one {obj_type} neighbor ({p1_neighbors}) -> {obj} belongs to {p2}")
        puzzle.mark_true(obj, p2)
    # if p2 has one neighbor of type(obj) and not obj, then
    #   p1 belongs to obj
    p2_neighbors = p2_adj[obj_type]
    if len(p2_neighbors) == 1 and obj not in p2_neighbors:
        print(f"+ {p2} has only one {obj_type} neighbor ({p2_neighbors}) -> {obj} belongs to {p1}")
        puzzle.mark_true(obj, p1)

    def transitive_check(pair_item, other_category):
        
        # if pair_item 
        pass

    # TODO: Add transitive either-or checks (based on true conditions)
    # A transitive relationship exists whenever you have a pre-existing true or false relationship
    # on the grid for either one of the two "either/or" options, in relation to the group of the
    # other option.
    
    # Check p1 in relation to category(p2), and
    # Check p2 in relation to category(p1)
    #
    # If there exists a true relationship for p1 in category(p2) then obj is that value or p2
    # If there exists a true relationship for p2 in category(p1) then obj is that value or p1
    #  -- Mark all of obj options of the category in question as false
    # 

def pairs(puzzle, pair1, pair2):
    assert len(pair1) == 2
    assert len(pair2) == 2
    a, b = pair1
    c, d = pair2
    puzzle.mark_false(a, b)
    puzzle.mark_false(c, d)
    either_or(puzzle, a, pair2)
    either_or(puzzle, b, pair2)
    either_or(puzzle, c, pair1)
    either_or(puzzle, d, pair1)

    def pair_same_type_logic(pair, p_type, other_pair):
        # IF both items in a pair are the same type, then we know some additional
        # information about other objects of the same type.
        assert len(pair) == 2
        assert len(other_pair) == 2
        others = set(pair).symmetric_difference(puzzle._items[p_type])
        c, d = other_pair
        for o in others:
            o_adj = puzzle.neighbors(o)
            if c not in o_adj and d not in o_adj:
                continue
            if c not in puzzle.neighbors(o):
                print("++ {c} not a neighbor of {o}, so {d} can't be a neighbor of {o}")
                puzzle.mark_false(o, d)
            elif d not in puzzle.neighbors(o):
                print("++ {d} not a neighbor of {o}, so {c} can't be a neighbor of {o}")
                puzzle.mark_false(o, c)

    p1a_type = puzzle._category(a)
    p1b_type = puzzle._category(b)
    if p1a_type == p1b_type:
        pair_same_type_logic(pair1, p1a_type, pair2)

    p2c_type = puzzle._category(c)
    p2d_type = puzzle._category(d)
    if p2c_type == p2d_type:
        pair_same_type_logic(pair2, p2c_type, pair1)

def mutual_exclusive(puzzle, list_of_things):
    # All of the things in the list are different
    # Add a false relationship to any intersections of the pairs of items in the list:
    pass



def ranking():
    # Need to add a rule that accumulates comparative relationships and identifies
    # Additional false relationships. E.g.
    #   a < b
    #   b < c
    # We now know:
    #   a < b < c
    # So a != b, b != c & a != c
    pass

def delta_comparison(puzzle, lesser, greater, delta, category):
    assert delta >= 0
    logger.info(f"\n\nSIZE_DELTA({lesser=}, {greater=}, {delta=})")
    puzzle.mark_false(lesser, greater)
    numeric = puzzle._items[category]
    cat_neighbors = lambda x: puzzle.neighbors(x, category)
    # lesser can't be the max size, greater can't be the min size
    puzzle.mark_false(greater, min(numeric))
    puzzle.mark_false(lesser, max(numeric))
    for p in numeric:
        p_plus_delta = p + delta
        p_minus_delta = p - delta
        logger.info(f"++ {p=}, {p_plus_delta=}, {p_minus_delta}")
        logger.debug(f"++ {min(cat_neighbors(lesser))=}")
        logger.debug(f"++ {max(cat_neighbors(greater))=}")

        if p not in cat_neighbors(lesser) and p_plus_delta in numeric:
            logger.debug(f"+++ {p} not a neighbor of {lesser}, so {p_plus_delta} removed from {greater}")
            puzzle.mark_false(greater, p_plus_delta)
        if p not in cat_neighbors(greater) and p_minus_delta in numeric:
            logger.debug(f"+++ {p} not a neighbor of {greater}, so {p_minus_delta} removed from {lesser}")
            puzzle.mark_false(lesser, p_minus_delta)


        if p < min(cat_neighbors(lesser)) + delta:
            logger.info(f"++++ {p=} < {min(cat_neighbors(lesser)) + delta=}")
            puzzle.mark_false(greater, p)
        if p > max(cat_neighbors(greater)) - delta:
            logger.info(f"++++ {p=} > {max(cat_neighbors(greater)) - delta=}")
            puzzle.mark_false(lesser, p)
        if delta > 0:
            # if p - delta isn't in lesser, then p can't be in greater
            if p_minus_delta in numeric and p_minus_delta not in cat_neighbors(lesser):
                logger.info(f"+++++ {p_minus_delta=} not in {lesser} - removing {p} from {greater}")
                puzzle.mark_false(greater, p)
            # if p + delta isn't in greater, then p can't be in lesser
            if p_plus_delta in numeric and p_plus_delta not in cat_neighbors(greater):
                logger.info(f"+++++ {p_plus_delta=} not in {greater} - removing {p} from {lesser}")
                puzzle.mark_false(lesser, p)
                
# Other solving methods that may or may not be covered:
# Parallel cross elimination
# Skewed cross elimination
# 