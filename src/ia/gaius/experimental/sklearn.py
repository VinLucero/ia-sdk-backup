import heapq
import statistics
import time
import uuid
from collections import Counter, defaultdict
from copy import deepcopy
from math import floor
from sys import stdout
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.special import softmax
from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import KFold, cross_val_score
from sklearn.utils.multiclass import unique_labels
from sklearn.utils.validation import check_array, check_is_fitted, check_X_y
from tqdm.auto import tqdm

from ia.gaius.data_ops import validate_data
from ia.gaius.data_structures import PredictionEnsemble
from ia.gaius.manager import AgentManager
from ia.gaius.prediction_models import (
    most_common_ensemble_model_classification,
    prediction_ensemble_model_classification)
from ia.gaius.utils import create_gdf


def n_smallest_magnitude_keys(my_dict, n):
    # Create a heap of (magnitude, key) tuples
    heap = [(abs(value), key) for key, value in my_dict.items()]
    heapq.heapify(heap)

    # Get the first n elements from the heap
    smallest_n = heapq.nsmallest(n, heap)

    # Extract the keys from the tuples
    result = [key for _, key in smallest_n]

    return result

# starting_model_count = len(agent.get_kbs_as_json(ids=False, obj=True)['P1']['models_kb'])


def get_weakest_symbols(features: dict) -> Dict[str, float]:
    """Get symbols to delete, from features dict output of "split_feature_weights_by_key"

    Args:
        features (dict): _description_

    Returns:
        List[str]: dict of symbols to their (max) corresponding weight across all classifications in the linear model
    """
    symbol_weights_dict = Counter()

    for sym_features in features.values():
        for pred_index in sym_features:
            for key, symbol_fields in sym_features[pred_index].items():
                for sym_counter in symbol_fields.values():
                    for sym, val in sym_counter.items():
                        if f'{key}|{sym}' not in symbol_weights_dict:
                            symbol_weights_dict[f'{key}|{sym}'] = val
                        else:
                            symbol_weights_dict[f'{key}|{sym}'] = max_magnitude(
                                symbol_weights_dict[f'{key}|{sym}'], val)

    syms_to_drop = symbol_weights_dict

    return syms_to_drop


def get_weakest_models(features: dict) -> Dict[str, float]:
    """Get models to delete, from features dict output of "split_feature_weights_by_key"

    Args:
        features (dict): _description_

    Returns:
        List[str]: dict of models to their (max) corresponding weight across all classifications in the linear model
    """
    model_weights_dict = Counter()

    for sym_features in features.values():
        for pred_index in sym_features:
            for symbol_fields in sym_features[pred_index].values():
                for sym_counter in symbol_fields.values():
                    for sym, val in sym_counter.items():
                        if sym not in model_weights_dict:
                            model_weights_dict[sym] = val
                        else:
                            model_weights_dict[sym] = max_magnitude(
                                model_weights_dict[sym], val)

    models_to_drop = model_weights_dict

    return models_to_drop


