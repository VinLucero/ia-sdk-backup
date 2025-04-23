import time
import random
import numpy as np
import os
import traceback
import logging
from typing import Tuple, Any, Union
from collections.abc import Callable
from copy import deepcopy
import multiprocessing
from deap import base, creator, tools, algorithms
from deap.tools import Logbook
from tqdm.auto import tqdm
from ia.gaius.agent_client import AgentClient
from ia.gaius.manager import AgentManager
from ia.gaius.pvt import PerformanceValidationTest
from hashlib import sha1

logger = logging.getLogger(__name__)

# define maximum permissible values for performing optimization
# on several genes. Restricts range of values explored by optimization
MAX_PRED_LIMIT = 100
MAX_RT_LIMIT = 0.999

SUPPORTED_GENES = ['recall_threshold', 'max_predictions']
SPAWN_AGENT_LOCK = multiprocessing.Lock()

def generate_gene_data(config):

    result = {}
    for gene, params in config.items():
        if params["step"] == 0:
            value = round(random.uniform(params["start"], params["stop"]), 2)
        else:
            values = range(params["start"], params["stop"], params["step"])
            # print(gene, list(values))
            value = random.choice(values)

        result[gene] = value
    return result

class GenomeOptimizer:

    def __init__(self,
                 path_to_original_genome: str,
                 nodes_to_optimize: list,
                 pvt_config: dict,
                 gene_config: dict, 
                 evolutionary_params: dict,
                 agent_constructor=AgentClient,
                 agent_kwargs: dict = None,
                 pvt_constructor=PerformanceValidationTest,
                 weights: dict = {"accuracy": 1.0, "precision": 1.0},
                 ):
        self.am = AgentManager(local=False)
        self.genome_path = path_to_original_genome
        self.nodes_to_optimize = nodes_to_optimize
        self.agent_constructor = agent_constructor
        self.agent_kwargs = agent_kwargs
        self.pvt_config = pvt_config
        self.gene_config = gene_config
        self.pvt_constructor = pvt_constructor
        self._results = None  # internal variable to hold copy of results

        # Parameters for running evolution
        self.evolutionary_params = evolutionary_params
        self.fitness_weight_dict = weights

        try:
            del creator.FitnessMax
            del creator.Individual
        except:
            pass
        # Create and register DEAP types
        creator.create("FitnessMax", base.Fitness,
                       weights=(self.fitness_weight_dict["accuracy"],
                                self.fitness_weight_dict["precision"]))
        creator.create("Individual", dict, fitness=creator.FitnessMax)

        self.stats = tools.Statistics(key=lambda ind: ind)
        self.stats.register("average_fitness",
                            compute_metric_by_key, func=np.average)
        self.stats.register("std_dev_fitness",
                            compute_metric_by_key, func=np.std)
        self.stats.register("min_fitness", compute_metric_by_key, func=np.min)
        self.stats.register("max_fitness", compute_metric_by_key, func=np.max)

        # Create the toolbox
        self.toolbox = base.Toolbox()
        self.toolbox.register(
            'gen_individual', self.generate_individual, nodes_to_optimize=self.nodes_to_optimize)
        # self.toolbox.register("individual", creator.Individual)
        self.toolbox.register("population", tools.initRepeat,
                              list, self.toolbox.gen_individual)

        # Register evolutionary operators
        self.toolbox.register("evaluate", evaluate, am=self.am, agent_constructor=self.agent_constructor,
                              agent_kwargs=self.agent_kwargs,
                              pvt_config=self.pvt_config, genome_path=self.genome_path,
                              pvt_constructor=self.pvt_constructor,
                              nodes_to_optimize=nodes_to_optimize)
        self.toolbox.register("mate", crossover, toolbox=self.toolbox, gene_config=self.gene_config)
        self.toolbox.register("mutate", mutate, toolbox=self.toolbox, gene_config=self.gene_config)
        self.toolbox.register("select", tools.selTournament, tournsize=3)

    def generate_individual(self, nodes_to_optimize: list):

        # return creator.Individual({node: {"recall_threshold":  round(random.uniform(0.001, 0.999), 4),
        #                            "max_predictions": round(random.uniform(1, 100))} for node in nodes_to_optimize})
        return creator.Individual({node: generate_gene_data(self.gene_config) for node in nodes_to_optimize})

    def evolve(self, pool=None):
        if pool:
            self.toolbox.register("map", pool.map)
        params = deepcopy(self.evolutionary_params)
        population = self.toolbox.population(params.pop("npop"))

        self._results = algorithms.eaSimple(
            population=population, toolbox=self.toolbox, stats=self.stats, **params)
        return deepcopy(self._results)

    def multiprocessed_evolve(self, n_proc: int = None, start_hoster: bool=True) -> Tuple[Any, Logbook]:
        """Driver function to run genetic optimization using multithreading.
        Utilizes AgentManager to spawn and manage multiple agents

        Args:
            n_proc (int, optional): Number of processing cores to use. Defaults to minimum of (core_count, population_size).

        Returns:
            Tuple[Any, Logbook]
        """

        pop = None
        # set max number of processes to minimum of population size, core count
        if n_proc == None:
            CPU_COUNT = os.cpu_count()
            if CPU_COUNT == None:
                CPU_COUNT = 1

            n_proc = min([self.evolutionary_params['npop'], CPU_COUNT])
        try:
            SPAWN_AGENT_LOCK.release() # ensure lock is released before starting multiprocessing pool
        except:
            pass

        try:
            with multiprocessing.Pool(processes=n_proc) as pool:
                if start_hoster:
                    self.am.start_hoster()
                pop = self.evolve(pool=pool)
        except Exception as error:
            traceback.print_exc()
            logger.exception("Exception during multiprocessed_evolve")
            logger.info("Killing started agents")
            self.am.kill_all_agents()
            pass

        return pop


