import functools
import json
import logging
import operator
import os
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import chain
from pathlib import Path
from typing import Union
import requests

# Data
import numpy as np
from tqdm.auto import tqdm

# Gaius Agent
from ia.gaius.agent_client import AgentClient
from ia.gaius.data_ops import Data, PreparedData
from ia.gaius.prediction_models import (
    average_emotives, hive_model_classification,
    most_common_ensemble_model_classification,
    prediction_ensemble_modeled_emotives)
from ia.gaius.pvt.mongo_interface import MongoData, MongoResults
from ia.gaius.pvt.pvt_utils import (compute_abs_residual, compute_residual,
                                    compute_squared_residual, f1_score,
                                    false_discovery_rate, false_negative_rate,
                                    false_omission_rate, false_positive_rate,
                                    init_emotive_on_node,
                                    init_emotive_polarity_results,
                                    negative_likelihood_ratio,
                                    negative_predictive_value, on_error_learn,
                                    plot_confusion_matrix,
                                    plot_emotives_value_charts,
                                    positive_likelihood_ratio,
                                    prevalence_threshold, rmse, smape,
                                    threat_score, true_negative_rate,
                                    true_positive_rate, update_accuracy,
                                    update_precision)
from ia.gaius.thinkflux_client import TFClient

logger = logging.getLogger(__name__)


class PVTAbortError(Exception):
    """Raised when PVT is aborted by Celery. Used to exit cleanly from nested test/train functions"""
    pass


class PVTConfigError(Exception):
    pass


class PVTMessage():
    """Wrapper for PVT socket messages to be sent during training and testing"""

    def __init__(self, status: str,
                 current_record: int,
                 total_record_count: int,
                 metrics: dict,
                 cur_test_num: int,
                 total_test_num: int,
                 test_id: str = None,
                 user_id: str = '',
                 test_type: str = 'default',
                 overall_metrics: dict = None):
        self.status = status
        self.current_record = current_record
        self.total_record_count = total_record_count
        self.metrics = metrics
        self.test_id = test_id
        self.user_id = user_id
        self.cur_test_num = cur_test_num
        self.total_test_num = total_test_num
        self.test_type = test_type
        self.overall_metrics = overall_metrics

    def toJSON(self):
        return json.loads(json.dumps({'status': self.status,
                                      'current_record': self.current_record,
                                      'total_record_count': self.total_record_count,
                                      'metrics': self.metrics,
                                      'overall_metrics': self.overall_metrics,
                                      'test_id': self.test_id,
                                      'user_id': self.user_id,
                                      'cur_test_num': self.cur_test_num,
                                      'total_test_num': self.total_test_num,
                                      'test_type': self.test_type
                                      }))


