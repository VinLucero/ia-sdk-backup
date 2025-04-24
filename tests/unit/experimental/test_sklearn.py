"""Unit tests for the sklearn integration module."""
import pytest
import sys
import os
import numpy as np
import pandas as pd
from unittest.mock import Mock, patch, MagicMock

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../src')))

from ia.gaius.experimental.sklearn import (
    GAIuSClassifier, GDFTransformer, GAIuSTransformer, 
    ensemble2vec, make_sklearn_fv, get_feature_names_from_weights
)
from ia.gaius.data_structures import PredictionEnsemble

# Mock classes
class MockAgentManager:
    def __init__(self):
        self.agents = {}
        self.hoster_started = False
    
    def start_hoster(self):
        self.hoster_started = True
        return True
    
    def kill_all_agents(self):
        self.agents = {}
    
    def start_agent(self, genome_name, agent_name, agent_id):
        self.agents[agent_name] = True
        
        class MockAgentObject:
            def get_agent_client(self):
                return MockAgentClient({
                    'api_key': 'test-key',
                    'name': agent_name,
                    'domain': 'test.com',
                    'secure': False
                })
        
        return MockAgentObject()

class MockPrediction:
    def __init__(self, prediction_data):
        self._prediction = prediction_data

class MockAgentClient:
    def __init__(self, bottle_info):
        self._bottle_info = bottle_info
        self._connected = False
        self.ingress_nodes = []
        self.query_nodes = []
        self._summarize_for_single_node = True
    
    def connect(self):
        self._connected = True
        return {'connection': 'okay', 'agent': 'test'}
    
    def set_ingress_nodes(self, nodes):
        self.ingress_nodes = nodes
        return nodes
    
    def set_query_nodes(self, nodes):
        self.query_nodes = nodes
        return nodes
    
    def set_summarize_for_single_node(self, value):
        self._summarize_for_single_node = value
    
    def change_genes(self, gene_data):
        return gene_data
    
    def clear_wm(self):
        return 'cleared'
    
    def clear_all_memory(self):
        return 'cleared all'

    def observe(self, data, nodes=None):
        return 'observed'
    
    def stop_predicting(self):
        return 'stopped predicting'
    
    def start_predicting(self):
        return 'started predicting'
    
    def get_predictions(self):
        # Return a mock prediction ensemble
        return {
            'P1': [
                MockPrediction({
                    'matches': ['class1', 'feature1'],
                    'missing': ['feature2'],
                    'name': 'MODEL|model1'
                }),
                MockPrediction({
                    'matches': ['class2'],
                    'missing': [],
                    'name': 'MODEL|model2'
                })
            ]
        }
    
    def learn(self):
        return {'P1': 'MODEL|test_model'}
    
    def get_kbs_as_json(self, ids=False, obj=True):
        return {
            'P1': {
                'symbols_kb': {
                    'class1': {},
                    'class2': {},
                    'feature1': {},
                    'feature2': {}
                },
                'models_kb': {
                    'model1': {},
                    'model2': {}
                }
            }
        }
    
    def remove_symbols_from_system(self, symbols_list):
        return 'removed'
    
    def delete_model(self, model_name):
        return 'deleted'
    
    def load_kbs_from_json(self, obj):
        return 'loaded'

# Test fixtures
@pytest.fixture
def mock_agent_manager():
    return MockAgentManager()

@pytest.fixture
def mock_gaius_classifier():
    with patch('ia.gaius.experimental.sklearn.AgentManager', return_value=MockAgentManager()):
        classifier = GAIuSClassifier(
            recall_threshold=0.1,
            max_predictions=5,
            near_vector_count=3,
            as_vectors=False,
            cv=0,
            shuffle=True,
            pred_as_int=True
        )
        return classifier

@pytest.fixture
def sample_data():
    # Create a small dataset for testing
    X = np.zeros((3, 1), dtype=object)
    X[0][0] = [{'strings': ['feature1', 'feature2'], 'vectors': [], 'emotives': {}}]
    X[1][0] = [{'strings': ['feature1', 'feature3'], 'vectors': [], 'emotives': {}}]
    X[2][0] = [{'strings': ['feature2', 'feature3'], 'vectors': [], 'emotives': {}}]
    
    y = np.array(['class1', 'class2', 'class1'])
    
    return X, y

def test_gaius_classifier_initialization():
    """Test GAIuSClassifier initialization."""
    with patch('ia.gaius.experimental.sklearn.AgentManager', return_value=MockAgentManager()):
        classifier = GAIuSClassifier(
            recall_threshold=0.1,
            max_predictions=5,
            near_vector_count=3
        )
        
        assert classifier.recall_threshold == 0.1
        assert classifier.max_predictions == 5
        assert classifier.near_vector_count == 3
        assert classifier.as_vectors is False
        assert classifier.cv == 0
        assert classifier.agent is not None