def compute_metric_by_key(pop: list, func: Callable):
    for ind in pop:
        ind.fitness_overall = np.average(ind.fitness.values, weights=[
                                         int(weight) for weight in ind.fitness.weights])
    return func([ind.fitness_overall for ind in pop])


def evaluate(individual,
             am: AgentManager,
             agent_constructor: AgentClient,
             agent_kwargs,
             pvt_config: dict,
             genome_path: str,
             pvt_constructor: Callable,
             nodes_to_optimize: list) -> Tuple[float, float]:
    """Driver function for conducting PVT on each individual

    Args:
        individual: The individual (including GCPs)
        am (AgentManager): AgentManager used to spawn a new agent
        pvt_config (dict): Configuration for PVT test
        genome_path (str): Genome used to spawn agent
        pvt_constructor (PerformanceValidationTest): PVT class
        nodes_to_optimize (list): list of nodes to optimize

    Returns:
        tuple: accuracy, precision
    """
    am.remediate_dead_agents()
    # Copy baseline config to assign agent
    test_config = deepcopy(pvt_config)
    if agent_kwargs == None:
        agent_kwargs = {}
    # logger.debug(f"{individual = }")
    ind_copy = deepcopy(individual)
    agent_name = sha1(str(ind_copy).encode(
        'utf-8', 'replace')).hexdigest()[:4] + "-" + multiprocessing.current_process().name

    accuracy = 0.0
    precision = 0.0

    # check if agent already alive
    if agent_name in am.current_agents:
        am.delete_agent(agent_name)
    released = True
    try:
        SPAWN_AGENT_LOCK.acquire()
        released = False

        with am.agent_context(genome_file=genome_path, user_id='optimizer', agent_id=agent_name, agent_name=agent_name) as agent:
            SPAWN_AGENT_LOCK.release()
            released = True

            time.sleep(5)
            agent = agent_constructor(agent._bottle_info, **agent_kwargs)
            agent.connect()
            logger.debug(f'in evaluate, {individual = }')
            for node in nodes_to_optimize:
                agent.change_genes(dict(individual[node]), nodes=node)

            test_config["agent"] = agent
            pvt = pvt_constructor(**test_config)
            agent.set_summarize_for_single_node(False)

            pvt.conduct_pvt()

            accuracy = pvt.testing_log[-1][-1]['overall_metrics']["accuracy"]["hive"]
            precision = pvt.testing_log[-1][-1]['overall_metrics']["precision"]["hive"]
            logger.info(
                f"Individual {individual} results: {accuracy = },{precision = }")

            SPAWN_AGENT_LOCK.acquire()
            released = False
    except:
        logger.exception("exception in evaluate thread")
    finally:
        if not released:
            SPAWN_AGENT_LOCK.release()
    return accuracy, precision