class PerformanceValidationTest():
    """
    Performance Validation Test (PVT) - Splits a GDF folder into training and testing sets.
    Based on the test type certain visualizations will be produced.

    Test types:

    - Classification
    - Emotive Value
    - Emotives Polarity
    """

    def __init__(self,
                 agent: AgentClient,
                 ingress_nodes: list,
                 query_nodes: list,
                 test_type: str,
                 test_count: int,
                 dataset: Union[Path, Data, MongoData, PreparedData],
                 test_prediction_strategy="continuous",
                 clear_all_memory_before_training: bool = True,
                 turn_prediction_off_during_training: bool = False,
                 learning_strategy: str = 'after_every',
                 shuffle: bool = False,
                 dataset_info: dict = None,
                 **kwargs: dict):
        """Initialize the PVT object with all required parameters for execution

        Args:
            agent (AgentClient): GAIuS Agent to use for trainings
            ingress_nodes (list): Ingress nodes for the GAIuS Agent (see :func:`ia.gaius.agent_client.AgentClient.set_query_nodes`)
            query_nodes (list): Query nodes for the GAIuS Agent (see :func:`ia.gaius.agent_client.AgentClient.set_query_nodes`)
            test_type (str): classification, emotives_value, or emotives_polarity
            test_count (int): Number of tests to run
            dataset (Union[Path, Data, MongoData, PreparedData]): Dataset path or object
            test_prediction_strategy (str, optional): when to learn new sequences. continuous -> learn during training and testing. noncontinuous -> learn only during training. Defaults to "continuous".
            clear_all_memory_before_training (bool, optional): Whether the GAIuS agent's memory should be cleared before each training. Defaults to True.
            turn_prediction_off_during_training (bool, optional): Whether predictions should be disabled during training to reduce computational load. Defaults to False.
            learning_strategy (str, optional): when learning is to be performed. Conforms to test_prediction_strategy. after_every -> learn after every sequence. on_error -> learn when agent guesses incorrectly
            shuffle (bool, optional): Whether dataset should be shuffled before each test iteration. Defaults to False.
            sio (_type_, optional): SocketIO object to emit information on. Defaults to None.
            task (_type_, optional): Celery details to emit information about. Defaults to None.
            user_id (str, optional): user_id to emit information to on SocketIO. Defaults to ''.
            mongo_db (pymongo.MongoClient, optional): MongoDB where dataset should be retrieved from
            dataset_info (dict, optional): information about how to retrieve dataset, used for MongoDB query
            test_id (str, optional): unique identifier to be sent with messages about this test. Also used for storing to mongodb
            test_configuration (dict, optional): dictionary storing additional metadata about test configuration, to be saved in mongodb with test results
            socket_channel (str, optional): SocketIO channel to broadcast results on. Defaults to 'pvt_status'
            QUIET (bool, optional): flag used to disable log output during PVT. Defaults to False
            DISABLE_TQDM (bool, optional): flag used to disable TQDM progress bars during PVT. Defaults to None (enabled)
            PLOT (bool, optional): flag used to determine whether to plot result graphs. Defaults to True
        """

        self.agent = agent
        self.ingress_nodes = ingress_nodes
        self.query_nodes = query_nodes
        self.test_count = test_count
        self.dataset = dataset

        self.dataset_percentage = kwargs.get('dataset_percentage', None)
        self.training_percentage = kwargs.get('training_percentage', None)
        self.shuffle = shuffle
        self.test_type = test_type
        self.clear_all_memory_before_training = clear_all_memory_before_training
        self.turn_prediction_off_during_training = turn_prediction_off_during_training
        self.test_prediction_strategy = test_prediction_strategy

        self.emotives_set = defaultdict(set)
        self.labels_set = defaultdict(set)
        self.predictions = None
        self.actuals = None
        self.emotive_value_results = None
        self.pvt_results = None

        self.dataset_info = dataset_info
        self.testing_log = []
        self.mongo_results = None
        self.learning_strategy = learning_strategy
        self.labels_counter = Counter()
        self.overall_labels_counter = Counter()
        self.testing_counter = Counter()
        self.training_counter = Counter()
        self.overall_training_counter = Counter()
        self.overall_testing_counter = Counter()
        self.predicted_class_statistics = defaultdict(Counter)
        self.overall_predicted_class_statistics = defaultdict(Counter)

        self.test_id: str = kwargs.get('test_id', None)
        self.user_id: str = kwargs.get('user_id', None)
        self.socket_channel = kwargs.get('socket_channel', 'pvt_status')
        self.QUIET: bool = kwargs.get('QUIET', False)
        self.DISABLE_TQDM: bool = kwargs.get('DISABLE_TQDM', None)
        self.sio = kwargs.get('sio', None)
        self.task = kwargs.get('task', None)
        self.mongo_db = kwargs.get('mongo_db', None)
        self.test_configuration = kwargs.get('test_configuration', {})
        self.results_filepath = kwargs.get('results_filepath', None)
        self.PLOT = kwargs.get('PLOT', True)

        self.overall_metrics = None
        self.overall_results = None
        self._original_dataset = self.dataset
        self.__validate_settings()

        # retrieve genes before test
        self.agent_genes = {}
        all_nodes = [node['name'] for node in self.agent.all_nodes]
        
        # Setting summarize single to False by default in order to handle multiply nodes topologies
        self.agent.set_summarize_for_single_node(False)

        self.agent_genes = self.agent.get_all_genes(nodes=all_nodes)
        self.test_configuration['initial_agent_genes'] = self.agent_genes
        self.test_configuration['genome'] = self.agent.genome.topology
        
        if isinstance(self._original_dataset, MongoData):
            self.mongo_results = MongoResults(mongo_db=self.mongo_db,
                                              result_collection_name=self.dataset_info['results_collection'],
                                              log_collection_name=self.dataset_info['logs_collection'],
                                              test_id=self.test_id,
                                              user_id=self.user_id,
                                              dataset_id=self.dataset_info['dataset_id'],
                                              test_configuration=self.test_configuration)
        elif (isinstance(self._original_dataset, Path) or isinstance(self._original_dataset, str)):
            self.dataset = Data(data_directories=[self.dataset])
        elif isinstance(self._original_dataset, PreparedData):
            pass
        elif isinstance(self._original_dataset, Data):
            pass

        if self.results_filepath is not None:
            if not os.path.exists(self.results_filepath):
                os.makedirs(self.results_filepath)
        # Show Agent status by Default
        self.agent.show_status()

        # Assign Ingress and Query Nodes
        self.agent.set_ingress_nodes(nodes=self.ingress_nodes)
        self.agent.set_query_nodes(nodes=self.query_nodes)



        logger.debug(f"test_counts = {self.test_count}")

    def __validate_settings(self):
        if self.test_prediction_strategy not in ['continuous', 'noncontinuous']:
            raise Exception(
                """
                Not a valid test prediction strategy. Please choose either 
                'continuous': learn the test sequence/answer after the agent has tried to make a prediction
                'noncontinuous': do not learn the test sequence.
                """
            )
        if self.learning_strategy not in ['after_every', 'on_error']:
            raise Exception(
                """Not a valid learning strategy. Please choose either
        'after_every': learn every sequence
        'on_error': learn the sequence only when the agent guesses incorrectly.
        """
            )
        if self.learning_strategy == 'on_error':
            if self.turn_prediction_off_during_training == True:
                raise Exception(
                    """When learning_strategy is 'on_error', predictions must be enabled during training.
                    """
                )
            if self.test_type not in ['classification', 'emotives_polarity']:
                raise Exception(
                    """When learning_strategy is 'on_error', test_type must be either 'classification' or 'emotives_polarity'
                    """
                )
        if not any([isinstance(self.dataset, ds_type) for ds_type in [Data, MongoData, PreparedData, Path, str]]):
            raise Exception(
                f'unknown type for dataset: {type(self.dataset)}')
        if self.test_type not in ['classification', 'emotives_value', 'emotives_polarity']:
            raise Exception(f'unknown value for test_type: {self.test_type}')

        if any([isinstance(self._original_dataset, ds_type) for ds_type in [Path, str]]):
            if (self.dataset_percentage == None) or (self.training_percentage is None):
                raise Exception(
                    "dataset_percentage and training_percentage must be provided when using filepath for dataset")

        return

    def prepare_datasets(self):
        
        percent_of_dataset_chosen = self.dataset.percent_of_dataset_chosen
        percent_reserved_for_training = self.dataset.percent_reserved_for_training
        if self.dataset_percentage is not None:
            percent_of_dataset_chosen = self.dataset_percentage
        if self.training_percentage is not None:
            percent_reserved_for_training = self.training_percentage

        self.dataset.prep(
            percent_of_dataset_chosen=percent_of_dataset_chosen,
            percent_reserved_for_training=percent_reserved_for_training,
            shuffle=self.shuffle
        )
        logger.debug(
            f"Length of Training Set = {len(self.dataset.train_sequences)}")
        logger.debug(
            f"Length of Testing Set  = {len(self.dataset.test_sequences)}")
        return

    def run_classification_pvt(self):
        for test_num in range(0, self.test_count):
            self.test_num = test_num
            logger.debug(f'Conducting Test # {test_num}')
            logger.debug('\n---------------------')

            self.prepare_datasets()

            if self.sio:  # pragma: no cover
                self.sio.emit(self.socket_channel,
                              PVTMessage(status='training',
                                         current_record=0,
                                         total_record_count=len(
                                             self.dataset.train_sequences),
                                         metrics={},
                                         overall_metrics={},
                                         cur_test_num=self.test_num,
                                         total_test_num=self.test_count-1,
                                         test_id=self.test_id,
                                         user_id=self.user_id,
                                         test_type=self.test_type).toJSON(),
                              to=self.user_id)
            try:

                self.train_agent()

                if len(self.dataset.test_sequences) == 0:
                    logger.debug(f'Complete!')
                    continue

                self.test_agent()

                class_metrics_data_structures = self.compile_classification_results()

            except Exception as error:
                logger.error(
                    'error during training/testing phase of test, remediating database for failed test, then raising error')
                if self.mongo_results:
                    logger.info('about to remediate database')
                    self.mongo_results.deleteResults()
                    logger.info('remediated database')

                logger.debug(f'raising error {str(error)}')
                raise error

            try:
                if not isinstance(self.dataset, MongoData) and (self.PLOT == True):
                    logger.debug('Plotting Results...')
                    plot_confusion_matrix(test_num=test_num,
                                          class_metrics_data_structures=class_metrics_data_structures,
                                          results_dir=self.results_filepath)
            except Exception as error:
                logger.exception(
                    f'error plotting results from classification pvt: {str(error)}')
                pass

            response_dict = {'counter': self.labels_counter,
                             'pvt_results': self.pvt_results,
                             'overall_results': self.overall_results,
                             'final_agent_status': self.agent.show_status()}
            result_msg = PVTMessage(status='finished',
                                    current_record=0,
                                    total_record_count=0,
                                    metrics=response_dict,
                                    overall_metrics={},
                                    cur_test_num=self.test_num,
                                    total_test_num=self.test_count-1,
                                    test_id=self.test_id,
                                    user_id=self.user_id,
                                    test_type=self.test_type).toJSON()
            if self.sio:  # pragma: no cover
                self.sio.emit(self.socket_channel,
                              result_msg,
                              to=self.user_id)

        if self.mongo_results:
            self.mongo_results.saveResults(result_msg)
        return

    def run_emotive_value_pvt(self):
        self.pvt_results = []
        for test_num in range(0, self.test_count):
            self.test_num = test_num
            logger.debug(f'Conducting Test # {test_num}')
            logger.debug('\n---------------------\n')

            self.prepare_datasets()
            if self.sio:  # pragma: no cover
                self.sio.emit(self.socket_channel,
                              PVTMessage(status='training',
                                         current_record=0,
                                         total_record_count=len(
                                             self.dataset.train_sequences),
                                         metrics={},
                                         cur_test_num=self.test_num,
                                         total_test_num=self.test_count-1,
                                         test_id=self.test_id,
                                         user_id=self.user_id,
                                         test_type=self.test_type).toJSON(),
                              to=self.user_id)

            self.train_agent()

            if len(self.dataset.test_sequences) == 0:
                logger.debug(f'Complete!')
                return

            self.test_agent()

            self.emotive_value_results = get_emotives_value_metrics(
                emotives_set=self.emotives_set, this_test_log=self.testing_log[self.test_num], overall=False)
            self.overall_results = get_emotives_value_metrics(
                emotives_set=self.emotives_set, this_test_log=list(chain(*self.testing_log)), overall=True)
            self.pvt_results.append(deepcopy(self.emotive_value_results))
            logger.debug('Plotting Results...')

            # don't try to plot emotive values if we're working to save in a mongo database
            # (its probably running without a jupyter GUI)
            if self.PLOT:
                plot_emotives_value_charts(test_num=self.test_num,
                                           emotive_value_results=self.emotive_value_results,
                                           QUIET=self.QUIET,
                                           results_filepath=self.results_filepath)

        # send out finished socket message
        response_dict = {'counter': self.labels_counter,
                         'pvt_results': self.pvt_results,
                         'overall_results': self.overall_results,
                         'final_agent_status': self.agent.show_status()}

        final_msg = PVTMessage(status='finished',
                               current_record=0,
                               total_record_count=0,
                               metrics=response_dict,
                               overall_metrics={},
                               cur_test_num=self.test_num,
                               total_test_num=self.test_count-1,
                               test_id=self.test_id,
                               user_id=self.user_id,
                               test_type=self.test_type).toJSON()
        if self.sio:  # pragma: no cover
            self.sio.emit(self.socket_channel,
                          final_msg,
                          to=self.user_id)
        if self.mongo_results:
            self.mongo_results.saveResults(final_msg)
        return

    def run_emotive_polarity_pvt(self):
        self.pvt_results = []
        for test_num in range(0, self.test_count):
            self.test_num = test_num
            logger.debug(f'Conducting Test # {test_num}')

            self.prepare_datasets()

            if self.sio:  # pragma: no cover
                self.sio.emit(self.socket_channel,
                              PVTMessage(status='training',
                                         current_record=0,
                                         total_record_count=len(
                                             self.dataset.train_sequences),
                                         metrics={},
                                         overall_metrics={},
                                         cur_test_num=self.test_num,
                                         total_test_num=self.test_count-1,
                                         test_id=self.test_id,
                                         user_id=self.user_id,
                                         test_type=self.test_type).toJSON(),
                              to=self.user_id)

            logger.debug("Training Agent...")
            self.train_agent()

            if len(self.dataset.test_sequences) == 0:
                logger.debug(f'Complete!')
                return

            logger.debug("Testing Agent...")
            self.test_agent()

            logger.debug('Getting Emotives Polarity Metrics...')
            logger.debug('Saving results to pvt_results...')
            self.pvt_results.append(
                deepcopy(get_emotives_polarity_metrics(emotives_set=self.emotives_set,
                                                       this_test_log=self.testing_log[self.test_num],
                                                       overall=False)))
            self.overall_results = get_emotives_polarity_metrics(
                emotives_set=self.emotives_set,
                this_test_log=list(chain(*self.testing_log)),
                overall=True)

        # send out finished socket message
        response_dict = {'counter': self.labels_counter,
                         'pvt_results': self.pvt_results,
                         'overall_results': self.overall_results,
                         'final_agent_status': self.agent.show_status()}
        final_msg = PVTMessage(status='finished',
                               current_record=0,
                               total_record_count=0,
                               metrics=response_dict,
                               overall_metrics={},
                               cur_test_num=self.test_num,
                               total_test_num=self.test_count-1,
                               test_id=self.test_id,
                               user_id=self.user_id,
                               test_type=self.test_type).toJSON()
        if self.sio:  # pragma: no cover
            self.sio.emit(self.socket_channel,
                          final_msg, to=self.user_id)
        if self.mongo_results:
            self.mongo_results.saveResults(final_msg)
        return

    def conduct_pvt(self):
        """
        Function called to execute the PVT session. Determines test to run based on 'test_type' attribute

        Results from PVT is stored in the 'pvt_results' attribute

        .. note::

            A complete example is shown in the :ref:`Usage Examples <training reference>` document. Please see this doc for further information about how to conduct a PVT test

        """

        try:
            self.test_num = 0
            self.pvt_results = []
            self.testing_log = []

            self.overall_metrics = None

            if self.test_type in ['classification']:
                self.overall_labels_counter = Counter()
                self.overall_testing_counter = Counter()
                self.overall_training_counter = Counter()
                self.overall_predicted_class_statistics = defaultdict(Counter)
                self.overall_metrics = defaultdict(lambda: defaultdict(float))
            elif self.test_type in ['emotives_value']:
                self.overall_labels_counter = Counter()
                self.overall_testing_counter = Counter()
                self.overall_training_counter = Counter()
                self.overall_predicted_class_statistics = defaultdict(Counter)
                self.overall_metrics = defaultdict(
                    lambda: defaultdict(lambda: defaultdict(float)))
            elif self.test_type in ['emotives_polarity']:
                self.labels_counter = defaultdict(Counter)
                self.testing_counter = defaultdict(Counter)
                self.training_counter = defaultdict(Counter)
                self.overall_labels_counter = defaultdict(Counter)
                self.overall_testing_counter = defaultdict(Counter)
                self.overall_training_counter = defaultdict(Counter)
                self.predicted_class_statistics = defaultdict(
                    lambda: defaultdict(Counter))
                self.overall_predicted_class_statistics = defaultdict(
                    lambda: defaultdict(Counter))

                # init overall metrics for emotive polarity
                self.overall_metrics = defaultdict(
                    lambda: defaultdict(lambda: defaultdict(float)))
                self.overall_metrics['positive'] = defaultdict(
                    lambda: defaultdict(lambda: defaultdict(float)))
                self.overall_metrics['negative'] = defaultdict(
                    lambda: defaultdict(lambda: defaultdict(float)))
                self.overall_metrics['overall'] = defaultdict(
                    lambda: defaultdict(lambda: defaultdict(float)))

            # Validate Test Type
            if self.test_type == 'classification':
                logger.debug("Conducting Classification PVT...\n")
                self.run_classification_pvt()

            elif self.test_type == 'emotives_value':
                logger.debug("Conducting Emotives Value PVT...\n")
                self.run_emotive_value_pvt()

            elif self.test_type == 'emotives_polarity':
                logger.debug("Conducting Emotives Polarity PVT...\n")
                self.run_emotive_polarity_pvt()

            else:
                raise Exception(
                    """
                    Please choose one of the test type:
                    - classification
                    - emotives_value
                    - emotives_polarity

                    ex.
                    --> pvt.test_type='emotives_value'
                    then, retry
                    --> pvt.conduct_pvt()
                    """
                )
        except Exception as error:
            logger.exception(
                f'failed to conduct PVT test, test_type={self.test_type}: {str(error)}')
            raise error

        # convert defaultdict to normal dict by dumping and loading pvt results
        self.pvt_results = json.loads(json.dumps(self.pvt_results))
        self.overall_metrics = json.loads(json.dumps(self.overall_metrics))

    def train_agent(self):
        """
        Takes a training set of gdf files, and then trains an agent on those records.
        The user can turn prediction off if the topology doesn't have abstractions
        where prediction is needed to propagate data through the topology.
        """
        # Initialize
        if self.clear_all_memory_before_training is True:
            logger.debug('Clearing memory of selected ingress nodes...')
            self.agent.clear_all_memory()

        self.labels_set.clear()
        self.labels_counter.clear()
        self.training_counter.clear()
        self.testing_counter.clear()
        self.emotives_set.clear()
        self.predicted_class_statistics.clear()

        # Train Agent
        if self.turn_prediction_off_during_training is True:
            self.agent.stop_predicting(nodes=self.query_nodes)
        else:
            self.agent.start_predicting(nodes=self.query_nodes)

        logger.debug('Preparing to train agent...')

        train_seq_len = len(self.dataset.train_sequences)

        train_metrics, train_progress_bar = self._setup_training()

        for j, _ in enumerate(train_progress_bar):

            if j % 10 == 0:
                if self.task:  # pragma: no cover (testing disabled for Celery code (used by Lab))
                    if self.task.is_aborted():
                        self.abort_test_remediation(
                            current_record=j, record_count=train_seq_len)
                        return

            sequence = self._extract_training_sequence(j)

            current_labels = None
            record_emotive_set = None

            # update label/emotive counters
            if self.test_type == 'classification':

                train_metrics, current_labels = self._train_classification(
                    sequence=sequence, train_metrics=train_metrics)

            elif self.test_type in ['emotives_value', 'emotives_polarity']:

                train_metrics, record_emotive_set = self._train_emotives(
                    sequence=sequence, train_metrics=train_metrics)

            self._apply_learning_strategy(
                sequence=sequence, current_labels=current_labels, record_emotive_set=record_emotive_set)
            self.overall_metrics.update({'counter': self.overall_labels_counter,
                                         'training_counter': self.overall_training_counter})

            training_msg = PVTMessage(status='training',
                                      current_record=j + 1,
                                      total_record_count=train_seq_len,
                                      metrics=train_metrics,
                                      overall_metrics=self.overall_metrics,
                                      cur_test_num=self.test_num,
                                      total_test_num=self.test_count-1,
                                      test_id=self.test_id,
                                      user_id=self.user_id,
                                      test_type=self.test_type)

            self.store_train_record(
                test_num=self.test_num, record=training_msg)

        train_progress_bar.reset()
        logger.debug('Finished training agent!')

    def _apply_learning_strategy(self, sequence, current_labels, record_emotive_set):

        if self.learning_strategy == 'on_error':

            predictions = self.agent.get_predictions()
            self.agent.observe(data=sequence[-1], nodes=self.ingress_nodes)
            if self.test_type == 'classification':
                on_error_learn(agent=self.agent, test_type=self.test_type, query_nodes=self.query_nodes,
                               predictions=predictions, current_labels=current_labels, record_emotive_set=None)
            elif self.test_type == 'emotives_polarity':
                on_error_learn(agent=self.agent, test_type=self.test_type, query_nodes=self.query_nodes,
                               predictions=predictions, current_labels=None, record_emotive_set=record_emotive_set)

        elif self.learning_strategy == 'after_every':
            if self.test_type == 'classification':
                self.agent.observe(
                    data=sequence[-1], nodes=self.ingress_nodes)
            self.agent.learn(nodes=self.ingress_nodes)

    def _setup_training(self):

        train_metrics = {}
        if self.test_type == 'classification':
            train_metrics = {'counter': self.labels_counter,
                             'training_counter': self.training_counter,
                             'testing_counter': self.testing_counter,
                             'predicted_class_statistics': self.predicted_class_statistics}
        elif self.test_type == 'emotives_polarity':
            train_metrics = {'counter': self.labels_counter,
                             'training_counter': self.training_counter,
                             'testing_counter': self.testing_counter}
        elif self.test_type == 'emotives_value':

            train_metrics = {'counter': self.labels_counter,
                             'training_counter': self.training_counter,
                             'testing_counter': self.testing_counter}

        train_progress_bar = tqdm(self.dataset.train_sequences,
                                  bar_format="{l_bar}{bar} {n_fmt}/{total_fmt} [{remaining} {rate_fmt}{postfix}]",
                                  disable=self.DISABLE_TQDM,
                                  leave=True,
                                  unit=' records')
        train_progress_bar.set_description(f'Training (Test #{self.test_num})')
        train_progress_bar.unit = ' records'

        return train_metrics, train_progress_bar

    def _extract_training_sequence(self, idx):
        if isinstance(self.dataset, PreparedData):
            sequence = self.dataset.train_sequences[idx]
        elif isinstance(self.dataset, Data):
            with open(self.dataset.train_sequences[idx], "r") as sequence_file:
                sequence = sequence_file.readlines()
                sequence = [json.loads(d) for d in sequence]
        elif isinstance(self.dataset, MongoData):
            sequence = self.dataset.getSequence(
                self.dataset.train_sequences[idx])

        return sequence

    def _train_emotives(self, sequence, train_metrics):

        # observe training sequence
        for event in sequence:
            self.agent.observe(data=event, nodes=self.ingress_nodes)
            for node in self.ingress_nodes:
                percept_emotives = list(self.agent.get_percept_data()[
                                        node]['emotives'].keys())
                self.emotives_set[node].update(percept_emotives)

        # compute emotive information in current sequence, for emotive tests
        if self.test_type == 'emotives_polarity':
            record_emotive_set = dict()
            for event in sequence:
                record_emotive_set.update(event['emotives'])
        elif self.test_type == 'emotives_value':
            record_emotive_set = set()
            for event in sequence:
                record_emotive_set.update(
                    list(event['emotives'].keys()))

        self.update_training_counters(
            current_labels=record_emotive_set)

        train_metrics.update(
            {'actual': self.sum_sequence_emotives(sequence)})
        self.overall_metrics.update(
            {'actual': self.sum_sequence_emotives(sequence)})

        return train_metrics, record_emotive_set

    def _train_classification(self, sequence, train_metrics):
        for event in sequence[:-1]:
            self.agent.observe(data=event, nodes=self.ingress_nodes)
        current_labels = [label.rsplit(
            '|', maxsplit=1)[-1] for label in sequence[-1]['strings']]
        for node in self.ingress_nodes:
            self.labels_set[node].update(current_labels)

        self.update_training_counters(current_labels=current_labels)

        train_metrics.update({'actual': current_labels})
        self.overall_metrics.update({'actual': current_labels})

        return train_metrics, current_labels

    def test_agent(self):
        """
        Test agent on dataset test sequences provided in self.dataset.test_sequences
        """
        # Start Testing
        self.agent.start_predicting(nodes=self.query_nodes)
        self.predictions = []
        self.actuals = []

        self.testing_log.append([])

        test_seq_len = len(self.dataset.test_sequences)
        if test_seq_len == 0:
            logger.debug('length of testing sequences is 0... returning\n')
            return

        test_step_info, test_progress_bar = self._setup_testing()

        for k, _ in enumerate(test_progress_bar):

            if k % 10 == 0:
                if self.task:  # pragma: no cover (testing disabled for Celery code (used by Lab))
                    if self.task.is_aborted():
                        self.abort_test_remediation(
                            current_record=k, record_count=test_seq_len)
                        return

            sequence = self._extract_testing_sequence(k)

            current_labels = None
            record_emotive_set = None

            self.agent.clear_wm(nodes=self.ingress_nodes)
            if self.test_type == 'classification':
                test_step_info, current_labels = self._test_classification(
                    sequence=sequence, test_step_info=test_step_info, idx=k)

            elif self.test_type in ['emotives_value', 'emotives_polarity']:
                test_step_info, record_emotive_set = self._test_emotives(
                    sequence=sequence, test_step_info=test_step_info, idx=k)

            if self.test_prediction_strategy == 'continuous':
                self._apply_testing_strategy(
                    current_labels=current_labels, record_emotive_set=record_emotive_set)

            # prepare test step message
            test_step_msg = PVTMessage(status='testing',
                                       current_record=k + 1,
                                       total_record_count=test_seq_len,
                                       metrics=test_step_info,
                                       overall_metrics=self.overall_metrics,
                                       cur_test_num=self.test_num,
                                       total_test_num=self.test_count-1,
                                       test_id=self.test_id,
                                       user_id=self.user_id,
                                       test_type=self.test_type)

            self.store_train_record(test_num=self.test_num,
                                    record=test_step_msg)

        test_progress_bar.reset()
        return

    def _apply_testing_strategy(self, current_labels, record_emotive_set):

        if self.learning_strategy == 'on_error':
            if self.test_type == 'classification':
                on_error_learn(agent=self.agent, test_type=self.test_type, query_nodes=self.query_nodes,
                               predictions=self.predictions[-1], current_labels=current_labels, record_emotive_set=None)
            elif self.test_type == 'emotives_polarity':
                on_error_learn(agent=self.agent, test_type=self.test_type, query_nodes=self.query_nodes,
                               predictions=self.predictions[-1], current_labels=None, record_emotive_set=record_emotive_set)

        elif self.learning_strategy == 'after_every':
            self.agent.learn(nodes=self.ingress_nodes)

    def _test_emotives(self, sequence, test_step_info, idx):

        if self.test_type == 'emotives_value':
            record_emotive_set = set()
            for event in sequence:
                self.agent.observe(
                    data=event, nodes=self.ingress_nodes)
                record_emotive_set.update(
                    list(event['emotives'].keys()))
                for node in self.ingress_nodes:
                    self.emotives_set[node].update(
                        list(self.agent.get_percept_data()[node]['emotives'].keys()))
        elif self.test_type == 'emotives_polarity':
            record_emotive_set = dict()
            for event in sequence:
                self.agent.observe(
                    data=event, nodes=self.ingress_nodes)
                record_emotive_set.update(event['emotives'])
                for node in self.ingress_nodes:
                    self.emotives_set[node].update(
                        list(self.agent.get_percept_data()[node]['emotives'].keys()))

        # update counters with emotives from testing record
        self.update_testing_counters(current_labels=record_emotive_set)

        # get and store predictions after observing events
        self.predictions.append(
            self.agent.get_predictions(nodes=self.query_nodes))
        # store answers in a separate list for evaluation
        self.actuals.append(self.sum_sequence_emotives(sequence))

        pred_dict = {node: prediction_ensemble_modeled_emotives(
            self.predictions[idx][node]) for node in self.query_nodes}

        # compute hive prediction for time idx
        pred_dict['hive'] = average_emotives(list(pred_dict.values()))

        self.update_predicted_class_statistics(pred_dict=pred_dict)

        test_step_info.update({'idx': idx,
                               'predicted': pred_dict,
                               'actual': self.actuals[-1],
                               'counter': self.labels_counter,
                               'training_counter': self.training_counter,
                               'testing_counter': self.testing_counter,
                               'predicted_class_statistics': self.predicted_class_statistics})
        test_step_info = compute_incidental_probabilities(
            test_step_info=test_step_info, test_type=self.test_type)
        self.overall_metrics.update({'predicted': pred_dict,
                                     'actual': self.actuals[-1],
                                     'counter': self.overall_labels_counter,
                                     'training_counter': self.overall_training_counter,
                                     'testing_counter': self.overall_testing_counter,
                                     'predicted_class_statistics': self.overall_predicted_class_statistics})
        self.overall_metrics['idx'] = self.overall_metrics.get(
            'idx', idx-1) + 1
        # doing compute incidental probabilities a second time, for the overall metrics
        self.overall_metrics = compute_incidental_probabilities(
            test_step_info=self.overall_metrics, test_type=self.test_type)

        return test_step_info, record_emotive_set

    def _test_classification(self, sequence, test_step_info, idx):

        for event in sequence[:-1]:
            self.agent.observe(data=event, nodes=self.ingress_nodes)

        # get and store predictions after observing events
        self.predictions.append(
            self.agent.get_predictions(nodes=self.query_nodes))

        # store answers in a separate list for evaluation
        current_labels = [label.rsplit('|', maxsplit=1)[-1]
                          for label in sequence[-1]['strings']]

        self.actuals.append(deepcopy(current_labels))

        for node in self.ingress_nodes:
            self.labels_set[node].update(current_labels)

        # persists across multiple runs
        self.update_testing_counters(current_labels)

        # get predicted classification on the fly, so we can save to mongo individually
        pred_dict = {node: most_common_ensemble_model_classification(
            self.predictions[idx][node]) for node in self.query_nodes}
        pred_dict['hive'] = hive_model_classification(
            self.predictions[idx])
        if pred_dict['hive'] is not None:
            pred_dict['hive'] = pred_dict['hive'].most_common(1)[0][0]

        self.update_predicted_class_statistics(pred_dict=pred_dict)
        test_step_info.update({'idx': idx,
                               'predicted': pred_dict,
                               'actual': self.actuals[idx],
                               'counter': self.labels_counter,
                               'training_counter': self.training_counter,
                               'testing_counter': self.testing_counter,
                               'predicted_class_statistics': self.predicted_class_statistics})
        test_step_info = compute_incidental_probabilities(
            test_step_info=test_step_info, test_type=self.test_type)
        self.overall_metrics.update({'predicted': pred_dict,
                                     'actual': self.actuals[idx],
                                     'counter': self.overall_labels_counter,
                                     'training_counter': self.overall_training_counter,
                                     'testing_counter': self.overall_testing_counter,
                                     'predicted_class_statistics': self.overall_predicted_class_statistics})
        self.overall_metrics['idx'] = self.overall_metrics.get(
            'idx', idx-1) + 1
        # doing compute incidental probabilities a second time, for the overall metrics
        self.overall_metrics = compute_incidental_probabilities(
            test_step_info=self.overall_metrics, test_type=self.test_type)

        # observe answer
        self.agent.observe(sequence[-1], nodes=self.ingress_nodes)

        return test_step_info, current_labels

    def _setup_testing(self):
        if self.test_type == 'classification':
            test_step_info = defaultdict(lambda: defaultdict(float))

        elif self.test_type == 'emotives_polarity':
            test_step_info = defaultdict(
                lambda: defaultdict(lambda: defaultdict(float)))
            test_step_info['positive'] = defaultdict(
                lambda: defaultdict(lambda: defaultdict(float)))
            test_step_info['negative'] = defaultdict(
                lambda: defaultdict(lambda: defaultdict(float)))
            test_step_info['overall'] = defaultdict(
                lambda: defaultdict(lambda: defaultdict(float)))

        elif self.test_type == 'emotives_value':
            test_step_info = defaultdict(
                lambda: defaultdict(lambda: defaultdict(float)))

        test_progress_bar = tqdm(self.dataset.test_sequences,
                                 bar_format="{l_bar}{bar} {n_fmt}/{total_fmt} [{remaining} {rate_fmt}{postfix}]",
                                 disable=self.DISABLE_TQDM,
                                 leave=True,
                                 unit=' records')
        test_progress_bar.set_description(f'Testing (Test #{self.test_num})')

        return test_step_info, test_progress_bar

    def _extract_testing_sequence(self, idx):
        if isinstance(self.dataset, PreparedData):
            sequence = self.dataset.test_sequences[idx]
        elif isinstance(self.dataset, Data):
            with open(self.dataset.test_sequences[idx], "r") as sequence_file:
                sequence = sequence_file.readlines()
                sequence = [json.loads(d) for d in sequence]
        elif isinstance(self.dataset, MongoData):
            sequence = self.dataset.getSequence(
                self.dataset.test_sequences[idx])


        return sequence

    def update_training_counters(self, current_labels):
        if self.test_type in ['classification', 'emotives_value']:
            self.labels_counter.update(current_labels)
            self.training_counter.update(current_labels)
            self.overall_labels_counter.update(current_labels)
            self.overall_training_counter.update(current_labels)
        elif self.test_type in ['emotives_polarity']:
            for emo, val in current_labels.items():
                emotive_sign = np.sign(val)
                if emotive_sign == 1:
                    emotive_label_types = {
                        'positive': 1, 'overall': 1, 'negative': 0}
                elif emotive_sign == -1:
                    emotive_label_types = {
                        'positive': 0, 'overall': 1, 'negative': 1}
                self.labels_counter[emo].update(emotive_label_types)
                self.training_counter[emo].update(emotive_label_types)
                self.overall_labels_counter[emo].update(emotive_label_types)
                self.overall_training_counter[emo].update(emotive_label_types)

    def update_testing_counters(self, current_labels):
        if self.test_type in ['classification', 'emotives_value']:
            self.labels_counter.update(current_labels)
            self.testing_counter.update(current_labels)
            self.overall_labels_counter.update(current_labels)
            self.overall_testing_counter.update(current_labels)
        elif self.test_type in ['emotives_polarity']:
            for emo, val in current_labels.items():
                emotive_sign = np.sign(val)
                if emotive_sign == 1:
                    emotive_label_types = {
                        'positive': 1, 'overall': 1, 'negative': 0}
                elif emotive_sign == -1:
                    emotive_label_types = {
                        'positive': 0, 'overall': 1, 'negative': 1}
                self.labels_counter[emo].update(emotive_label_types)
                self.testing_counter[emo].update(emotive_label_types)
                self.overall_labels_counter[emo].update(emotive_label_types)
                self.overall_testing_counter[emo].update(emotive_label_types)

    def update_predicted_class_statistics(self, pred_dict):
        """Update predicted class statistics based on test_type
        and provided dictionary of node predictions

        Args:
            pred_dict (dict): dict of node predictions
        """
        if self.test_type == 'classification':
            for key, val in pred_dict.items():
                self.predicted_class_statistics[key].update([val])
                self.overall_predicted_class_statistics[key].update([val])

        elif self.test_type == 'emotives_value':
            for key, modeled_emotives_dict in pred_dict.items():
                for emo, emotive_value in modeled_emotives_dict.items():

                    self.predicted_class_statistics[key].update([emo])
                    self.overall_predicted_class_statistics[key].update([
                                                                        emo])

        elif self.test_type == 'emotives_polarity':
            for key, modeled_emotives_dict in pred_dict.items():
                for emo, emotive_value in modeled_emotives_dict.items():
                    emotive_sign = np.sign(emotive_value)
                    if emotive_sign == 1:
                        emotive_label_types = {
                            'positive': 1, 'overall': 1, 'negative': 0}
                    elif emotive_sign == -1:
                        emotive_label_types = {
                            'positive': 0, 'overall': 1, 'negative': 1}
                    self.predicted_class_statistics[key][emo].update(
                        emotive_label_types)
                    self.overall_predicted_class_statistics[key][emo].update(
                        emotive_label_types)

    def sum_sequence_emotives(self, sequence):
        """
        Sums all emotive values
        """
        emotives_seq = [event['emotives']
                        for event in sequence if event['emotives']]
        return dict(functools.reduce(operator.add, map(Counter, emotives_seq)))

    def abort_test_remediation(self, current_record, record_count):  # pragma: no cover (testing disabled for Celery code (used by Lab))
        logger.info(
            f'about to abort {self.task.request.id =}, {self.test_id=}')
        if self.sio:  # pragma: no cover
            logger.info('Sending abort message')
            abort_msg = PVTMessage(status='aborted',
                                   current_record=current_record + 1,
                                   total_record_count=record_count,
                                   metrics={},
                                   overall_metrics={},
                                   cur_test_num=self.test_num,
                                   total_test_num=self.test_count-1,
                                   test_id=self.test_id,
                                   user_id=self.user_id,
                                   test_type=self.test_type)
            self.sio.emit(self.socket_channel,
                          abort_msg.toJSON(), to=self.user_id)
        if self.mongo_results:
            logger.info('cleaning up MongoDB')
            self.mongo_results.deleteResults()

        raise PVTAbortError(
            f"Aborting Test, at record {current_record} of {record_count}")

    def store_train_record(self, test_num, record: PVTMessage):

        if record.status == 'testing':
            self.testing_log[test_num].append(deepcopy(record.toJSON()))

        # insert into test_log in mongo, if using mongodb
        if self.mongo_results:
            self.mongo_results.addLogRecord(
                type=record.status, record=deepcopy(record.toJSON()))

        # emit socketIO message
        if self.sio:  # pragma: no cover
            self.sio.emit(self.socket_channel, deepcopy(
                record.toJSON()), to=self.user_id)

    def compile_classification_results(self, include_thinkflux_node: bool=False):
        for k, labels in self.labels_set.items():
            self.labels_set[k] = set(
                [label.rsplit('|', maxsplit=1)[-1] for label in labels])
        logger.debug('Getting Classification Metrics...')
        class_metrics_data_structures = get_classification_metrics(
            labels_set=self.labels_set, this_test_log=self.testing_log[self.test_num], overall=False, include_thinkflux_node=include_thinkflux_node)
        self.overall_results = get_classification_metrics(
            labels_set=self.labels_set, this_test_log=list(chain(*self.testing_log)), overall=True, include_thinkflux_node=include_thinkflux_node)
        self.pvt_results.append(
            deepcopy(class_metrics_data_structures))

        return class_metrics_data_structures