def test_gaius_classifier_fit(mock_gaius_classifier, sample_data):
    """Test GAIuSClassifier fit method."""
    X, y = sample_data
    
    # Mock the validation data method to avoid validation errors
    with patch('ia.gaius.experimental.sklearn.validate_data', return_value=True):
        # Fit the classifier
        classifier = mock_gaius_classifier.fit(X, y)
        
        # Check that the classifier was fitted
        assert classifier.classes_ is not None
        assert len(classifier.classes_) == 2
        assert classifier.X_ is not None
        assert classifier.y_ is not None
        assert len(classifier.X_) == len(X)
        assert len(classifier.y_) == len(y)
        
        # Verify that the string classes are stored
        assert 'class1' in classifier.str_classes_
        assert 'class2' in classifier.str_classes_

def test_gaius_classifier_predict(mock_gaius_classifier, sample_data):
    """Test GAIuSClassifier predict method."""
    X, y = sample_data
    
    # First fit the classifier
    with patch('ia.gaius.experimental.sklearn.validate_data', return_value=True):
        mock_gaius_classifier.fit(X, y)
        
        # Mock prediction ensemble utility function
        with patch('ia.gaius.experimental.sklearn.prediction_ensemble_model_classification') as mock_pred:
            # Configure mock to return class1 as most common
            mock_counter = MagicMock()
            mock_counter.most_common.return_value = [('class1', 1)]
            mock_pred.return_value = mock_counter
            
            # Test prediction
            predictions = mock_gaius_classifier.predict(X)
            
            # Verify predictions
            assert len(predictions) == len(X)
            # Since pred_as_int is True and class1 is converted to index 0
            assert predictions[0] == 0

def test_gaius_classifier_predict_proba(mock_gaius_classifier, sample_data):
    """Test GAIuSClassifier predict_proba method."""
    X, y = sample_data
    
    # First fit the classifier
    with patch('ia.gaius.experimental.sklearn.validate_data', return_value=True):
        mock_gaius_classifier.fit(X, y)
        
        # Mock prediction ensemble utility function
        with patch('ia.gaius.experimental.sklearn.prediction_ensemble_model_classification') as mock_pred:
            # Configure mock to return probabilities
            mock_counter = MagicMock()
            mock_counter.get.side_effect = lambda x, default: 0.7 if x == 'class1' else 0.3
            mock_counter.__iter__.return_value = ['class1', 'class2']
            mock_counter.values.return_value = [0.7, 0.3]
            mock_pred.return_value = mock_counter
            
            # Test prediction probabilities
            probas = mock_gaius_classifier.predict_proba(X)
            
            # Verify probabilities
            assert len(probas) == len(X)
            assert probas.shape[1] == 2  # Two classes
            # The actual values are transformed with softmax, so we just check they sum to 1
            assert np.isclose(np.sum(probas[0]), 1.0)

def test_gdf_transformer_initialization():
    """Test GDFTransformer initialization."""
    transformer = GDFTransformer(as_vector=True, drop_zero=True)
    
    assert transformer.as_vector is True
    assert transformer.drop_zero is True
    assert transformer.fit_args == {}

def test_gdf_transformer_fit():
    """Test GDFTransformer fit method."""
    transformer = GDFTransformer()
    
    # Fit with custom args
    fitted = transformer.fit(None, feature_names=['f1', 'f2'])
    
    # Verify args are stored
    assert fitted.fit_args['feature_names'] == ['f1', 'f2']

def test_gdf_transformer_transform():
    """Test GDFTransformer transform method."""
    transformer = GDFTransformer()
    
    # Create simple input data
    X = np.array([[1, 2], [3, 4]])
    
    # Transform without feature names
    with patch('ia.gaius.experimental.sklearn.create_gdf') as mock_gdf:
        mock_gdf.return_value = {'strings': ['test'], 'vectors': [], 'emotives': {}}
        
        result = transformer.transform(X)
        
        # Verify result shape
        assert result.shape == (2, 1)
        assert isinstance(result, np.ndarray)
        
        # Verify create_gdf was called correctly
        calls = mock_gdf.call_args_list
        assert len(calls) == 2
        assert 'strings' in calls[0][1]

def test_gdf_transformer_with_feature_names():
    """Test GDFTransformer transform with feature names."""
    transformer = GDFTransformer()
    
    # Create simple input data
    X = np.array([[1, 2], [3, 4]])
    
    # Transform with feature names
    with patch('ia.gaius.experimental.sklearn.create_gdf') as mock_gdf:
        mock_gdf.return_value = {'strings': ['test'], 'vectors': [], 'emotives': {}}
        
        result = transformer.transform(X, feature_names=['feature1', 'feature2'])
        
        # Verify create_gdf was called with feature names
        calls = mock_gdf.call_args_list
        assert len(calls) == 2
        assert 'strings' in calls[0][1]
        assert 'feature1|1' in str(calls[0][1]['strings'])
        assert 'feature2|2' in str(calls[0][1]['strings'])

