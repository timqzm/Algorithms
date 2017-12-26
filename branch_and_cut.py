import re
import numpy as np
import sys
import time
import cplex


class Painter:
    def __init__(self, graph, degrees):
        self.graph = graph
        self.degrees = degrees
        self.colors = [0]
        self.colored_sets = [[]]

    def paintGraph(self):
        for vertex in range(len(self.graph[0])):
            self.paintVertex(vertex)
        return self.colored_sets

    def get_connected_vertexes_with_lower_indexes(self, vertex):
        return list(map(lambda y: y[0], filter(lambda x: x[1] == 1, enumerate(self.graph[vertex][:vertex]))))

    def paintVertex(self, vertex):
        for i in self.colors:
            if not (lambda a, b: any(i in b for i in a))(self.get_connected_vertexes_with_lower_indexes(vertex),
                                                         self.colored_sets[i]):
                self.colored_sets[i].append(vertex)
                return
        self.colors.append(len(self.colors))
        self.colored_sets.append([vertex])

    def paintSetOfVertexes(self, nodes):
        deg_and_ind = sorted(zip(list(map(lambda node: self.degrees[node], nodes)), nodes))
        sorted_indexes = [elem[1] for elem in deg_and_ind]
        coloring = [-1 for i in sorted_indexes]
        coloring[sorted_indexes[0]] = 0
        available = [False for i in sorted_indexes]
        for el in sorted_indexes[1:]:
            for sec_el in sorted_indexes:
                if self.graph[el][sec_el] == 1 and coloring[sec_el] != -1:
                    available[coloring[sec_el]] = True
            index = available.index(False)
            coloring[el] = index
            available = [False for i in sorted_indexes]
        # if max(coloring) + 1 == len(nodes):
        #    return True  # this is clique
        # else:
        ind_sets = []
        for color in range(max(coloring)):
            # if coloring.count(color) < 2:
            # continue
            ind_sets.append([index for index, value in enumerate(coloring) if value == color])
        return ind_sets