class GAIuSClassifier(BaseEstimator, ClassifierMixin):
    """GAIuS Classifier using a single node, for use with Scikit-Learn"""

    def __init__(self,
                 recall_threshold: float = 0.1,
                 max_predictions: int = 10,
                 near_vector_count: int = 5,
                 as_vectors: bool = False,
                 cv: int = 0,
                 shuffle: bool = True,
                 pred_as_int: bool = True):
        """Initialize GAIuSClassifier

        Args:
            recall_threshold (float, optional): _description_. Defaults to 0.1.
            max_predictions (int, optional): _description_. Defaults to 10.
            near_vector_count (int, optional): _description_. Defaults to 5.
            cv (int, optional): Whether to perform dreamer during fit, using cross validation splits. If cv <=0, no dreamer performed. Defaults to 0.
            shuffle (bool, optional): Whether to shuffle the cv splits. Defaults to True.
        """

        self.recall_threshold = recall_threshold
        self.max_predictions = max_predictions
        self.near_vector_count = near_vector_count
        self.as_vectors = as_vectors
        self.cv = cv
        self.shuffle = shuffle
        self.pred_as_int = pred_as_int

        self.am = AgentManager()
        self.am.start_hoster()
        # self.am.kill_all_agents()
        self.uuid_extension = uuid.uuid4().hex[:4]
        self.unique_agent_name = f"classif-{self.uuid_extension}"
        self.agent = self.am.start_agent(genome_name="simple.genome",
                                         agent_name=self.unique_agent_name,
                                         agent_id=self.unique_agent_name).get_agent_client()

        time.sleep(2.0)
        self.agent.connect()
        self.agent.set_ingress_nodes(["P1"])
        self.agent.set_query_nodes(["P1"])
        self.agent.set_summarize_for_single_node(False)

        self.agent.change_genes({'SORT': False,
                                 'max_predictions': max_predictions,
                                 'recall_threshold': recall_threshold,
                                 'near_vector_count': near_vector_count})
        self.classes_ = None
        self.X_ = None
        self.y_ = None
        self.cv_predictions = None
        self.cv_actuals = None
        self.cv_sequences = None
        self.dreamer_results = None

    # Deleting (Calling destructor)

    def _learn_sequence(self, sequence: List[dict], label) -> dict:
        """_summary_

        Args:
            sequence (List[dict]): _description_
            label (_type_): _description_
        """
        self.agent.clear_wm()
        for event in sequence:
            self.agent.observe(event)
        label_gdf = create_gdf(strings=[str(label)])
        self.agent.observe(label_gdf)
        return self.agent.learn()

    def _predict_on_sequence(self, sequence: List[dict]) -> dict:
        """Take in a gdf sequence, and get predictions when observing the last event

        Args:
            sequence (List[dict]): _description_

        Returns:
            dict: prediction ensemble
        """
        self.agent.clear_wm()

        if len(sequence) > 1:
            self.agent.stop_predicting()
        for gdf in sequence[:-1]:
            self.agent.observe(gdf)

        self.agent.start_predicting()
        self.agent.observe(sequence[-1])

        ensemble = self.agent.get_predictions()
        return ensemble

    def __drop_symbols_and_models(self, kb: dict, sym_features, mod_features):
        max_symbol_drop_count = int(
            0.10 * len(kb['P1']['symbols_kb']))
        max_model_drop_count = int(
            0.10 * len(kb['P1']['models_kb']))

        symbols_to_drop = get_weakest_symbols(features=sym_features)
        symbols_to_drop: List[tuple] = sorted(
            symbols_to_drop.items(), key=lambda x: abs(x[1]))
        symbols_to_drop = list(
            filter(lambda x: abs(x[1]) < 0.5, symbols_to_drop))
        if len(symbols_to_drop) > max_symbol_drop_count:
            symbols_to_drop = symbols_to_drop[:max_symbol_drop_count]
        symbols_to_drop = [sym[0] for sym in symbols_to_drop]

        print(f'Symbols to drop: {symbols_to_drop}')
        print(f'status before dropping symbols: {self.agent.show_status()}')

        self.agent.remove_symbols_from_system(symbols_list=symbols_to_drop)

        print(f'status after dropping symbols: {self.agent.show_status()}')

        models_to_drop = get_weakest_models(features=mod_features)
        models_to_drop = sorted(models_to_drop.items(),
                                key=lambda x: abs(x[1]))
        models_to_drop = list(
            filter(lambda x: abs(x[1]) < 0.5, models_to_drop))
        if len(models_to_drop) > max_model_drop_count:
            models_to_drop = models_to_drop[:max_model_drop_count]
        models_to_drop = [sym[0] for sym in models_to_drop]

        print(f'Models to drop: {models_to_drop}')
        print(f'status before dropping models: {self.agent.show_status()}')

        for mod in models_to_drop:
            self.agent.delete_model(mod)

    def _dreamer_fit(self, sequences: List[List[dict]], ensembles: List[dict], actuals: List[str]):

        # setup SGD classifier to model prediction ensembles.
        # Use high alpha to increase regularization
        sgd_classifier = SGDClassifier(loss='log_loss',
                                       random_state=42,
                                       penalty='elasticnet',
                                       l1_ratio=0.15,
                                       alpha=0.001,
                                       max_iter=5000)

        CHOSEN_PREDICTION_FIELDS = ['matches', 'missing', 'name']

        self.dreamer_results = {}
        ensemble_data = list(zip(ensembles, actuals))

        for i in range(10):
            self.dreamer_results[i] = {}
            self.dreamer_results[i]['before_kb'] = self.agent.get_kbs_as_json(
                ids=False, obj=True)
            self.dreamer_results[i]['before_ensemble_data'] = deepcopy(
                ensemble_data)
            X, y = make_sklearn_fv(ensemble_data=ensemble_data,
                                   kb=self.dreamer_results[i]['before_kb']['P1'],
                                   max_predictions=self.max_predictions,
                                   prediction_fields=CHOSEN_PREDICTION_FIELDS)
            sgd_classifier.fit(X, y)
            features = get_feature_names_from_weights(coefficients=sgd_classifier.coef_,
                                                      kb=self.dreamer_results[i]['before_kb']['P1'],
                                                      prediction_fields=CHOSEN_PREDICTION_FIELDS)

            self.dreamer_results[i]['features'] = deepcopy(features)

            sym_features = {}
            mod_features = {}
            for feature_num in features:
                sym_features[feature_num] = split_feature_weights_by_key(
                    features[feature_num]['symbols'])

            for feature_num in features:
                mod_features[feature_num] = split_feature_weights_by_key(
                    features[feature_num]['models'])

            self.dreamer_results[i]['sym_features'] = deepcopy(sym_features)
            self.dreamer_results[i]['mod_features'] = deepcopy(mod_features)

            self.__drop_symbols_and_models(kb=self.dreamer_results[i]['before_kb'],
                                           sym_features=sym_features,
                                           mod_features=mod_features)

            self.dreamer_results[i]['after_kb'] = self.agent.get_kbs_as_json(
                ids=False, obj=True)
            self.agent.load_kbs_from_json(
                obj=self.dreamer_results[i]['after_kb'])

            new_predictions = []
            for sequence in tqdm(sequences):
                new_predictions.append(
                    self._predict_on_sequence(sequence=sequence))

            ensemble_data = list(zip(new_predictions, actuals))
            self.dreamer_results[i]['after_ensemble_data'] = ensemble_data
            self.dreamer_results[i]['after_model_count'] = len(
                self.dreamer_results[i]['after_kb']['P1']['models_kb'])
            self.dreamer_results[i]['pvt_predictions'] = new_predictions
            self.dreamer_results[i]['pvt_actuals'] = actuals
            print(
                f'after deleting models, model count = {self.dreamer_results[i]["after_model_count"]}')
            if (not any(actuals)) or (not any(new_predictions)):
                print(
                    f'breaking on iteration {i}, {actuals=}, {new_predictions=}')
                break
            self.dreamer_results[i]['after_accuracy'] = accuracy_score([act[0] if act else 'None' for act in actuals], [
                str(most_common_ensemble_model_classification(p['P1'])) if p else 'None' for p in new_predictions])
            X, y = make_sklearn_fv(ensemble_data=ensemble_data,
                                   kb=self.dreamer_results[i]['after_kb']['P1'],
                                   max_predictions=self.max_predictions,
                                   prediction_fields=CHOSEN_PREDICTION_FIELDS)

            # Perform cross-validation
            num_folds = self.cv  # You can adjust the number of folds as needed
            cv_scores = cross_val_score(sgd_classifier,
                                        X,
                                        y,
                                        cv=num_folds,
                                        scoring='accuracy',
                                        verbose=2)

            # Print the cross-validation scores
            print(f"Cross-Validation Scores for iteration {i}: {cv_scores}")
            print(
                f"Mean Accuracy for iteration {i}: {np.mean(cv_scores):3.2f}")

            self.dreamer_results[i]['after_classifier_accuracy'] = np.mean(
                cv_scores)

            sgd_classifier.fit(X, y)

    def fit(self, X: np.ndarray, y: np.ndarray):

        # Check that X and y have correct shape
        X, y = check_X_y(X, y, dtype=object)

        # Store the classes seen during fit
        self.classes_ = unique_labels(y)
        self.str_classes_ = [str(c) for c in self.classes_]

        self.X_ = X
        self.y_ = y
        self.cv_predictions = None
        self.cv_actuals = None
        self.cv_sequences = None
        self.dreamer_results = None

        for row in self.X_:
            for gdf in row[0]:
                if not validate_data(data=gdf):
                    raise ValueError(f"Bad gdf found in sequence: {gdf=}")

        if self.cv > 0:
            self.cv_predictions = []
            self.cv_actuals = []
            self.cv_sequences = []

            kf = KFold(n_splits=self.cv, shuffle=self.shuffle)
            for j, (train, test) in enumerate(tqdm(kf.split(self.X_), total=self.cv, leave=False)):
                X_train, X_test, y_train, y_test = X[train], X[test], y[train], y[test]
                self.agent.clear_all_memory()
                self.agent.stop_predicting()
                for i, seq in enumerate(tqdm(X_train, leave=False, desc=f'CV Split {j} training')):
                    self._learn_sequence(sequence=seq[0], label=y_train[i])

                for seq in tqdm(X_test, leave=False, desc=f'CV Split {j} testing'):
                    ensemble = self._predict_on_sequence(sequence=seq[0])
                    self.cv_predictions.append(ensemble)
                    self.cv_sequences.append(seq[0])

                self.cv_actuals.extend(y_test.tolist())

        # at the end, re-train entire agent
        # use predictions, actual values to fit linear model,
        # and prune unimportant symbols
        self.agent.clear_all_memory()
        self.agent.stop_predicting()
        original_models = set()
        for i, seq in enumerate(tqdm(self.X_, leave=False)):
            original_models.add(self._learn_sequence(
                sequence=seq[0], label=self.y_[i])['P1'])

        if self.as_vectors:
            new_models = set()
            for i, seq in enumerate(tqdm(self.X_, leave=False)):
                new_models.add(self._learn_sequence(
                    sequence=seq[0], label=self.y_[i])['P1'])

            original_models.difference_update(new_models)
            for model in original_models:
                self.agent.delete_model(model)

        self.agent.start_predicting()

        # dream if using cv
        if self.cv > 0:
            self._dreamer_fit(sequences=self.cv_sequences,
                              ensembles=self.cv_predictions,
                              actuals=self.cv_actuals)

        # Return the classifier
        return self

    def predict(self, X: np.ndarray):

        # Check if fit has been called
        check_is_fitted(self)

        # Input validation
        X = check_array(X, dtype=object)

        output = []
        self.agent.start_predicting()
        pbar = tqdm(X, leave=False)
        for seq in pbar:
            ensemble = self._predict_on_sequence(sequence=seq[0])
            try:
                classif = prediction_ensemble_model_classification(
                    ensemble['P1']).most_common()[0][0]
                if self.pred_as_int and (classif in self.str_classes_):
                    classif = self.str_classes_.index(classif)
            except Exception:
                classif = -1
            output.append(classif)
        del pbar
        return np.array(output)

    def predict_proba(self, X: np.ndarray):
        print('in predict_proba')
        # Check if fit has been called
        check_is_fitted(self)

        # Input validation
        X = check_array(X, dtype=object)

        output = []
        for seq in X:
            ensemble = self._predict_on_sequence(sequence=seq[0])
            classif_dict = prediction_ensemble_model_classification(ensemble['P1'])
            total = sum(classif_dict.values(), 0.0)

            for key in classif_dict:
                classif_dict[key] /= total

            # get probabilities for each class in self.classes_. Default to 0.0
            probs = [classif_dict.get(str(classif), 0.0)
                     for classif in self.classes_]
            output.append(softmax(probs))

        return np.array(output)


