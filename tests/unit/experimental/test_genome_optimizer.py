"""Unit tests for the genome_optimizer module."""
import pytest
import sys
import os
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))

from ia.gaius.experimental.genome_optimizer import (
    GenomeOptimizer, generate_gene_data, evaluate, crossover, mutate, mutate_variable
)

# Mock classes
class MockAgentManager:
    def __init__(self):
        self.current_agents = {}
        self.hoster_started = False
    
    def start_hoster(self):
        self.hoster_started = True
    
    def kill_all_agents(self):
        self.current_agents = {}
    
    def remediate_dead_agents(self):
        pass
    
    def delete_agent(self, agent_name):
        if agent_name in self.current_agents:
            del self.current_agents[agent_name]
    
    def agent_context(self, genome_file, user_id, agent_id, agent_name):
        class AgentContext:
            def __init__(self, bottle_info):
                self._bottle_info = bottle_info
        
        class ContextManager:
            def __init__(self):
                bottle_info = {
                    'api_key': 'test-key',
                    'name': agent_name,
                    'domain': 'test.com',
                    'secure': False
                }
                self.agent = AgentContext(bottle_info)
            
            def __enter__(self):
                return self.agent
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
        
        self.current_agents[agent_name] = True
        return ContextManager()

class MockPVT:
    def __init__(self, agent=None, **kwargs):
        self.agent = agent
        self.testing_log = [[['test', 0.1, {'overall_metrics': {
            'accuracy': {'hive': 0.8},
            'precision': {'hive': 0.7}
        }}]]]
    
    def conduct_pvt(self):
        pass

class MockAgentClient:
    def __init__(self, bottle_info, **kwargs):
        self._bottle_info = bottle_info
        self._connected = False
    
    def connect(self):
        self._connected = True
    
    def change_genes(self, gene_data, nodes=None):
        pass
    
    def set_summarize_for_single_node(self, value):
        pass
    
    def clear_all_memory(self):
        pass
    
    def get_kbs_as_json(self, ids=False, obj=True):
        return {
            'P1': {
                'symbols_kb': {'symbol1': {}, 'symbol2': {}},
                'models_kb': {'model1': {}, 'model2': {}}
            }
        }
    
    def load_kbs_from_json(self, obj):
        pass

# Test fixtures
@pytest.fixture
def gene_config():
    return {
        'recall_threshold': {'start': 0.001, 'stop': 0.999, 'step': 0},
        'max_predictions': {'start': 1, 'stop': 100, 'step': 1}
    }

@pytest.fixture
def mock_optimizer():
    with patch('ia.gaius.experimental.genome_optimizer.AgentManager', return_value=MockAgentManager()):
        optimizer = GenomeOptimizer(
            path_to_original_genome='test_genome.json',
            nodes_to_optimize=['P1'],
            pvt_config={'test_param': 'test_value'},
            gene_config={
                'recall_threshold': {'start': 0.001, 'stop': 0.999, 'step': 0},
                'max_predictions': {'start': 1, 'stop': 100, 'step': 1}
            },
            evolutionary_params={
                'npop': 10,
                'ngen': 5,
                'cxpb': 0.5,
                'mutpb': 0.2
            },
            agent_constructor=MockAgentClient,
            pvt_constructor=MockPVT
        )
        return optimizer

def test_generate_gene_data(gene_config):
    """Test generating gene data according to config."""
    result = generate_gene_data(gene_config)
    
    # Check that recall_threshold is within range and is a float
    assert 0.001 <= result['recall_threshold'] <= 0.999
    assert isinstance(result['recall_threshold'], float)
    
    # Check that max_predictions is within range and is an integer
    assert 1 <= result['max_predictions'] <= 100
    assert isinstance(result['max_predictions'], int)

def test_mutate_variable(gene_config):
    """Test mutation of individual variables."""
    # Test continuous variable mutation (recall_threshold)
    rt_value = 0.5
    new_rt = mutate_variable(
        val=rt_value,
        key='recall_threshold',
        mu=0.0,
        sigma=0.1,
        gene_config=gene_config
    )
    
    # Check that it changed but is still within bounds
    assert new_rt != rt_value
    assert 0.001 <= new_rt <= 0.999
    assert isinstance(new_rt, float)
    
    # Test discrete variable mutation (max_predictions)
    mp_value = 50
    new_mp = mutate_variable(
        val=mp_value,
        key='max_predictions',
        mu=0.0,
        sigma=0.1,
        gene_config=gene_config
    )
    
    # Check that it changed but is still within bounds
    assert 1 <= new_mp <= 100
    assert isinstance(new_mp, int)