class TFPVT(PerformanceValidationTest):
    def __init__(self,
                 agent: AgentClient,
                 thinkflux: TFClient,
                 ingress_nodes: list,
                 query_nodes: list,
                 test_type: str,
                 test_count: int,
                 dataset: Union[Path, Data, MongoData, PreparedData],
                 test_prediction_strategy="noncontinuous",
                 clear_all_memory_before_training: bool = True,
                 turn_prediction_off_during_training: bool = False,
                 learning_strategy: str = 'after_every',
                 shuffle: bool = False,
                 dataset_info: dict = None,
                 bootstrap_concept_params: dict = None,
                 **kwargs: dict):
        pass
        
        self.agent_alias = 'TFPVT-INTERFACE-CONFIG'
        self.thinkflux = thinkflux

        self.bootstrap_concept_params = bootstrap_concept_params
        if bootstrap_concept_params is None:
            self.bootstrap_concept_params = {}
        
        super().__init__(agent, ingress_nodes, query_nodes, test_type, test_count, dataset, test_prediction_strategy, clear_all_memory_before_training, turn_prediction_off_during_training, learning_strategy, shuffle, dataset_info, **kwargs)    
        self.__validate_settings()

        self.interface_config = self.agent.get_interface_node_config()
        self.interface_config['alias'] = self.agent_alias
        self.thinkflux.add_interface_nodes(agent_config=self.interface_config)


    def __validate_settings(self):
        if self.test_prediction_strategy not in ['noncontinuous']:
            raise Exception(
                """
                Only noncontinuous prediction strategy implemented for TFPVT.
                """
            )
        if self.learning_strategy not in ['after_every', 'on_error']:
            raise Exception(
                """Not a valid learning strategy. Please choose either
        'after_every': learn every sequence
        'on_error': learn the sequence only when the agent guesses incorrectly.
        """
            )
        if self.learning_strategy == 'on_error':
            if self.turn_prediction_off_during_training == True:
                raise Exception(
                    """When learning_strategy is 'on_error', predictions must be enabled during training.
                    """
                )
            if self.test_type not in ['classification']:
                raise Exception(
                    """When learning_strategy is 'on_error', test_type must be either 'classification' or 'emotives_polarity'
                    """
                )
        if not any([isinstance(self.dataset, ds_type) for ds_type in [Data, MongoData, PreparedData, Path, str]]):
            raise Exception(
                f'unknown type for dataset: {type(self.dataset)}')
        if self.test_type not in ['classification']:
            raise Exception(f'Only classification test_type implemented for TFPVT')

        if any([isinstance(self._original_dataset, ds_type) for ds_type in [Path, str]]):
            if (self.dataset_percentage == None) or (self.training_percentage is None):
                raise Exception(
                    "dataset_percentage and training_percentage must be provided when using filepath for dataset")


        
        return

    def run_classification_pvt(self):
        for test_num in range(0, self.test_count):
            self.test_num = test_num
            logger.debug('Conducting Test # %s\n\n---------------------', test_num)

            self.prepare_datasets()

            if self.sio:  # pragma: no cover
                self.sio.emit(self.socket_channel,
                              PVTMessage(status='training',
                                         current_record=0,
                                         total_record_count=len(
                                             self.dataset.train_sequences),
                                         metrics={},
                                         overall_metrics={},
                                         cur_test_num=self.test_num,
                                         total_test_num=self.test_count-1,
                                         test_id=self.test_id,
                                         user_id=self.user_id,
                                         test_type=self.test_type).toJSON(),
                              to=self.user_id)
            try:
                # self.thinkflux.clear_all_kbs()
                self.train_agent()
                
                logger.debug("about to bootstrap concepts")
                self.agent.start_predicting()
                bootstrap_response = self.thinkflux.bootstrap_concepts(**self.bootstrap_concept_params)
                if not bootstrap_response.ok:
                    raise Exception(f"failed bootstrapping concepts: {bootstrap_response.content}")
                if len(self.dataset.test_sequences) == 0:
                    logger.debug('Complete!')
                    continue

                self.test_agent()

                class_metrics_data_structures = self.compile_classification_results(include_thinkflux_node=True)

            except Exception as e:
                logger.exception(
                    'error during training/testing phase of test, remediating database for failed test, then raising error')
                if self.mongo_results:
                    logger.info('about to remediate database')
                    self.mongo_results.deleteResults()
                    logger.info('remediated database')

                logger.debug('raising error')
                raise e

            try:
                if not isinstance(self.dataset, MongoData) and (self.PLOT == True):
                    logger.debug('Plotting Results...')
                    plot_confusion_matrix(test_num=test_num,
                                          class_metrics_data_structures=class_metrics_data_structures,
                                          results_dir=self.results_filepath)
            except Exception:
                logger.exception('error plotting results from classification pvt')

            response_dict = {'counter': self.labels_counter,
                             'pvt_results': self.pvt_results,
                             'overall_results': self.overall_results,
                             'final_agent_status': self.agent.show_status()}
            result_msg = PVTMessage(status='finished',
                                    current_record=0,
                                    total_record_count=0,
                                    metrics=response_dict,
                                    overall_metrics={},
                                    cur_test_num=self.test_num,
                                    total_test_num=self.test_count-1,
                                    test_id=self.test_id,
                                    user_id=self.user_id,
                                    test_type=self.test_type).toJSON()
            if self.sio:  # pragma: no cover
                self.sio.emit(self.socket_channel,
                              result_msg,
                              to=self.user_id)

            self.thinkflux._query(requests.post,
                                  f'{self.thinkflux._url}/pvt/results/{self.agent_alias}',
                                  json=response_dict)

        if self.mongo_results:
            self.mongo_results.saveResults(result_msg)
        return


    def _test_classification(self, sequence, test_step_info, idx):

        for event in sequence[:-1]:
            self.agent.observe(data=event, nodes=self.ingress_nodes)

        # get and store predictions after observing events
        self.predictions.append(
            self.agent.get_predictions(nodes=self.query_nodes))

        # store answers in a separate list for evaluation
        current_labels = [label.rsplit('|', maxsplit=1)[-1]
                          for label in sequence[-1]['strings']]

        self.actuals.append(deepcopy(current_labels))

        for node in self.ingress_nodes + ['thinkflux']:
            self.labels_set[node].update(current_labels)

        # persists across multiple runs
        self.update_testing_counters(current_labels)

        # get predicted classification on the fly, so we can save to mongo individually
        pred_dict = {node: most_common_ensemble_model_classification(
            self.predictions[idx][node]) for node in self.query_nodes}
        pred_dict['hive'] = hive_model_classification(
            self.predictions[idx])
        if pred_dict['hive'] is not None:
            pred_dict['hive'] = pred_dict['hive'].most_common(1)[0][0]
        
        thinkflux_classification = self.thinkflux._query(requests.post,
                                                         f'{self.thinkflux._url}/query/{self.agent_alias}',
                                                         json=self.predictions[idx]).json()
        thinkflux_classification = thinkflux_classification['message']
        pred_dict['thinkflux'] = thinkflux_classification

        self.update_predicted_class_statistics(pred_dict=pred_dict)
        test_step_info.update({'idx': idx,
                               'predicted': pred_dict,
                               'actual': self.actuals[idx],
                               'counter': self.labels_counter,
                               'training_counter': self.training_counter,
                               'testing_counter': self.testing_counter,
                               'predicted_class_statistics': self.predicted_class_statistics})
        test_step_info = compute_incidental_probabilities(
            test_step_info=test_step_info, test_type=self.test_type)
        self.overall_metrics.update({'predicted': pred_dict,
                                     'actual': self.actuals[idx],
                                     'counter': self.overall_labels_counter,
                                     'training_counter': self.overall_training_counter,
                                     'testing_counter': self.overall_testing_counter,
                                     'predicted_class_statistics': self.overall_predicted_class_statistics})
        self.overall_metrics['idx'] = self.overall_metrics.get(
            'idx', idx-1) + 1
        # doing compute incidental probabilities a second time, for the overall metrics
        self.overall_metrics = compute_incidental_probabilities(
            test_step_info=self.overall_metrics, test_type=self.test_type)

        # observe answer
        self.agent.observe(sequence[-1], nodes=self.ingress_nodes)

        return test_step_info, current_labels