def crossover(individual1, individual2, toolbox, gene_config):

    child1, child2 = [dict(toolbox.clone(ind))
                      for ind in (individual1, individual2)]

    for node in individual1.keys():
        for key in individual1[node].keys():
            parent_values = [individual1[node][key], individual2[node][key]]
            quartiles = np.percentile(parent_values, [25, 75])
            
            # if variable is continuous, round to 4 decimals
            # otherwise, round to integer value
            if gene_config[key]['step'] == 0: 
                child1[node][key] = round(quartiles[0], 4)
                child2[node][key] = round(quartiles[1], 4)
            else:
                child1[node][key] = round(quartiles[0])
                child2[node][key] = round(quartiles[1])

            # clip values to range provided in gene_config
            child1[node][key] = min(child1[node][key], gene_config[key]['stop'])
            child1[node][key] = max(child1[node][key], gene_config[key]['start'])
            
            child2[node][key] = min(child2[node][key], gene_config[key]['stop'])
            child2[node][key] = max(child2[node][key], gene_config[key]['start'])
            
    return creator.Individual(child1), creator.Individual(child2)


def mutate(individual: dict, toolbox, gene_config, mu: float = 0.0, sigma: float = 0.1):
    """Mutate an individual by applying an offset sampled from a gaussian distribution
    centered at mu, with std deviation sigma

    Args:
        individual (dict): starting point
        toolbox (_type_): toolbox
        mu (float, optional): center of distribution. Defaults to 0.0.
        sigma (float, optional): standard deviation of distribution. Defaults to 0.1.

    Returns:
        creator.Individual: the mutated individual
    """
    new_individual = toolbox.gen_individual()
    # del new_individual.fitness.values

    # Mutate a float individual by adding Gaussian noise
    for node in individual:
        for k in individual[node]:
            logger.debug(
                f'mutating {k} from node({node}) on individual {individual}')
            new_individual[node][k] = mutate_variable(
                val=individual[node][k], key=k, mu=mu, sigma=sigma, gene_config=gene_config)

    return creator.Individual(new_individual),


def mutate_variable(val: Union[float, int], key: str, mu: float, sigma: float, gene_config: dict) -> float:
    """Mutate a variable on an individual, using gaussian noise. Performs bound checking on variable

    Args:
        val (float): initial value
        key (str): variable name
        mu (int, optional): center of gaussian noise. Defaults to 0.
        sigma (float, optional): percent deviation. Will be scaled by the maximum allowed value for each variable. Defaults to 0.1 (e.g. 10%).

    Returns:
        Union[float, int]: new value
    """
    # if key == 'recall_threshold':
    #     val = val + random.gauss(mu=mu, sigma=sigma*MAX_RT_LIMIT)
    #     val = round(max(min(val, 0.9999), 0.0001), 4)
    # elif key == 'max_predictions':
    #     val = val + random.gauss(mu=mu, sigma=sigma*MAX_PRED_LIMIT)
    #     val = round(max(min(val, MAX_PRED_LIMIT), 1))
    # return val

    # Check if continous variable, and round to integer if it is
    trunc = 4 if gene_config[key] == 0 else None

    upper_bound = gene_config[key]["stop"]
    lower_bound = gene_config[key]["start"]
    val = val + random.gauss(mu=mu, sigma=sigma*upper_bound)

    val = round(val, trunc)
    val = max(min(val, upper_bound), lower_bound)
    
    return val


