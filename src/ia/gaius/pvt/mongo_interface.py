import random
import pymongo
import json
from bson.objectid import ObjectId
from copy import deepcopy
import zipfile
import datetime
from traceback import print_exc
import io
from ia.gaius.data_ops import validate_data


class MongoDataRecords:
    def __init__(self,
                 dataset_records,
                 DR: float,
                 DF: float,
                 shuffle: bool):
        """
        Args:
            dataset_records (str or list, required): List of mongo
                ObjectIds to use as data records
            DR (float, required): fraction of total data to use for
                testing and training. 0 < DR < 100
            DF (float, required): fraction of the DR to use for training.
                The rest of the DR is used for testing. 0 < DF < 100
            shuffle (bool, required): whether to shuffle the
                data when creating sets

            After creating the class, utilize the member variables
                `train_sequences` and `test_sequences` for the data sets

        :ivar train_sequences: the mongo documents to use for training
        :ivar test_sequences: the mongo documents to use for testing
        """
        DR = DR / 100
        DF = DF / 100
        self.random = random.Random()

        if DR > 1 or DF > 1:
            raise Exception(f'Invalid value provided for DR or DF: \
                            {DR=}, {DF=}')

        try:
            if shuffle:
                self.random.shuffle(dataset_records)
            if DR == 1 and DF == 1:
                self.train_sequences = dataset_records
                self.test_sequences = []
            else:
                num_files = len(dataset_records)
                # use a fraction of the whole set
                num_use_files = int(num_files * DR)

                num_train_sequences = int(num_use_files * DF)
                num_test_sequences = num_use_files - num_train_sequences

                self.train_sequences = dataset_records[:num_train_sequences]
                self.test_sequences = dataset_records[num_train_sequences:(
                    num_train_sequences + num_test_sequences)]
        except Exception as exception:
            print(f'MongoDataRecords BROKE by {exception.args}')
            raise


def check_dataset_exists(mongo_db,
                         dataset_collection_name: str,
                         user_id: str,
                         dataset_id: str):
    """Will check if the specified dataset is found in MongoDB

    Args:
        mongo_db : MongoDB database object
        dataset_collection_name (str): collection name where
            master dataset record is saved
        user_id (string): user unique identifier
        dataset_id (string): dataset unique identifier

    Returns:
        bool: represents whether the dataset was successfully found
    """
    dataset_obj = {'user_id': user_id,
                   'dataset_id': dataset_id}

    # checking if dataset count != 1. If >1, something nefarious is
    # potentially happening
    if mongo_db[dataset_collection_name].count_documents({**dataset_obj}) != 1:
        return False
    return True