def get_classification_metrics(labels_set, this_test_log, overall=False, include_thinkflux_node: bool = False):
    """
    Builds classification final results structure for each node
    """

    class_metrics = defaultdict(lambda: defaultdict(list))
    actuals = []

    if overall:
        metrics_key = 'overall_metrics'
    else:
        metrics_key = 'metrics'

    for record in this_test_log:
        record_metrics = record[metrics_key]
        actuals.append(record_metrics['actual'])
        for node in record_metrics['predicted'].keys():
            class_metrics[node]['predictions'].append(
                record_metrics['predicted'][node])
    last_test_record = this_test_log[-1]
    for node in class_metrics:
        class_metrics[node]['actuals'] = actuals
        class_metrics[node]['metrics'] = {}
        node_test_metrics = last_test_record[metrics_key]
        class_metrics[node]['metrics']['training_counter'] = node_test_metrics['training_counter']
        class_metrics[node]['metrics']['testing_counter'] = node_test_metrics['testing_counter']
        class_metrics[node]['metrics']['counter'] = node_test_metrics['counter']
        for metric, metric_values in node_test_metrics.items():
            if metric in ['training_counter', 'testing_counter', 'counter', 'idx', 'predicted', 'actual']:
                continue
            class_metrics[node]['metrics'][metric] = metric_values[node]
        if node == 'hive':
            continue
        class_metrics[node]['labels'] = list(
            set(list(labels_set[node]) + [None]))

    hive_label_set = set()
    label_set: set
    for label_set in labels_set.values():
        hive_label_set.update(label_set)
    class_metrics['hive']['labels'] = list(hive_label_set)

    if include_thinkflux_node:
        class_metrics['thinkflux']['labels'] = list(hive_label_set)

    return class_metrics


