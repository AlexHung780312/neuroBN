"""
************************************
Exact Maximum A Posteriori Inference
************************************

Perform exact MAP inference over a BayesNet object,
with or without evidence.

Eventually, there will be a wrapper function "map_exact"
for all of the algorithms, and users can choose their method as
an argument to that function.

Exact MAP Inference Algorithms
------------------------------

    - Max-Product Variable Elimination


References
----------
[1] Koller, Friedman (2009). "Probabilistic Graphical Models."

"""

__author__ = """N. Cullen <ncullen.th@dartmouth.edu>"""

from copy import copy
import numpy as np
from pulp import *

from neuroBN.classes.factor import Factor
from neuroBN.classes.factorization import Factorization


def map_ve_e(bn,
            evidence={},
            target=None,
            prob=False):
    """
    Perform Max-Sum Variable Elimination over a BayesNet object
    for exact maximum a posteriori inference.

    This has been validated w/ and w/out evidence
    
    """
    _phi = Factorization(bn)

    order = copy(list(bn.nodes()))
    #### EVIDENCE PROCESSING ####
    for E, e in evidence.items():
        _phi -= (E,e)
        order.remove(E)

    #### MAX-PRODUCT ELIMINATE VAR ####
    for var in order:
        _phi //= var 
    
    #### TRACEBACK MAP ASSIGNMENT ####
    max_assignment = _phi.traceback_map()

    #### RETURN ####
    if prob:
        # multiply phi's together if there is evidence
        final_phi = _phi.consolidate()
        max_prob = round(final_phi.cpt[0],5)

        if target is not None:
            return max_prob, max_assignment[target]
        else:
            return max_prob, max_assignment
    else:
        if target is not None:
            return max_assignment[target]
        else:
            return max_assignment
    

def map_opt_e(bn, evidence={}):
    """
    Solve MAP Inference as an integer linear optimization
    problem, as formulated in Sontag's notes:
    http://cs.nyu.edu/~dsontag/courses/pgm12/slides/lecture6.pdf

    Arguments
    ---------
    *bn* : a BayesNet object

    *evidence* : a dictionary, where
        key = rv and value = rv's value

    """

    model = LpProblem("MAP Inference",LpMinimize)

    # CREATE VARIABLE FOR EVERY CPT ENTRY
    var_dict = {} # key = rv, value = list of variables for each cpt entry
    weight_list = []
    var_list = []
    ii = 0
    for rv in bn.nodes():
        var_dict[rv] = {}
        for idx in xrange(len(bn.cpt(rv))):
            #str_rep = bn.cpt_str_idx(rv,idx)
            str_rep = str(rv)+'-'+str(idx)
            new_var = LpVariable(str_rep,0,1,LpInteger)
            var_dict[rv][idx] = new_var
            var_list.append(new_var)
            weight_list.append(round(-np.log(bn.cpt(rv)[idx]),3))
            ii+=1

    # OBJECTIVE FUNCTION
    model += np.dot(var_list,weight_list)
    
    # RV - VALUE CONSTRAINTS
    for rv in bn.nodes():
        model += sum([var_dict[rv][idx] \
            for idx in range(len(bn.cpt(rv)))]) == 1, \
            'RV Constraint - ' + str(rv)
    
    # OUTGOING EDGE CONSTRAINTS
    k=0
    for rv in bn.nodes():
        for val_idx in xrange(len(bn.cpt(rv))):
            val = bn.values(rv)[val_idx % bn.card(rv)] # actual rv-val
            for child in bn.children(rv):
                # get indices of the child cpt which correspond to rv-val
                child_cpt_indices = bn.cpt_indices(child, {rv:val})
                # rv-val variable = sum(child[child_cpt_indices] variables)
                model += var_dict[rv][val_idx] <= \
                    sum([var_dict[child][i] for i in child_cpt_indices]), \
                    'OUT-CPT Constraint - ' + str(k)
                k+=1
    
    # INGOING EDGE CONSTRAINTS
    k=0
    for rv in bn.nodes():
        if len(bn.parents(rv)) > 0:
            for val_idx in xrange(len(bn.cpt(rv))):
                # find which parent-vals that index belongs to
                p_cpt = {}
                for parent in bn.parents(rv):
                    p_cpt[parent] = []
                    for p_idx in xrange(len(bn.cpt(parent))):
                        p_val = bn.values(parent)[p_idx % bn.card(parent)]
                        if val_idx in bn.cpt_indices(rv, {parent:p_val}):
                            p_cpt[parent].append(p_idx)
                model += var_dict[rv][val_idx] <= \
                    sum([var_dict[p][pi] for p in bn.parents(rv) for pi in p_cpt[p]]), \
                    'IN-CPT Constraint - ' + str(k)
                k+=1
    print model

    model.solve()

    #for v in model.variables():
       # if v.varValue == 1.0:
         #   print v.name

    

    