def test_individual_mutation(mock_optimizer, monkeypatch):
    """Test mutation of a complete individual."""
    # Create a test individual
    individual = {'P1': {'recall_threshold': 0.5, 'max_predictions': 50}}
    
    # Mock the gen_individual function to return a predictable result
    def mock_gen_individual(*args, **kwargs):
        return {'P1': {'recall_threshold': 0.6, 'max_predictions': 60}}
    
    monkeypatch.setattr(mock_optimizer.toolbox, 'gen_individual', mock_gen_individual)
    
    # Test mutation
    result, = mutate(
        individual=individual,
        toolbox=mock_optimizer.toolbox,
        gene_config=mock_optimizer.gene_config,
        mu=0.0,
        sigma=0.1
    )
    
    # Check result
    assert result['P1']['recall_threshold'] == 0.6
    assert result['P1']['max_predictions'] == 60

def test_crossover_operation(mock_optimizer):
    """Test crossover between two individuals."""
    # Create parent individuals
    parent1 = {'P1': {'recall_threshold': 0.2, 'max_predictions': 20}}
    parent2 = {'P1': {'recall_threshold': 0.8, 'max_predictions': 80}}
    
    # Create toolbox mock that returns the original individual
    mock_optimizer.toolbox.clone = lambda x: dict(x)
    
    # Test crossover
    child1, child2 = crossover(
        individual1=parent1,
        individual2=parent2,
        toolbox=mock_optimizer.toolbox,
        gene_config=mock_optimizer.gene_config
    )
    
    # Check that children have values between parents (based on quartiles)
    # Since our crossover uses 25% and 75% quartiles
    assert child1['P1']['recall_threshold'] <= child2['P1']['recall_threshold']
    assert child1['P1']['max_predictions'] <= child2['P1']['max_predictions']
    
    # Check that children are within bounds
    assert 0.001 <= child1['P1']['recall_threshold'] <= 0.999
    assert 0.001 <= child2['P1']['recall_threshold'] <= 0.999
    assert 1 <= child1['P1']['max_predictions'] <= 100
    assert 1 <= child2['P1']['max_predictions'] <= 100

def test_evaluate_function(gene_config):
    """Test the evaluate function."""
    # Create mock objects
    agent_manager = MockAgentManager()
    individual = {'P1': {'recall_threshold': 0.5, 'max_predictions': 50}}
    pvt_config = {'test_config': 'value'}
    
    # Run evaluation
    accuracy, precision = evaluate(
        individual=individual,
        am=agent_manager,
        agent_constructor=MockAgentClient,
        agent_kwargs=None,
        pvt_config=pvt_config,
        genome_path='test_genome.json',
        pvt_constructor=MockPVT,
        nodes_to_optimize=['P1']
    )
    
    # Check results (from our mock PVT)
    assert accuracy == 0.8
    assert precision == 0.7
    
    # Check agent was created and cleaned up
    assert len(agent_manager.current_agents) == 1

def test_generate_individual(mock_optimizer):
    """Test generating a random individual."""
    individual = mock_optimizer.generate_individual(nodes_to_optimize=['P1'])
    
    # Check structure
    assert 'P1' in individual
    assert 'recall_threshold' in individual['P1']
    assert 'max_predictions' in individual['P1']
    
    # Check value ranges
    assert 0.001 <= individual['P1']['recall_threshold'] <= 0.999
    assert 1 <= individual['P1']['max_predictions'] <= 100

def test_evolve_process(mock_optimizer, monkeypatch):
    """Test the evolution process."""
    # Mock the algorithms.eaSimple function to avoid actual evolution
    def mock_ea_simple(*args, **kwargs):
        # Return a mock population and logbook
        population = [
            {'P1': {'recall_threshold': 0.5, 'max_predictions': 50}}
        ]
        logbook = {'gen': 1, 'nevals': 1, 'avg': 0.8, 'min': 0.7, 'max': 0.9}
        return population, logbook
    
    # Apply the mock
    monkeypatch.setattr('ia.gaius.experimental.genome_optimizer.algorithms.eaSimple', mock_ea_simple)
    
    # Run evolution
    result = mock_optimizer.evolve()
    
    # Check result
    assert len(result) == 2
    population, logbook = result
    assert isinstance(population, list)
    assert len(population) > 0
    assert isinstance(logbook, dict)

def test_multiprocessed_evolve(mock_optimizer, monkeypatch):
    """Test multiprocessed evolution."""
    # Mock the evolve method to avoid actual evolution
    def mock_evolve(pool=None):
        # Return a mock population and logbook
        population = [
            {'P1': {'recall_threshold': 0.5, 'max_predictions': 50}}
        ]
        logbook = {'gen': 1, 'nevals': 1, 'avg': 0.8, 'min': 0.7, 'max': 0.9}
        return population, logbook
    
    # Apply the mock
    monkeypatch.setattr(mock_optimizer, 'evolve', mock_evolve)
    
    # Run multiprocessed evolution with limited cores
    result = mock_optimizer.multiprocessed_evolve(n_proc=1)
    
    # Check result
    assert len(result) == 2
    population, logbook = result
    assert isinstance(population, list)
    assert len(population) > 0
    assert isinstance(logbook, dict)
    
    # Verify hoster was started
    assert mock_optimizer.am.hoster_started is True