class MongoData:
    """
        Analogous object to the Data class, but utilizes a MongoDB cursor
        instead of a directory to reference data records

        Start with a MongoDB document containing the name of all dataset
        files (located separately)

        Only retrieve actual data files when calling retrieveDataRecord.
        Overloaded iterator functions to allow treating of object
        as a list.

        Example:

            .. code-block:: python

                >>> mongo = pymongo.MongoClient('mongodb://mongodb:27017/')
                >>> mongo_db = mongo.db['main_database']
                >>> dataset_details = {"user_id": "ABCD1",
                                    "dataset_id": "iris_0_0_13"}
                >>> md = MongoData(mongo_dataset_details=dataset_details,
                                mongo_db=mongo_db,
                                data_files_collection_name='dataset_files')
                >>> md.prep(percent_of_dataset_chosen=50,
                            percent_reserved_for_training=50,
                            shuffle=True)
                >>> md.setIterMode('testing')
                >>> for record in md:
                ...

    """

    def __init__(self,
                 mongo_dataset_details: dict,
                 data_files_collection_name: str,
                 mongo_db: pymongo.MongoClient,
                 dataset_collection_name: str = 'datasets'):
        """Initialized dataset object from MongoDB

        Args:
            mongo_dataset_details (dict): contains info about the user_id
                and dataset_id of the dataset. Used to query MongoDB
            data_files_collection_name (str): Collection in MongoDB where
                individual data records are stored
            dataset_collection_name (str): Collection in MongoDB where master
                dataset info record is stored
            mongo_db (pymongo.MongoClient): MongoDB client object to use
                for dataset lookups

        Raises:
            Exception: user_id field missing from mongo_dataset_details
            Exception: dataset_id field missing from mongo_dataset_details
            Exception: multiple datasets found pertaining to same user_id
                and dataset_id field
        """
        if 'user_id' not in mongo_dataset_details:
            raise Exception(f'user_id field missing from mongo_dataset_details\
                            ({mongo_dataset_details=})')
        if 'dataset_id' not in mongo_dataset_details:
            raise Exception(f'dataset_id field missing from \
                            mongo_dataset_details ({mongo_dataset_details=})')

        self._mongo_dataset_details = deepcopy(mongo_dataset_details)
        self._data_files_collection_name = deepcopy(data_files_collection_name)
        self.mongo_db = mongo_db

        # initialize iteration variables
        self._iter_mode = None
        self.__curr = None
        self.__term = None

        self.percent_of_dataset_chosen = None
        self.percent_reserved_for_training = None
        dataset_obj = {'user_id': self._mongo_dataset_details['user_id'],
                       'dataset_id': self._mongo_dataset_details['dataset_id']}

        ds_count: int = mongo_db[dataset_collection_name].count_documents(
            dataset_obj)

        if ds_count != 1:

            raise Exception(f'{ds_count} \
                            dataset records found for {dataset_obj=}')

        dataset = mongo_db[dataset_collection_name].find_one(dataset_obj)

        self._mongo_dataset_details['files'] = \
            [item for item in dataset['dataset']['files']]

        self.train_sequences = []
        self.test_sequences = []

    @classmethod
    def upload_dataset(cls, mongo_db, dataset_details: dict, filepath: str):
        """Upload a dataset to MongoDB from a local filepath

        Args:
            mongo_db (pymongo.MongoClient): MongoDB Database object
            dataset_details (dict): Dictionary containing details about
            dataset (e.g. name, user_id, dataset_id, collection names, etc.)
            filepath (str): filepath of zip folder
                containing dataset (GDF records)

        Returns:
            _type_: _description_

        Example:
            .. code-block:: python

                from ia.gaius.pvt.mongo_interface import MongoData
                ...
                dataset_details = {"user_id": "user-1234",
                                   "dataset_name": "MNIST",
                                   "dataset_id": "abba12",
                                   "data_files_collection_name": "dataset_files",
                                   "dataset_collection_name": "datasets"}
                MongoData.upload_dataset(mongo_db=mongo_db,
                                         dataset_details=dataset_details)

        """

        data_files_collection_name = dataset_details['data_files_collection_name']
        dataset_collection_name = dataset_details['dataset_collection_name']

        # ensure dataset details has user_id and dataset_id fields
        if 'user_id' not in dataset_details:
            raise Exception(
                f'user_id field missing from dataset_details ({dataset_details=})')
        if 'dataset_id' not in dataset_details:
            raise Exception(
                f'dataset_id field missing from dataset_details ({dataset_details=})')

        cur_time = datetime.datetime.now().isoformat()
        dataset_obj = {'user_id': dataset_details['user_id'],
                       'dataset_id': dataset_details['dataset_id'],
                       'lastModifiedDate': cur_time,
                       'uploadedDate': cur_time,
                       'size': None,
                       'dataset': {'files': []}}

        # retrieve dataset from filepath
        # if anything fails along the way, try to remediate database
        # by deleting stuff already inserted
        try:
            with zipfile.ZipFile(filepath, 'r') as zipObject:
                dataset_obj['size'] = sum(
                    [zinfo.file_size for zinfo in zipObject.filelist])
                records = zipObject.namelist()
                records = [(zipObject.read(item), item)
                           for item in records if not item.endswith('/') or item.startswith('.') or item.startswith('__')]
                records = [{'file': item[0],
                            'filename': item[1],
                            'user_id': dataset_obj['user_id'],
                            'dataset_id': dataset_obj['dataset_id']}
                           for item in records]

                # upload individual records to MongoDB data_files collection
                try:
                    insert_result = mongo_db[data_files_collection_name].insert_many(
                        records)
                except Exception as error:
                    print(f'failed to insert records: {str(error)}')
                    try:
                        mongo_db[data_files_collection_name].delete_many(
                            {'dataset_id': dataset_obj['dataset_id']})
                    except Exception as e2:
                        print(
                            f'failed to remediate data files collection: {str(e2)}')
                    finally:
                        return f'failed to insert records: {str(error)}'
                dataset_items = insert_result.inserted_ids
                dataset_obj['dataset']['files'] = dataset_items
                dataset_obj['dataset']['file_count'] = len(dataset_items)

                try:
                    # upload master dataset record to MongoDB dataset_collection_name
                    mongo_db[dataset_collection_name].insert_one(dataset_obj)
                except Exception as error:
                    print(f'failed to insert master record: {str(error)}')
                    try:
                        mongo_db[dataset_collection_name].delete_one(
                            dataset_obj)
                        mongo_db[data_files_collection_name].delete_many(
                            {'dataset_id': dataset_obj['dataset_id']})
                    except Exception as e2:
                        print(f'failed to remediate database: {str(e2)}')
                    finally:
                        return f'failed to insert master dataset record: {str(error)}'

        except Exception as e3:
            print(f'failed in zipfile handling: {str(e3)}')
            print_exc()
            return f'failed in zipfile handling: {str(e3)}'

        return 'success!!!'

    @classmethod
    def delete_dataset(cls, mongo_db, dataset_details: dict):
        """Upload a dataset to MongoDB from a local filepath

        Args:
            mongo_db (pymongo.MongoClient): MongoDB database object
            dataset_details (dict): Dictionary containing details about
                dataset (e.g. name, user_id, dataset_id, collection names)

        Returns:
            str: String depicting action that was taken

        Example:
            .. code-block:: python

                from ia.gaius.pvt.mongo_interface import MongoData
                ...
                dataset_details = {"user_id": "user-1234",
                                   "dataset_name": "MNIST",
                                    "dataset_id": "abba12",
                                    "data_files_collection_name": "dataset_files",
                                    "dataset_collection_name": "datasets"}
                MongoData.delete_dataset(mongo_db=mongo_db,
                                         dataset_details=dataset_details)

        """
        data_files_collection_name = dataset_details['data_files_collection_name']
        dataset_collection_name = dataset_details['dataset_collection_name']
        try:
            if not check_dataset_exists(mongo_db=mongo_db,
                                        dataset_collection_name=dataset_collection_name,
                                        user_id=dataset_details['user_id'],
                                        dataset_id=dataset_details['dataset_id']):
                return 'dataset-not-found'
        except Exception as error:
            print(f"error while checking if dataset exists: {str(error)}")
            raise e
        dataset_obj = {'user_id': dataset_details['user_id'],
                       'dataset_id': dataset_details['dataset_id']}
        dataset = None
        try:
            if mongo_db[dataset_collection_name].count_documents({**dataset_obj}) != 1:
                raise Exception(
                    f'found {mongo_db[dataset_collection_name].count_documents({**dataset_obj})} datasets in mongo, expecting 1')
            dataset = mongo_db[dataset_collection_name].find_one(
                {**dataset_obj})
        except Exception as error:
            print(f"error while retrieving dataset: {error=}")
            raise e

        try:
            mongo_db[data_files_collection_name].delete_many(
                {'_id': {'$in': dataset['dataset']['files']}})
        except Exception as error:
            print(e)
            raise e

        mongo_db[dataset_collection_name].delete_one({**dataset_obj})

        return 'deleted'

    def prep(self,
             percent_of_dataset_chosen: float,
             percent_reserved_for_training: float,
             shuffle: bool = False):
        """Prepare the dataset

        Args:
            percent_of_dataset_chosen (float): The percent of the dataset
                to utilize
            percent_reserved_for_training (float): The training/testing
                split for the dataset (e.g.
                set to 80 for 80/20 training/testing split)
            shuffle (bool, optional): Whether to shuffle the data.
                Defaults to False.
        """
        self.percent_of_dataset_chosen = percent_of_dataset_chosen
        self.percent_reserved_for_training = percent_reserved_for_training
        
        data = [MongoDataRecords(deepcopy(self._mongo_dataset_details['files']),
                                 percent_of_dataset_chosen,
                                 percent_reserved_for_training,
                                 shuffle)]

        self.train_sequences = []
        self.test_sequences = []
        for d in data:
            self.train_sequences += d.train_sequences
            self.test_sequences += d.test_sequences

    def retrieveDataRecord(self, document_id: ObjectId):
        """Retrieve a data record from MongoDB,
        pertaining to the ObjectId specifed

        Args:
            document_id (ObjectId, required): data record to retrieve
                from mongo, located in the collection specified when
                calling :func:`__init__`

        Raises:
            Exception: Raised when MongoDB document is not found.
                Shows query performed that failed

        Returns:
            str: binary string depicting data sequence
            stored in MongoDB Document
        """
        query_dict = {'user_id': self._mongo_dataset_details['user_id'],
                      'dataset_id': self._mongo_dataset_details['dataset_id'],
                      '_id': document_id}

        record = self.mongo_db[self._data_files_collection_name].find_one(
            query_dict)
        if record is None:
            raise Exception(
                f'DataRecord {str(document_id)} not found using {query_dict=}')

        return record['file']

    def convertBinaryStringtoSequence(self, record):
        """Convert Binary string of multiple GDFs (delimited by newline) into a sequence of JSON objects

        Args:
            record (str, required): binary string of GDFs to convert

        Returns:
            list: list of GDFs in json format
        """
        try:
            lines = io.StringIO(record.decode('utf-8'))
            sequence = (tuple([json.loads(line.strip()) for line in lines]))
            return sequence
        except Exception as error:
            print(f'failed to retrieve record as StringIO: {error=}')

    def getSequence(self, record):
        """Wrapper function to retrieve a record from MongoDB
        and convert it into a sequence

        Args:
            record (ObjectId): The MongoDB ObjectId of the data
                record to retrieve

        Returns:
            list: GDF sequence retrieved from MongoDB
        """
        sequence = self.convertBinaryStringtoSequence(
            self.retrieveDataRecord(record))
        for gdf in sequence:
            validate_data(gdf)
        return sequence

    def setIterMode(self, mode: str) -> None:
        """Set mode to be used for iterating across dataset

        Args:
            mode (str): set to "training" or "testing" depending
                on what set of sequences is to be iterated across

        Raises:
            Exception: When no data is in train_sequences or
                test_sequences, and :func:`prep` should be called first
            Exception: When invalid mode specified in mode argument
        """
        if len(self.train_sequences) == 0 and len(self.test_sequences) == 0:
            raise Exception('no data in train_sequences or test_sequences, \
                            use prep first')

        if mode == 'training':

            self.__curr = 0
            self.__term = len(self.train_sequences)

        elif mode == 'testing':
            self.__curr = 0
            self.__term = len(self.test_sequences)
        else:
            raise Exception('setIterMode only supports "training" \
                            and "testing"')

        self._iter_mode = mode
        return

    def __iter__(self):
        return self

    def __next__(self):
        """Iterate across range, calling :func:`retrieveDataRecord` for each item
        """
        if self.__curr >= self.__term:
            self.__curr = 0
            raise StopIteration()

        if self._iter_mode == 'training':
            (cur, self.__curr) = (
                self.train_sequences[self.__curr], self.__curr + 1)

        elif self._iter_mode == 'testing':
            (cur, self.__curr) = (
                self.test_sequences[self.__curr], self.__curr + 1)

        else:
            raise Exception('invalid iter mode: {self._iter_mode}, \
                            set using setIterMode(mode)')

        return self.retrieveDataRecord(cur)