class GDFTransformer(BaseEstimator, TransformerMixin):
    """Transform dataset from numerical data into GDF format (each record is a list of GDFs)
    """

    def __init__(self, as_vector: bool = False, drop_zero=False):
        self.as_vector = as_vector
        self.drop_zero = drop_zero
        self.fit_args = {}

    def fit(self, X, y=None, **kwargs):
        self.fit_args = kwargs
        return self

    def transform(self, X: np.ndarray, y=None, feature_names: List[str] = None):
        _X = X
        # print(f'Input shape: {X.shape}')
        pd_feature_names = None
        if isinstance(X, pd.DataFrame):
            _X = X.values
            pd_feature_names = X.columns.tolist()

        if feature_names is None:
            if 'feature_names' in self.fit_args:
                feature_names = self.fit_args['feature_names']
            elif pd_feature_names is not None:
                feature_names = pd_feature_names
            else:
                feature_names = [str(i) for i in range(_X.shape[1])]

        if len(feature_names) != _X.shape[1]:
            raise Exception(
                f"length of feature_names ({len(feature_names)}) does not match data shape ({_X.shape[1]})")

        new_X = np.zeros(shape=(_X.shape[0], 1), dtype=object)

        row: np.ndarray
        for i, row in enumerate(tqdm(_X, leave=False)):
            if not isinstance(row, np.ndarray):
                row = row.toarray().flatten()
            if self.as_vector:
                new_X[i][0] = [create_gdf(vectors=[row.tolist()])]
            elif self.drop_zero:
                new_X[i][0] = [create_gdf(
                    strings=[f'{one}|{two}' for one, two in zip(feature_names, row.tolist()) if two])]
            else:
                new_X[i][0] = [create_gdf(
                    strings=[f'{one}|{two}' for one, two in zip(feature_names, row.tolist())])]
        # todo convert input rows into gdf format
        return new_X