def get_emotives_value_metrics(emotives_set, this_test_log, overall=False):
    """
    Builds emotives value data structures for each node
    """
    # Build an emotives Metric Data Structure
    results = defaultdict(lambda: defaultdict(dict))
    # generate hive emotive set
    hive_emotive_set = set()
    label_set: set
    for label_set in emotives_set.values():
        hive_emotive_set.update(label_set)
    emotives_set['hive'] = hive_emotive_set

    if overall:
        metrics_key = 'overall_metrics'
    else:
        metrics_key = 'metrics'

    # init metrics structure for each node, emotive
    for node in emotives_set:
        for emotive in emotives_set[node]:
            results[node][emotive] = {}
            results[node][emotive]['actuals'] = []
            results[node][emotive]['predictions'] = []
            results[node][emotive]['residuals'] = []
            results[node][emotive]['abs_residuals'] = []
            results[node][emotive]['squared_residuals'] = []

    for record in this_test_log:
        current_metrics = record[metrics_key]
        for node, node_predicted_emotives in current_metrics['predicted'].items():
            for emotive, predicted_value in node_predicted_emotives.items():
                results[node][emotive]['predictions'].append(
                    predicted_value)
                results[node][emotive]['actuals'].append(
                    current_metrics['actual'][emotive])
                results[node][emotive]['residuals'].append(
                    current_metrics['residuals'][node][emotive])
                results[node][emotive]['abs_residuals'].append(
                    current_metrics['abs_residuals'][node][emotive])
                results[node][emotive]['squared_residuals'].append(
                    current_metrics['squared_residuals'][node][emotive])

    last_test_record = this_test_log[-1]
    test_metrics = last_test_record[metrics_key]
    for node in results:
        for emotive in emotives_set[node]:

            results[node][emotive]['metrics'] = {}
            results[node][emotive]['metrics']['response_counts'] = test_metrics['response_counts'][node][emotive]
            results[node][emotive]['metrics']['response_percentage'] = test_metrics['response_percentage'][node][emotive]
            results[node][emotive]['metrics']['unknown_percentage'] = test_metrics['unknown_percentage'][node][emotive]
            results[node][emotive]['metrics']['response_percentage'] = test_metrics['response_percentage'][node][emotive]
            results[node][emotive]['metrics']['counter'] = test_metrics['counter'][emotive]
            results[node][emotive]['metrics']['training_counter'] = test_metrics['training_counter'][emotive]
            results[node][emotive]['metrics']['testing_counter'] = test_metrics['testing_counter'][emotive]
            if (node in test_metrics['rmse']) and (emotive in test_metrics['rmse'][node]):
                results[node][emotive]['metrics']['rmse'] = test_metrics['rmse'][node][emotive]
                results[node][emotive]['metrics']['smape'] = test_metrics['smape'][node][emotive]
                results[node][emotive]['metrics']['1-smape'] = test_metrics['1-smape'][node][emotive]
            else:
                results[node][emotive]['metrics']['rmse'] = np.nan
                results[node][emotive]['metrics']['smape'] = np.nan
                results[node][emotive]['metrics']['1-smape'] = np.nan

    return results