class MongoResults:
    """Class to handle saving and linking result data inside MongoDB.

    Provides functions to insert single log record during training/testing,
    save final result after test completion, and remediation/deletion
    function for test aborting, database cleanup
    """

    def __init__(self,
                 mongo_db,
                 result_collection_name: str,
                 log_collection_name: str,
                 test_id: str,
                 user_id: str,
                 dataset_id: str,
                 test_configuration: dict = None):
        """Initialize MongoResults object

        Args:
            mongo_db (pymongo.MongoClient): Database where the results
                are to be stored
            result_collection_name (str): collection name to save final
                test results
            log_collection_name (str): collection name to save testing
                log documents
            test_id (str): unique-id for the test being conducted
            user_id (str): unique-id for the user conducting the test
            dataset_id (str): unique-id for the dataset being used
                in the test
            test_configuration (dict): object showing all of the options
                used for configuring pvt
        """

        self.test_id = test_id
        self.user_id = user_id
        self.dataset_id = dataset_id

        self.mongo_db = mongo_db
        self.result_collection_name = result_collection_name
        self.log_collection_name = log_collection_name
        self.result_collection = mongo_db[result_collection_name]
        self.log_collection = mongo_db[log_collection_name]
        self.test_configuration = test_configuration
        self.result_obj = {'testing_logs': [],
                           'training_logs': [],
                           'test_id': test_id,
                           'user_id': user_id,
                           'dataset_id': dataset_id,
                           'start_time_utc': str(datetime.datetime.utcnow()),
                           'test_configuration': self.test_configuration}

    def reset(self):
        """Reset start time and testing/training logs in result_obj
        """
        self.result_obj.update({'testing_logs': [],
                                'training_logs': [],
                                'start_time_utc': str(datetime.datetime.utcnow())})
        return

    def addLogRecord(self,
                     type: str,
                     record: dict):
        """Called during the testing loop to insert a pvt status
        record into MongoDB

        Args:
            type (str): Whether the record should be appended to the
                training or testing logs
            record (dict): the record to insert

        Raises:
            Exception: Thrown if the type provided is not supported
        """

        record_id = self.log_collection.insert_one(record).inserted_id
        if type == 'training':
            self.result_obj['training_logs'].append(record_id)
        elif type == 'testing':
            self.result_obj['testing_logs'].append(record_id)
        else:
            raise Exception(f'Unsupported record type {type} for \
                record {record}')

        return

    def saveResults(self,
                    final_results: dict):
        """Save a document in MongoDB, linking the result doc to
        the logs documents

        Args:
            final_results (dict): Information pertaining to the
                results of the test, to be stored in the results
                object for future use

        Returns:
            str: string of the ObjectId saved in MongoDB

        Example:
            .. code-block:: python

                uid = mongo_results.saveResults(final_state)
        """
        self.result_obj['end_time_utc'] = str(datetime.datetime.utcnow())
        self.result_obj['final_results'] = final_results
        # print(f'{self.result_obj = }')
        result_id = self.result_collection.insert_one(
            self.result_obj).inserted_id
        print(
            f'saved test results in {self.result_collection_name} as id: {result_id}')
        return str(result_id)

    def deleteResults(self):
        """Function used to remediate database in the event of a
        failed/aborted test

        Returns:
            dict: dict showing the deleted result record, if any
        """
        try:
            query_object = {'user_id': self.user_id,
                            'dataset_id': self.dataset_id,
                            'test_id': self.test_id
                            }
            delete_result = self.result_collection.find_one_and_delete(query_object,
                                                                       {'_id': False})

        except Exception as error:
            print(f'failed to delete results: {error=}')
            return None

        if delete_result is not None:
            try:
                self.log_collection.delete_many(
                    {'_id': {'$in': delete_result['training_logs']}})
                self.log_collection.delete_many(
                    {'_id': {'$in': delete_result['testing_logs']}})

            except Exception as error:
                print(f'failed to delete log record: {error=}')
                return None

        if self.result_obj['testing_logs']:
            self.log_collection.delete_many(
                {'_id': {'$in': self.result_obj['testing_logs']}})

        if self.result_obj['training_logs']:
            self.log_collection.delete_many(
                {'_id': {'$in': self.result_obj['training_logs']}})

        return {'status': 'deleted', 'record': delete_result}

    def retrieveResults(self):
        """Retreive test results from MongoDB based on user_id, dataset_id,
        and test_id

        Raises:
            Exception: If dataset master record is not found in database

        Returns:
            dict: Entire test result object
        """
        query_object = {'user_id': self.user_id,
                        'dataset_id': self.dataset_id,
                        'test_id': self.test_id
                        }
        self.result_obj = self.result_collection.find_one(query_object)

        if self.result_obj is None:
            raise Exception(f'Test not found based on {query_object=}')

        # retrieve successful
        training_ids = self.result_obj['training_logs']
        testing_ids = self.result_obj['testing_logs']
        training_logs = [item for item in self.log_collection.find(
            {'_id': {'$in': training_ids}})]
        testing_logs = [item for item in self.log_collection.find(
            {'_id': {'$in': testing_ids}})]

        self.result_obj['training_logs'] = training_logs
        self.result_obj['testing_logs'] = testing_logs

        return self.result_obj