class GAIuSTransformer(GAIuSClassifier, TransformerMixin):
    """Treat a simple GAIuS Agent as a way to feature extract on data. Input is expected
    to be from GDFTransformer, output is a flattened prediction ensemble feature vector

    Args:
        GAIuSClassifier (_type_): Simple GAIuS Classifier
        TransformerMixin (_type_): Sklearn mixin
    """
    def transform(self, X, y=None):
        # Check if fit has been called
        check_is_fitted(self)

        # Input validation
        X = check_array(X, dtype=object)

        CHOSEN_PREDICTION_FIELDS = ['matches', 'missing', 'name']
        ensembles = []

        self.agent.start_predicting()
        pbar = tqdm(X, leave=False)
        for seq in pbar:
            ensemble = self._predict_on_sequence(sequence=seq[0])

            ensembles.append(ensemble)

        del pbar

        kb = self.agent.get_kbs_as_json(ids=False,
                                        obj=True)

        X = make_sklearn_fv_no_y(ensemble_data=ensembles,
                                 kb=kb['P1'],
                                 max_predictions=self.max_predictions,
                                 prediction_fields=CHOSEN_PREDICTION_FIELDS)

        return X


def make_sklearn_fv_no_y(ensemble_data: List[Dict[str, dict]], kb: Dict[str, dict], max_predictions: int = 5, prediction_fields: List[str] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Make Ensemble feature vectors from a list of (ensemble, actual) tuples.
    This gets the Agent prediction ensemble output into the proper format for ingest into a Scikit learn classifier (to model the output of GAIuS)

    Args:
        ensemble_data (List[Tuple[Dict[str, dict], List[List[str]]]]): Corresponds to zip of pvt.predictions and pvt.actuals
        kb (Dict[str, dict]): _description_
        max_predictions (int, optional): _description_. Defaults to 5.
        prediction_fields (List[str], optional): _description_. Defaults to None.

    Returns:
        Tuple[np.ndarray, np.ndarray]: Feature Vectors, Actual Label arrays in expected Scikit-learn formats
    """

    if prediction_fields is None:
        prediction_fields = ["matches", "missing", "name"]

    prediction_field_count = len(prediction_fields)

    if 'name' in prediction_fields:
        sorted_symbol_names = list(
            kb['symbols_kb'].keys()) + [f'MODEL|{val}' for val in kb['models_kb'].keys()]
    else:
        sorted_symbol_names = list(kb['symbols_kb'].keys())
    sorted_symbol_names = sorted(sorted_symbol_names)

    total_length = prediction_field_count * \
        max_predictions * (len(sorted_symbol_names))

    sparse_array = None
    for ensemble in tqdm(ensemble_data, leave=False):
        if sparse_array is None:
            sparse_array = sp.csr_array(ensemble2vec(ensemble=PredictionEnsemble(ensemble),
                                                     sorted_symbol_names=sorted_symbol_names,
                                                     max_predictions=max_predictions,
                                                     prediction_fields=prediction_fields),
                                        (1, total_length),
                                        dtype=np.bool_)
        else:
            sparse_array = sp.vstack((sparse_array,
                                      sp.csr_array(ensemble2vec(ensemble=PredictionEnsemble(ensemble),
                                                                sorted_symbol_names=sorted_symbol_names,
                                                                max_predictions=max_predictions,
                                                                prediction_fields=prediction_fields),
                                                   dtype=np.bool_)),
                                     dtype=np.bool_)

    return sparse_array


def flatten(l: List[List[str]]) -> List[str]:
    """Flatten list of lists into a single list

    Args:
        l (List[List[str]]): _description_

    Returns:
        List[str]: _description_
    """
    return [item for sublist in l for item in sublist]


def ensemble2vec(ensemble: PredictionEnsemble, sorted_symbol_names: List[str], max_predictions: int = 5, prediction_fields: List[str] = None) -> np.ndarray:
    """Get a sparse 'presence' vector that depicts whether the symbol was present in prediction

    Args:
        ensemble (PredictionEnsemble): Prediction Ensemble to vectorize
        sorted_symbol_names (List[str]): list of all symbols possibly present (symbols from symbols_kb + model names, sorted)
        max_predictions (int, optional): max number of predictions to include in the feature vector. Defaults to 5.
        prediction_fields (List[str], optional): Which fields to extract from prediction objects to make feature vector. Defaults to None.

    Raises:
        Exception: Indexing out of bounds

    Returns:
        np.ndarray: feature vector

    Example:

              Prediction 1                                | Prediction 2
              MATCHES_10k   MISSING_10k     MODEL_NAMES   | MATCHES MISSING MODEL_NAMES
        vec = HELLO         WORLD           MODEL|123214  | HELLO           MODEL|21341

    """

    nodes = list(ensemble.ensemble.keys())
    assert len(nodes) == 1  # for now only supporting the "simple" case

    if prediction_fields is None:
        prediction_fields = ["matches", "missing", "future"]

    prediction_field_count = len(prediction_fields)
    prediction_feature_count = len(sorted_symbol_names)

    single_pred_feature_length = prediction_field_count * \
        (prediction_feature_count)
    total_length = prediction_field_count * \
        max_predictions * (prediction_feature_count)

    resultant_vector = np.zeros(total_length, dtype=np.bool_)

    for i, pred in enumerate(ensemble.ensemble[nodes[0]]):
        if i >= max_predictions:
            break

        for j, field in enumerate(prediction_fields):
            field_data = pred._prediction[field]
            if field == "name":
                field_data = [f'MODEL|{field_data}']

            if not field_data:
                continue
            if isinstance(field_data[0], list):
                field_data = flatten(field_data)

            for symbol in field_data:
                try:
                    # get index of symbol

                    sorted_sym_position = sorted_symbol_names.index(symbol)
                    sym_index = i * (single_pred_feature_length) + \
                        j * prediction_feature_count + sorted_sym_position
                    if sym_index >= total_length:
                        raise Exception(
                            f"Sym index ({sym_index}) greater than length {total_length}!!!")

                    resultant_vector[sym_index] = 1

                except:
                    print(
                        f'Symbol {symbol} not found in symbols_kb, continuing')
                    pass

    return resultant_vector


def make_sklearn_fv(ensemble_data: List[Tuple[Dict[str, dict], List[List[str]]]], kb: Dict[str, dict], max_predictions: int = 5, prediction_fields: List[str] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Make Ensemble feature vectors from a list of (ensemble, actual) tuples.
    This gets the Agent prediction ensemble output into the proper format for ingest into a Scikit learn classifier (to model the output of GAIuS)

    Args:
        ensemble_data (List[Tuple[Dict[str, dict], List[List[str]]]]): Corresponds to zip of pvt.predictions and pvt.actuals
        kb (Dict[str, dict]): _description_
        max_predictions (int, optional): _description_. Defaults to 5.
        prediction_fields (List[str], optional): _description_. Defaults to None.

    Returns:
        Tuple[np.ndarray, np.ndarray]: Feature Vectors, Actual Label arrays in expected Scikit-learn formats
    """

    if prediction_fields is None:
        prediction_fields = ["matches", "missing", "name"]

    prediction_field_count = len(prediction_fields)

    if 'name' in prediction_fields:
        sorted_symbol_names = list(
            kb['symbols_kb'].keys()) + [f'MODEL|{val}' for val in kb['models_kb'].keys()]
    else:
        sorted_symbol_names = list(kb['symbols_kb'].keys())
    sorted_symbol_names = sorted(sorted_symbol_names)

    total_length = prediction_field_count * \
        max_predictions * (len(sorted_symbol_names))

    sparse_array = None
    for ensemble in tqdm(ensemble_data, leave=False):
        if sparse_array is None:
            sparse_array = sp.csr_array(ensemble2vec(ensemble=PredictionEnsemble(ensemble[0]),
                                                     sorted_symbol_names=sorted_symbol_names,
                                                     max_predictions=max_predictions,
                                                     prediction_fields=prediction_fields),
                                        (1, total_length),
                                        dtype=np.bool_)
        else:
            sparse_array = sp.vstack((sparse_array,
                                      sp.csr_array(ensemble2vec(ensemble=PredictionEnsemble(ensemble[0]),
                                                                sorted_symbol_names=sorted_symbol_names,
                                                                max_predictions=max_predictions,
                                                                prediction_fields=prediction_fields),
                                                   dtype=np.bool_)),
                                     dtype=np.bool_)

    y = np.array([ens[1][0] for ens in ensemble_data], dtype=str)

    return sparse_array, y


def get_feature_names_from_weights(coefficients: np.ndarray, kb: Dict[str, dict], prediction_fields: List[str]):

    symbol_count = len(kb['symbols_kb'])
    model_count = len(kb['models_kb'])
    prediction_field_count = len(prediction_fields)

    if 'name' in prediction_fields:
        sorted_symbol_names = list(
            kb['symbols_kb'].keys()) + [f'MODEL|{val}' for val in kb['models_kb'].keys()]
    else:
        sorted_symbol_names = list(kb['symbols_kb'].keys())
    sorted_symbol_names = sorted(sorted_symbol_names)

    prediction_feature_count = len(sorted_symbol_names)
    single_pred_feature_length = prediction_field_count * \
        (prediction_feature_count)
    print(f'{single_pred_feature_length=}')

    feature_dict_template = {'models': defaultdict(lambda: defaultdict(Counter)),
                             'symbols': defaultdict(lambda: defaultdict(Counter))}

    feature_dict = {}

    coefficient_list = coefficients.tolist()
    for j, coefficient_row in enumerate(coefficients):
        sub_feature_dict = deepcopy(feature_dict_template)
        for i, val in enumerate(coefficient_row):
            if not val:
                continue
            try:
                sym_index = i % prediction_feature_count
                prediction_index = floor(
                    int(i)/int(single_pred_feature_length))
                pred_field = floor(
                    int(i)/int(prediction_feature_count)) % prediction_field_count

                if sorted_symbol_names[sym_index].startswith("MODEL"):
                    sub_feature_dict['models'][prediction_index][prediction_fields[pred_field]
                                                                 ][sorted_symbol_names[sym_index]] = val
                else:
                    # symbol
                    sub_feature_dict['symbols'][prediction_index][prediction_fields[pred_field]
                                                                  ][sorted_symbol_names[sym_index]] = val

            except:
                print(
                    f'{i=}, {sym_index=}, {val=}, {prediction_feature_count=}, {symbol_count=}')
                raise

        for pred_key in sub_feature_dict['models']:
            sub_feature_dict['models'][pred_key] = dict(
                sub_feature_dict['models'][pred_key].items())

        for pred_key in sub_feature_dict['symbols']:
            sub_feature_dict['symbols'][pred_key] = dict(
                sub_feature_dict['symbols'][pred_key].items())

        sub_feature_dict['models'] = dict(sub_feature_dict['models'].items())
        sub_feature_dict['symbols'] = dict(sub_feature_dict['symbols'].items())
        feature_dict[j] = sub_feature_dict
    return feature_dict


def split_feature_weights_by_key(symbol_feature_counter: Dict[int, Dict[str, Counter]]):
    features_by_key = defaultdict(
        lambda: defaultdict(lambda: defaultdict(dict)))
    for pred_index, symbol_feature_subcounter in symbol_feature_counter.items():

        for pred_field, pred_field_subcounter in symbol_feature_subcounter.items():
            key: str
            value: float
            for key, value in pred_field_subcounter.items():
                if len(split_key := key.rsplit('|', maxsplit=1)) <= 1:
                    continue
                try:
                    features_by_key[pred_index][split_key[0]
                                                ][pred_field][float(split_key[1])] = value
                except:
                    features_by_key[pred_index][split_key[0]
                                                ][pred_field][split_key[1]] = value
                    pass

        for key, key_features in features_by_key[pred_index].items():
            for sym_key in key_features:
                features_by_key[pred_index][key][sym_key] = dict(
                    sorted(features_by_key[pred_index][key][sym_key].items()))
            features_by_key[pred_index][key] = dict(
                sorted(features_by_key[pred_index][key].items()))  # sort items by key

    for key, key_features in features_by_key.items():
        features_by_key[key] = dict(
            sorted(features_by_key[key].items()))  # sort items by key
    return dict(features_by_key.items())


def get_models_to_drop(sym_features: dict, threshold_multiplier: float = 1.0) -> List[str]:
    """Identify models that should be dropped, based on the provided sym_features dictionary

    Args:
        sym_features (dict): _description_
        threshold_multiplier (float, optional): _description_. Defaults to 1.0.

    Returns:
        List[str]: _description_
    """
    model_weights_dict = {}
    model_name_set = set()

    for pred_index in sym_features:
        for key, symbol_fields in sym_features[pred_index].items():
            for sym_field, sym_counter in symbol_fields.items():
                # print(f'{sym_field=}, {sym_counter=}')
                # model_weights_dict = sym_counter
                for sym, val in sym_counter.items():
                    if sym in model_weights_dict:
                        continue
                    model_weights_dict[sym] = val
        # lets only worry about prediction index 0 for now

    for pred_index in sym_features:
        for key, symbol_fields in sym_features[pred_index].items():
            for sym_field, sym_counter in symbol_fields.items():
                model_name_set.update(sym_counter.keys())

    mean_val = statistics.mean(model_weights_dict.values())
    std_dev = statistics.stdev(model_weights_dict.values())

    threshold = std_dev * threshold_multiplier
    models_to_drop = [key for key, value in model_weights_dict.items(
    ) if mean_val - threshold <= value <= mean_val + threshold]

    return models_to_drop


def max_magnitude(num1: float, num2: float) -> float:
    """Return the number that has the larger magnitude, preserving sign information on
    the number

    Args:
        num1 (float): number to compare
        num2 (float): number to compare

    Returns:
        float: the number with the larger magnitude
    """
    abs_num1 = abs(num1)
    abs_num2 = abs(num2)

    if abs_num1 >= abs_num2:
        return num1
    else:
        return num2


def gm2d(features: dict, threshold_multiplier: float = 1.0) -> List[str]:
    """Get models to delete, from features dict output of "split_feature_weights_by_key"

    Args:
        features (dict): _description_
        threshold_multiplier (float, optional): _description_. Defaults to 1.0.

    Returns:
        List[str]: list of models that should be dropped from the agent (low correlation to ANY class)
    """
    model_weights_dict = Counter()

    for index, sym_features in features.items():
        for pred_index in sym_features:
            for key, symbol_fields in sym_features[pred_index].items():
                for sym_field, sym_counter in symbol_fields.items():
                    for sym, val in sym_counter.items():
                        if sym not in model_weights_dict:
                            model_weights_dict[sym] = val
                        else:
                            model_weights_dict[sym] = max_magnitude(
                                model_weights_dict[sym], val)
            # lets only worry about prediction index 0 for now

    mean_val = statistics.mean(model_weights_dict.values())
    std_dev = statistics.stdev(model_weights_dict.values())

    threshold = std_dev * threshold_multiplier
    models_to_drop = [key for key, value in model_weights_dict.items(
    ) if mean_val - threshold <= value <= mean_val + threshold]

    return models_to_drop
