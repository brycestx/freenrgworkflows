#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = "Antonia Mey"
__email__ = "antonia.mey@ed.ac.uk"


import numpy as np
import networkx as nx
import scipy.stats
import copy


class PerturbationGraph(object):
    """Populates a directed free energy perturbation graph"""
    def __init__(self, ):
        self._graph = None
        self._pathAverages = []
        self._weightedPathAverages = []


    def populate_pert_graph(self, filename, delimiter=',', comments='#', nodetype=str, data=(('weight',float),('error',float))):
        r"""
        Reads data from a correctly formatted csv file into a networkx digraph
        Parameters
        ----------
        filename : String
            filename of the forward and backward perturbation generated from simulation output
            Filestructure should be:
            node1,node2,DG,eDG,other_attributes
        delimiter : String
            delimiter for network file 
            Default = ','
        comments : String
            Symbol used for comments in network file
            Default = '#'
        nodetype : String
            All nodes are usually identified by the compound name
        data : list
            Default, weight and error on Free energies of node
        """
        if self._graph == None:
            graph = nx.read_edgelist(filename, delimiter=delimiter, comments=comments, create_using=nx.DiGraph(),nodetype=nodetype, data=data)
            self._graph = self._symmetrize_graph(graph)
        else:
            print ('Use the method add_data_to_graph, to add further data to an existing graph')
            exit(-1)

    def add_data_to_graph(self, filename, delimiter=',', comments='#', nodetype=str, data=(('weight', float),('error',float))):
        r"""
        Adds data to an existing graph from a csv file in the right networkx format
        Parameters
        ----------
        filename : String
            filename of the forward and backward perturbation generated from simulation output
            Filestructure should be:
            node1,node2,DG,eDG,other_attributes
        delimiter : String
            delimiter for network file 
            Default = ','
        comments : String
            Symbol used for comments in network file
            Default = '#'
        nodetype : String
            All nodes are usually identified by the compound name
        data : list
            Default, weight and error on Free energies of node
        """
        newGraph = nx.read_edgelist(filename, delimiter=delimiter, comments=comments, create_using=nx.DiGraph(),nodetype=nodetype, data=data)
        newGraph = self._symmetrize_graph(newGraph)
        if self._graph!=None:
            for u,v,w in newGraph.edges(data=True):
                if self._graph.has_edge(u,v):
                    z = self._graph.get_edge_data(u,v)
                    mean_edge = np.mean([z['weight'], w['weight']])
                    error = 0.5*np.sqrt(z['error']**2+w['error']**2)
                    self._graph.remove_edge(u,v)
                    self._graph.add_edge(u,v,weight=mean_edge,error=error)
                else:
                    self._graph.add_edge(u, v, w)
        else:
            self._graph = newGraph

    def _symmetrize_graph(self, graph):
        r"""symmetrises the graph and computes backward and forward averages where  given. 
        Parameters
        ----------
        graph : networkx graph
            directed networkx graph

        Returns
        -------
        graph : networkx graph
            returns directed graph where, if not both a forward and backward edge are present a symmetrized reverse edge is included
        """
        symmetrizedGraph = nx.DiGraph()
        for u,v,w_forward in graph.edges(data=True):
            if graph.has_edge(v,u):
                w_backward = graph.get_edge_data(v,u)
                avg_weight_forw = np.mean([w_forward['weight'], -w_backward['weight']])
                avg_weight_back = -avg_weight_forw
                error = np.std([w_forward['weight'], -w_backward['weight']])
                symmetrizedGraph.add_edge(u,v,weight=avg_weight_forw, error = error)
                symmetrizedGraph.add_edge(v,u,weight=avg_weight_back, error = error)
        for u,v,w in symmetrizedGraph.edges(data=True):
            if not symmetrizedGraph.has_edge(v,u):
                assymetric_w = -w['weight']
                assymetric_e = -w['error']
                symmetrizedGraph.add_edge(v,u,weight=assymetric_w, error = assymetric_e)
        return symmetrizedGraph

    def save_average_paths(self, filename, pathAverages):
        f = open(filename, 'w')
        for d in pathAverages:
            for k,v in d.iteritems():
                if k == 'error':
                    error = v
                else:
                    r_energy_k = k
                    r_energy_v = v
            f.write(str(r_energy_k)+', '+str(r_energy_v)+', '+str(error)+'\n')
        f.close()

    def compute_average_paths(self, target_node):
        r"""
        Parameters
        ----------
        target_node : string
            node to which all possible paths are computed
        """
        #Get all relative free energies with respect to node x
        for n in self._graph.nodes():
            paths = nx.shortest_simple_paths(self._graph,target_node , n)
            err_list = []
            sum_list = []
            for p in paths:
                sum = 0
                error = 0.0
                for node in range(len(p)-1):
                    sum= sum+ self._graph.get_edge_data(p[node], p[node+1])['weight']
                    error = error+self._graph.get_edge_data(p[node], p[node+1])['error']**2
                sum_list.append(sum)
                err_list.append(error)
                error = np.sqrt(error)
                #print r'DDG for path %s is %f +/- %f kcal/mol' %(p, sum, error)
            avg_sum = np.mean(np.array(sum_list))
            avg_err = np.mean(np.array(err_list))
            avg_std = np.std(np.array(sum_list))
            #print ("Average sum for path to %s is %f " %(n,avg_sum))
            a = {str(n):avg_sum}
            a['error']=avg_std
            #a['error']=sqrt(avg_err)
            self._pathAverages.append(a)

    def compute_weighted_avg_paths(self, target_node):
        r""" computes all possible paths to a target node and returns a weighted average based on the errors along the edges of the path
        Parameters
        ----------
        target_node : string
            string name of the target node as defined in the networkx graph
        """
        #Get all relative free energies with respect to node x
        a = {target_node:0.0}
        a['error']=0.0
        self._weightedPathAverages.append(a)
        for n in self._graph.nodes():
            if n == target_node:
                continue
            paths = list(nx.shortest_simple_paths(self._graph,target_node , n))
            err_list = []
            sum_list = []
            for p in paths:
                summing = 0
                error = 0.0
                for node in range(len(p)-1):
                    summing= summing+ self._graph.get_edge_data(p[node], p[node+1])['weight']
                    error = error+self._graph.get_edge_data(p[node], p[node+1])['error']**2
                sum_list.append(summing)
                error = np.sqrt(error)
                err_list.append(error)
            err_list = np.array(err_list)
            sum_weights = np.sum(1.0/err_list)
            path_weights = (1.0/err_list)/sum_weights
            avg_sum = 0.0
            avg_err = 0.0
            for i in range(len(sum_list)):
                s = sum_list[i]
                avg_sum = avg_sum +(path_weights[i]*s)
                avg_err = avg_err+path_weights[i]*err_list[i]**2
            avg_err = np.sqrt(avg_err)
            a = {str(n):avg_sum}
            a['error']=avg_err
            self._weightedPathAverages.append(a)


    def get_cycles(self, max_length=4):
        r"""
        TODO: elaborate and find good way of saving this information 
        """
        #cycle closure
        cyc = nx.simple_cycles(self._graph)
        for c in cyc:
            sum = 0
            error = 0
            if len(c)>2:
                sum = self._graph.get_edge_data(c[-1], c[0])['weight']
                error = (self._graph.get_edge_data(c[-1], c[0])['error'])**2
                for node in range(len(c)-1):
                    sum= sum+ self._graph.get_edge_data(c[node], c[node+1])['weight']
                    error = error +(self._graph.get_edge_data(c[node], c[node+1])['error'])**2
                error = np.sqrt(error)
            if len(c)<=max_length:
                print ('DDG for cycle %s is %.2f ± %.2f kcal/mol' %(c,sum,error))

    @property
    def graph(self):
        return self._graph

    @property
    def pathAverages(self):
        r"""
        Return
        ------
        pathAverages : dictionary
            dictionary containing averaged free energies for each path, with paths weighted in the same way 
        """
        return self._pathAverages

    @property
    def weightedPathAverages(self):
        return self._weightedPathAverages