class BranchAndCut:
    def __init__(self, graph, degrees):
        self.graph = graph
        self.degrees = degrees
        self.graph_size = len(graph[0])
        # print("GRAPH SIZE", self.graph_size)
        self.current_max_clique_size = 0
        self.constraints = []
        self.constraints_uselessness = []
        self.constraints_count = 0
        self.m = 0

    def initializeCplex(self):
        c = cplex.Cplex()
        c.set_log_stream(None)
        c.set_error_stream(None)
        c.set_warning_stream(None)
        c.set_results_stream(None)
        c.objective.set_sense(c.objective.sense.maximize)
        c.variables.add(obj=[1.0] * self.graph_size,
                        ub=[1] * self.graph_size,
                        names=['x{0}'.format(x) for x in range(self.graph_size)],
                        types=[c.variables.type.continuous] * self.graph_size)

        #ind_sets = Painter(self.graph, self.degrees).paintSetOfVertexes(range(self.graph_size))
        ind_sets=Painter(self.graph, self.degrees).paintGraph()
        self.constraints_count+=len(ind_sets)
        len_ind_sets = 0
        for ind_set in ind_sets:
            len_ind_sets+=len(ind_set)
            self.constraints.append([ind_set, [1.0] * len(ind_set)])
        print(len_ind_sets)
        print(ind_sets)
        print("ind sets count", len(ind_sets))
        self.m = len(ind_sets)
        self.constraints_uselessness = [0] * len(self.constraints)
        c.linear_constraints.add(lin_expr=self.constraints,
                                 senses=['L'] * len(self.constraints),
                                 rhs=[1] * len(self.constraints),
                                 names=['c{0}'.format(x) for x in range(len(self.constraints))])
        return c

    def get_branching_variable(self, values):
        max_ = 0
        idx = 0
        for i, val in enumerate(values):
            if not val.is_integer() and val > max_:
                max_ = val
                idx = i
        if max_ != 0:
            return idx
        else:
            return None

    def check_clique(self, values):
        values = sorted(values)
        missed_edges = list()
        for v1 in values:
            for v2 in values[values.index(v1) + 1:]:
                if self.graph[v1, v2] == 0:
                    return tuple([v1, v2])
        return True

    def add_constraint(self, problem, bvars, rhs, type_eq):
        #print(problem.linear_constraints)
        if len(bvars) == 1:
            #print("addin 1 BVAR cons")
            self.constraints_uselessness.append(0)
            problem.linear_constraints.add(lin_expr=[[bvars, [1.0]]], senses=[type_eq], rhs=[rhs],
                                           names=['bvar_{0}_{1}'.format(bvars, rhs)])
        else:
            #print("addin 1 cons")
            self.constraints.append([['x{0}'.format(x) for x in bvars], [1.0] * len(bvars)])
            self.constraints_uselessness.append(0)
            problem.linear_constraints.add(lin_expr=[[['x{0}'.format(x) for x in bvars], [1.0] * len(bvars)]],
                                           senses=['L'],
                                           rhs=[1.0],
                                           names=['constr{0}'.format(len(self.constraints))])

        return problem

    def branching(self, problem):
        try:
            problem.set_log_stream(None)
            problem.set_error_stream(None)
            problem.set_warning_stream(None)
            problem.set_results_stream(None)
            problem.solve()
            solution_values = problem.solution.get_values()

            slacks = problem.solution.get_linear_slacks()

            for i in range(len(slacks)):
                if slacks[i] == 0:
                    # print("inc uslss", i)
                    self.constraints_uselessness[i] += 1
                    # if self.constraints_uselessness[i] > self.graph_size ** 1.8:
                    # inds.append(i)

            if len(slacks) > self.m and max(self.constraints_uselessness) > self.graph_size:
                d = len(slacks) - self.m
                print("too many slacks!", len(slacks), "diff", d)
                for i in range(d):
                    j = self.constraints_uselessness.index(max(self.constraints_uselessness))
                    del self.constraints_uselessness[j]
                    problem.linear_constraints.delete(j)

            # print("slacks:", slacks)

            # inds = []

            # #print("uslssnss:", self.constraints_uselessness)

            # if len(inds) > 0:
            #     print("DELETE!!!", inds)
            #     self.constraints_uselessness = [x for i, x in enumerate(self.constraints_uselessness) if i not in inds]
            #     problem.linear_constraints.delete(inds)

        except cplex.exceptions.CplexSolverError:
            return list()
        if sum(solution_values) > self.current_max_clique_size:
            branching_variable = self.get_branching_variable(solution_values)
            if branching_variable is None:  # all solution_values have int type
                possible_clique = list(index for index, value in enumerate(solution_values) if value == 1)
                # print('objective', sum(possible_clique))
                check_result = self.check_clique(possible_clique)
                if check_result == True:  # if clique
                    if self.current_max_clique_size < len(possible_clique):
                        self.current_max_clique_size = len(possible_clique)
                        return possible_clique
                    return list()
                else:
                    return self.branching(self.add_constraint(cplex.Cplex(problem), list(check_result), 1.0, 'L'))
            return max(self.branching(self.add_constraint(cplex.Cplex(problem), [branching_variable], 1.0, 'E')),
                       self.branching(self.add_constraint(cplex.Cplex(problem), [branching_variable], 0.0, 'E')),
                       key=lambda list: len(list))
        return list()

    def findMaxClique(self):
        return self.branching(self.initializeCplex())


def readGraphFromFile(file_name):
    with open(file_name, 'r') as read_file:
        graph = np.array
        for line in read_file:
            if line[0] == 'p':
                num_nodes = int(line.split()[2])
                graph = np.zeros((num_nodes, num_nodes), dtype=bool)
                degrees = np.zeros(num_nodes)
            if line[0] == 'e':
                edge = tuple(int(x) - 1 for x in line[1:].split())
                # graph[edge] = 1
                graph[edge[1]][edge[0]] = 1
                graph[edge[0]][edge[1]] = 1
                degrees[edge[0]] += 1
                degrees[edge[1]] += 1

    return graph, degrees


if __name__ == "__main__":
    if len(sys.argv) > 2:
        timeout = int(sys.argv[2])
        file = sys.argv[1]
    else:
        file = "U:\\clq\\myciel3.col.txt"
        # file = "U:\\clq\\johnson8-2-4.clq.txt"
        # file = "U:\\clq\\hamming6-4.clq.txt"

        # file = "C:\\Users\\Daniil\\Desktop\\graphs\\hamming6-4.clq.txt"
        # file = "C:\\Users\\shimk\\OneDrive\\Documents\\MAXCLIQUE_3\\clq\\hamming6-4.clq.txt"
        timeout = 3000
    end_time = time.time() + timeout

    graph, degrees = readGraphFromFile(file)
    max_clique = BranchAndCut(graph, degrees).findMaxClique()

    print(str(timeout - (end_time - time.time())) + " " + str(len(max_clique)), max_clique)