def test_gaius_transformer_transform(mock_gaius_classifier, sample_data):
    """Test GAIuSTransformer transform method."""
    X, y = sample_data
    
    # Create a transformer that inherits from GAIuSClassifier
    transformer = GAIuSTransformer(
        recall_threshold=0.1,
        max_predictions=5,
        near_vector_count=3
    )
    
    # Mock the underlying methods
    with patch.object(transformer, '_predict_on_sequence') as mock_predict:
        mock_predict.return_value = {'P1': [MockPrediction({'matches': ['class1'], 'missing': [], 'name': 'MODEL|test'})]}
        
        with patch('ia.gaius.experimental.sklearn.validate_data', return_value=True):
            with patch('ia.gaius.experimental.sklearn.make_sklearn_fv_no_y') as mock_make_fv:
                mock_make_fv.return_value = np.zeros((len(X), 10))
                
                # First fit, then transform
                transformer.fit(X, y)
                result = transformer.transform(X)
                
                # Verify result
                assert result.shape == (len(X), 10)
                assert mock_make_fv.called
                
                # Verify predict_on_sequence was called for each sample
                assert mock_predict.call_count == len(X)

def test_ensemble2vec():
    """Test ensemble2vec utility function."""
    # Create mock prediction ensemble
    prediction = PredictionEnsemble({
        'P1': [
            MockPrediction({
                'matches': ['symbol1', 'symbol2'],
                'missing': [],
                'name': 'MODEL|model1'
            })
        ]
    })
    
    # Define sorted symbol names to use
    sorted_symbols = ['symbol1', 'symbol2', 'symbol3', 'MODEL|model1']
    
    # Call ensemble2vec
    with patch('ia.gaius.experimental.sklearn.flatten', return_value=['symbol1', 'symbol2']):
        result = ensemble2vec(
            ensemble=prediction,
            sorted_symbol_names=sorted_symbols,
            max_predictions=1,
            prediction_fields=['matches', 'missing', 'name']
        )
        
        # Verify result shape
        assert len(result) == len(sorted_symbols) * 3  # 3 prediction fields
        
        # Check that the right indices are set to True
        symbol1_index = 0  # First symbol in matches field
        assert result[symbol1_index] == 1
        
        symbol2_index = 1  # Second symbol in matches field
        assert result[symbol2_index] == 1
        
        model_index = len(sorted_symbols) * 2 + 3  # Model name in the name field (third field)
        assert result[model_index] == 1

def test_make_sklearn_fv():
    """Test make_sklearn_fv utility function."""
    # Create mock ensemble data
    ensemble_data = [
        (
            {'P1': [MockPrediction({'matches': ['class1'], 'missing': [], 'name': 'MODEL|model1'})]},
            ['class1']
        ),
        (
            {'P1': [MockPrediction({'matches': ['class2'], 'missing': [], 'name': 'MODEL|model2'})]},
            ['class2']
        )
    ]
    
    # Create mock KB
    kb = {
        'symbols_kb': {'class1': {}, 'class2': {}},
        'models_kb': {'model1': {}, 'model2': {}}
    }
    
    # Mock the ensemble2vec function
    with patch('ia.gaius.experimental.sklearn.ensemble2vec') as mock_ensemble2vec:
        mock_ensemble2vec.return_value = np.array([1, 0, 0, 1])
        
        # Call make_sklearn_fv
        X, y = make_sklearn_fv(
            ensemble_data=ensemble_data,
            kb=kb,
            max_predictions=1,
            prediction_fields=['matches', 'name']
        )
        
        # Verify result
        assert len(X) == len(ensemble_data)
        assert len(y) == len(ensemble_data)
        assert y[0] == 'class1'
        assert y[1] == 'class2'
        
        # Verify ensemble2vec was called for each ensemble
        assert mock_ensemble2vec.call_count == len(ensemble_data)

def test_get_feature_names_from_weights():
    """Test get_feature_names_from_weights utility function."""
    # Create mock coefficients and KB
    coefficients = np.array([[0.5, 0.1, 0.0, 0.2]])
    kb = {
        'symbols_kb': {'symbol1': {}, 'symbol2': {}},
        'models_kb': {'model1': {}, 'model2': {}}
    }
    
    # Mock some of the internal functions to avoid complexity
    with patch('ia.gaius.experimental.sklearn.floor', side_effect=lambda x: int(x)):
        with patch('ia.gaius.experimental.sklearn.deepcopy', side_effect=lambda x: x):
            # Call the function
            result = get_feature_names_from_weights(
                coefficients=coefficients,
                kb=kb,
                prediction_fields=['matches', 'missing']
            )
            
            # Verify structure of result
            assert isinstance(result, dict)
            assert 0 in result
            assert 'models' in result[0]
            assert 'symbols' in result[0]

# Test helper functions
def test_max_magnitude():
    """Test max_magnitude utility function."""
    from ia.gaius.experimental.sklearn import max_magnitude
    
    # Test with positive numbers
    assert max_magnitude(5, 3) == 5
    
    # Test with negative numbers
    assert max_magnitude(-5, -3) == -5
    
    # Test with mixed numbers
    assert max_magnitude(-5, 3) == -5
    assert max_magnitude(5, -7) == -7