def get_emotives_polarity_metrics(emotives_set, this_test_log, overall=False):
    """
    Builds emotives polarity data structures for each node
    """

    if overall:
        metrics_key = 'overall_metrics'
    else:
        metrics_key = 'metrics'

    template_dict = {'predictions': [],
                     'actuals': [],
                     'metrics': init_emotive_polarity_results(),
                     'predicted_class_statistics': {}
                     }
    if len(this_test_log) == 0:
        return {}
    # lets flip the dictionary so that it is organized per node instead of per metric
    raw_test_results = deepcopy(this_test_log[-1][metrics_key])

    flattened_emotive_set = set(
        chain(*[list(item) for item in emotives_set.values()]))
    hive_emotives_set = flattened_emotive_set
    emotive_polarity_results = {k: {i: deepcopy(template_dict) for i in v}
                                for k, v in emotives_set.items()}
    emotive_polarity_results['hive'] = {emo: deepcopy(template_dict)
                                        for emo in hive_emotives_set}
    for metric_type, metric_info in raw_test_results.items():
        if metric_type == 'predicted_class_statistics':
            for node, info in metric_info.items():
                for emotive, emotive_pcs in info.items():
                    emotive_polarity_results[node][emotive]['predicted_class_statistics'] = emotive_pcs
        elif metric_type not in ['overall', 'positive', 'negative']:
            continue
        for k, v in metric_info.items():
            if k not in ['true_positive',
                         'false_positive',
                         'true_negative',
                         'false_negative',
                         'unknown_percentage',
                         'response_percentage',
                         'response_counts',
                         'accuracy',
                         'precision',
                         'FPR',
                         'FDR',
                         'TNR',
                         'TPR',
                         'NPV',
                         'FNR',
                         'FOR',
                         'LR+',
                         'LR-',
                         'PT',
                         'TS']:
                continue

            for node, info in v.items():
                for emotive, emotive_data in info.items():
                    if emotive in emotive_polarity_results[node]:
                        emotive_polarity_results[node][emotive]['metrics'][metric_type][k] = deepcopy(
                            emotive_data)

                        emotive_polarity_results[node][emotive]['metrics'][metric_type][
                            'training_counter'] = raw_test_results['training_counter'][emotive][metric_type]
                        emotive_polarity_results[node][emotive]['metrics'][metric_type][
                            'testing_counter'] = raw_test_results['testing_counter'][emotive][metric_type]
                        emotive_polarity_results[node][emotive]['metrics'][metric_type][
                            'counter'] = raw_test_results['counter'][emotive][metric_type]

    for record in this_test_log:
        metrics = record[metrics_key]
        for emotive, val in metrics['actual'].items():
            for node, node_emotive_set in emotives_set.items():
                if emotive in node_emotive_set:
                    emotive_polarity_results[node][emotive]['actuals'].append(
                        val)
        for node, emotive_dict in metrics['predicted'].items():
            for emotive, val in emotive_dict.items():
                emotive_polarity_results[node][emotive]['predictions'].append(
                    val)
    return emotive_polarity_results


