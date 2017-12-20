import re
import numpy as np
import sys
import time
import cplex


class Painter:
    def __init__(self, graph):
        self.graph = graph
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


class BranchAndBound:
    def __init__(self, graph):
        self.graph = graph
        self.graph_size = len(graph[0])
        self.current_max_clique_size = 0

    def getNotConnectedVertexes(self):
        not_connected = []
        for i in range(0, self.graph_size - 1):
            for j in range(i, self.graph_size):
                if self.graph[i][j] == 0:
                    not_connected.append([i, j])
        return not_connected

    def initializeCplex(self):
        c = cplex.Cplex()
        c.objective.set_sense(c.objective.sense.maximize)
        c.variables.add(obj=[1.0] * self.graph_size, ub=[1.0] * self.graph_size,
                        names=['x{0}'.format(x) for x in range(self.graph_size)],
                        types=[c.variables.type.continuous] * self.graph_size)
        constraints = []
        for ind_set in Painter(self.graph).paintGraph():
            constraints.append([['x{0}'.format(x)
                                 for x in ind_set], [1.0] * len(ind_set)])
        for xi, xj in self.getNotConnectedVertexes():
            constraints.append(
                [['x{0}'.format(xi), 'x{0}'.format(xj)], [1.0, 1.0]])
        c.linear_constraints.add(lin_expr=constraints,
                                 senses=['L'] * len(constraints),
                                 rhs=[1.0] * len(constraints),
                                 names=['constr{0}'.format(x) for x in range(len(constraints))])
        return c

    def get_branching_variable(self, values):
        for i, val in enumerate(values):
            if not val.is_integer():
                return i
        return None

    def add_constraint(self, problem: cplex.Cplex, bvar: float, rhs: float):
        problem.linear_constraints.add(lin_expr=[[[bvar], [1.0]]], senses=['E'], rhs=[rhs],
                                       names=['bvar_{0}_{1}'.format(bvar, rhs)])
        return problem

    def branching(self, problem: cplex.Cplex):
        try:
            problem.solve()
            solution_values = problem.solution.get_values()
        except cplex.exceptions.CplexSolverError:
            return list()
        if sum(solution_values) > self.current_max_clique_size:
            branching_variable = self.get_branching_variable(solution_values)
            if branching_variable is None:
                current_clique = list(index for index, value in enumerate(solution_values) if value == 1.0)
                self.current_max_clique_size = len(current_clique) if self.current_max_clique_size \
                                                                      < len(current_clique)else self.current_max_clique_size
                return current_clique
            return max(self.branching(self.add_constraint(cplex.Cplex(problem), branching_variable, 1.0)),
                       self.branching(self.add_constraint(cplex.Cplex(problem), branching_variable, 0.0)),
                       key=lambda list: len(list))
        return list()

    def findMaxClique(self):
        return self.branching(self.initializeCplex())


def readGraphFromFile(file_name):
    with open(file_name, 'r') as read_file:
        for line in read_file:
            if line.startswith('p'):
                graph = np.eye(int(re.search('[0-9]+', line).group()))
            elif line.startswith('e'):
                e = re.findall('[0-9]+', line)
                graph[int(e[0]) - 1][int(e[1]) - 1] = 1
                graph[int(e[1]) - 1][int(e[0]) - 1] = 1

    return graph


if __name__ == "__main__":
    if len(sys.argv) > 2:
        timeout = int(sys.argv[2])
        file = sys.argv[1]
    else:
        file = "C:\\Users\\Daniil\\Desktop\\graphs\\johnson16-2-4.clq.txt"
        timeout = 3000
    end_time = time.time() + timeout

    max_clique = BranchAndBound(readGraphFromFile(file)).findMaxClique()

    print(str(timeout - (end_time - time.time())) + " " + str(len(max_clique)))