def compute_incidental_probabilities(test_step_info: dict, test_type: str):
    """Keep track of how well each node is doing during the testing phase. To be used for live visualizations

    Args:
        test_step_info (dict, required): Dictionary containing information about the current predicted, actual answers, and other related metrics (e.g. precision, unknowns, residuals, response rate, etc.)

    Returns:
        dict: updated test_step_info with the statistics for the current timestep
    """
    idx = test_step_info['idx']

    if test_type == 'classification':

        for k in test_step_info['predicted'].keys():
            if test_step_info['predicted'][k] != None:
                test_step_info['response_counts'][k] += 1

                if test_step_info['predicted'][k] in test_step_info['actual']:
                    test_step_info['true_positive'][k] += 1
                    # touch key in case it hasn't been initialized yet
                    test_step_info['false_positive'][k] += 0
                else:
                    test_step_info['false_positive'][k] += 1
                    # touch key in case it hasn't been initialized yet
                    test_step_info['true_positive'][k] += 0
            else:
                # touch key in case it hasn't been initialized yet
                test_step_info['response_counts'][k] += 0
                test_step_info['true_positive'][k] += 0
                test_step_info['false_positive'][k] += 0

            test_step_info['precision'][k] = update_precision(tp=test_step_info['true_positive'][k],
                                                              tn=0,
                                                              response_count=test_step_info['response_counts'][k])

            test_step_info['f1'][k] = f1_score(tp=test_step_info['true_positive'][k],
                                               fp=test_step_info['false_positive'][k],
                                               fn=0)

            test_step_info['accuracy'][k] = update_accuracy(tp=test_step_info['true_positive'][k],
                                                            tn=0,
                                                            overall_count=idx+1)
            # (test_step_info['true_positive'][k] / (idx + 1)) * 100
            test_step_info['response_percentage'][k] = (
                test_step_info['response_counts'][k] / (idx + 1)) * 100
            test_step_info['unknown_percentage'][k] = 100 - \
                test_step_info['response_percentage'][k]

            tp = test_step_info['true_positive'][k]
            tn = test_step_info['true_negative'][k]
            fp = test_step_info['false_positive'][k]
            fn = test_step_info['false_negative'][k]
            test_step_info['FPR'][k] = false_positive_rate(fp=fp, tn=tn)
            test_step_info['FDR'][k] = false_discovery_rate(tp=tp, fp=fp)
            test_step_info['TNR'][k] = true_negative_rate(tn=tn, fp=fp)
            test_step_info['TPR'][k] = true_positive_rate(tp=tp, fn=fn)
            test_step_info['NPV'][k] = negative_predictive_value(tn=tn, fn=fn)
            test_step_info['FNR'][k] = false_negative_rate(fn=fn, tp=tp)
            test_step_info['FOR'][k] = false_omission_rate(fn=fn, tn=tn)
            test_step_info['LR+'][k] = positive_likelihood_ratio(
                tp=tp, fp=fp, tn=tn, fn=fn)
            test_step_info['LR-'][k] = negative_likelihood_ratio(
                tp=tp, fp=fp, tn=tn, fn=fn)
            test_step_info['PT'][k] = prevalence_threshold(
                tp=tp, fp=fp, tn=tn, fn=fn)
            test_step_info['TS'][k] = threat_score(tp=tp, fp=fp, fn=fn)

    elif test_type == 'emotives_polarity':

        for k in test_step_info['predicted'].keys():
            for emotive in test_step_info['actual'].keys():
                actual_sign = np.sign(test_step_info['actual'][emotive])
                if actual_sign == 1:
                    actual_value_type = 'positive'
                elif actual_sign == -1:
                    actual_value_type = 'negative'
                if actual_sign == 0:
                    raise Exception(
                        f'Zero value found in polarity test at idx {idx}')

                # catch new emotives, not yet seen on node {k}
                if emotive not in test_step_info['overall']['true_positive'][k].keys():
                    init_emotive_on_node(
                        emotive=emotive, test_step_info=test_step_info, node=k)
                for val_type in [actual_value_type, 'overall']:
                    test_step_info[val_type]['testing_counter'][k][emotive] += 1
                if emotive in test_step_info['predicted'][k].keys():
                    pred_sign = np.sign(
                        test_step_info['predicted'][k][emotive])

                    for val_type in [actual_value_type, 'overall']:
                        # If predicted value non-zero
                        if bool(pred_sign):
                            test_step_info[val_type]['response_counts'][k][emotive] += 1

                        # True positive (correct)
                        if actual_sign > 0 and pred_sign > 0:
                            test_step_info[val_type]['true_positive'][k][emotive] += 1

                        # True Negative (correct)
                        elif actual_sign < 0 and pred_sign < 0:
                            test_step_info[val_type]['true_negative'][k][emotive] += 1

                        # False positive (incorrect)
                        elif actual_sign < 0 and not pred_sign < 0:
                            test_step_info[val_type]['false_positive'][k][emotive] += 1

                        # False negative (incorrect)
                        elif actual_sign > 0 and not pred_sign > 0:
                            test_step_info[val_type]['false_negative'][k][emotive] += 1

                        # Calculate precision value
                        tp = test_step_info[val_type]['true_positive'][k][emotive]
                        tn = test_step_info[val_type]['true_negative'][k][emotive]
                        fp = test_step_info[val_type]['false_positive'][k][emotive]
                        fn = test_step_info[val_type]['false_negative'][k][emotive]

                        test_step_info[val_type]['precision'][k][emotive] = update_precision(tp=tp,
                                                                                             tn=tn,
                                                                                             response_count=test_step_info[val_type]['response_counts'][k][emotive])

                        test_step_info[val_type]['accuracy'][k][emotive] = update_accuracy(tp=tp,
                                                                                           tn=tn,
                                                                                           overall_count=test_step_info[val_type]['testing_counter'][k][emotive])
                        test_step_info[val_type]['FPR'][k][emotive] = false_positive_rate(
                            fp=fp, tn=tn)
                        test_step_info[val_type]['FDR'][k][emotive] = false_discovery_rate(
                            tp=tp, fp=fp)
                        test_step_info[val_type]['TNR'][k][emotive] = true_negative_rate(
                            tn=tn, fp=fp)
                        test_step_info[val_type]['TPR'][k][emotive] = true_positive_rate(
                            tp=tp, fn=fn)
                        test_step_info[val_type]['NPV'][k][emotive] = negative_predictive_value(
                            tn=tn, fn=fn)
                        test_step_info[val_type]['FNR'][k][emotive] = false_negative_rate(
                            fn=fn, tp=tp)
                        test_step_info[val_type]['FOR'][k][emotive] = false_omission_rate(
                            fn=fn, tn=tn)
                        test_step_info[val_type]['LR+'][k][emotive] = positive_likelihood_ratio(
                            tp=tp, fp=fp, tn=tn, fn=fn)
                        test_step_info[val_type]['LR-'][k][emotive] = negative_likelihood_ratio(
                            tp=tp, fp=fp, tn=tn, fn=fn)
                        test_step_info[val_type]['PT'][k][emotive] = prevalence_threshold(
                            tp=tp, fp=fp, tn=tn, fn=fn)
                        test_step_info[val_type]['TS'][k][emotive] = threat_score(
                            tp=tp, fp=fp, fn=fn)

                for val_type in [actual_value_type, 'overall']:
                    # Update response percentage and unknown percentage
                    test_step_info[val_type]['response_percentage'][k][emotive] = (
                        test_step_info[val_type]['response_counts'][k][emotive] / (test_step_info[val_type]['testing_counter'][k][emotive])) * 100
                    test_step_info[val_type]['unknown_percentage'][k][emotive] = 100 - \
                        test_step_info[val_type]['response_percentage'][k][emotive]

    elif test_type == 'emotives_value':

        for emotive in test_step_info['actual'].keys():
            for k in test_step_info['predicted'].keys():
                if emotive in test_step_info['predicted'][k].keys():
                    test_step_info['residuals'][k][emotive] = compute_residual(actual=test_step_info['actual'][emotive],
                                                                               predicted=test_step_info['predicted'][k][emotive])
                    test_step_info['abs_residuals'][k][emotive] = compute_abs_residual(actual=test_step_info['actual'][emotive],
                                                                                       predicted=test_step_info['predicted'][k][emotive])
                    test_step_info['squared_residuals'][k][emotive] = compute_squared_residual(actual=test_step_info['actual'][emotive],
                                                                                               predicted=test_step_info['predicted'][k][emotive])

                    previous_rmse = test_step_info['rmse'][k][emotive]
                    previous_smape = test_step_info['smape'][k][emotive]
                    # touch 1-smape
                    test_step_info['1-smape'][k][emotive]
                    if test_step_info['predicted'][k][emotive] == np.nan:
                        continue

                    count = test_step_info['response_counts'][k][emotive]
                    # compute new_rmse
                    test_step_info['smape'][k][emotive] = smape(previous_smape=previous_smape,
                                                                count=count,
                                                                abs_residual=test_step_info['abs_residuals'][k][emotive],
                                                                predicted=test_step_info['predicted'][k][emotive],
                                                                actual=test_step_info['actual'][emotive])
                    test_step_info['rmse'][k][emotive] = rmse(previous_rmse=previous_rmse,
                                                              count=count,
                                                              squared_residual=test_step_info['squared_residuals'][k][emotive])
                    test_step_info['1-smape'][k][emotive] = 100 - \
                        (test_step_info['smape'][k][emotive])
                    test_step_info['response_counts'][k][emotive] += 1

                # Update response percentage and unknown percentage
                test_step_info['response_percentage'][k][emotive] = (
                    test_step_info['response_counts'][k][emotive] / (test_step_info['testing_counter'][emotive])) * 100
                test_step_info['unknown_percentage'][k][emotive] = 100 - \
                    test_step_info['response_percentage'][k][emotive]

    return test_step_info
