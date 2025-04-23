import os
import random
import re
from pathlib import Path
from typing import Union


def validate_data(data: dict):
    """Validates if the data is in correct GAIuS digestible format.
    Returns True if data validates.  Returns False if data does not validate.

    Args:
        data (dict, required): GDF to validate

    Example:
        .. code-block:: python

            >>> gdf = {'strings':["hello"], 'vectors': [], 'emotives': {} }
            >>> validate_data(gdf)
            True
            >>> bad_gdf = {'strings': []}
            >>> validate_data(bad_gdf)
            Exception: Dictionary requires "vectors", "emotives", and "strings" as keys!
            >>> bad_gdf_2 = {'strings':["hello"], 'vectors': [], 'emotives': ['utility|5'] }
            >>> validate_data(bad_gdf_2)
            Exception: "emotives" must be a dict of <str, float>. Dict not provided!

    .. testsetup:: validate_data

        gdf1 = {"strings": [],
            "vectors": [],
            "emotives": {},
            "metadata": {}}

        # empty gdf with additional field
        gdf2 = {"strings": [],
                "vectors": [],
                "emotives": {},
                "metadata": {},
                "invalid": True}

        # gdf with single string
        gdf3 = {"strings": ["hello"],
                "vectors": [],
                "emotives": {},
                "metadata": {}
                }

        # gdf with single string and vector
        gdf4 = {"strings": ["hello"],
                "vectors": [[1, 2, 3, 4]],
                "emotives": {},
                "metadata": {}
                }

        # gdf with malformed strings field
        gdf5 = {"strings": "hello",
                "vectors": [],
                "emotives": {},
                "metadata": {}
                }

        # gdf with malformed vectors field
        gdf6 = {"strings": ["hello"],
                "vectors": [1, 2, 3, 4],
                "emotives": {},
                "metadata": {}
                }

        # gdf with malformed emotives field
        gdf7 = {"strings": ["hello"],
                "vectors": [[1, 2, 3, 4]],
                "emotives": {"utility": "high"},
                "metadata": {}
                }

        # gdf with valid emotives field
        gdf8 = {"strings": ["hello"],
                "vectors": [[1, 2, 3, 4]],
                "emotives": {"utility": 23.7},
                "metadata": {}
                }
                
        from ia.gaius.data_ops import validate_data

    .. doctest:: validate_data
        :hide:
        
        >>> validate_data(gdf1)
        True
        >>> validate_data(gdf2)
        Traceback (most recent call last):
        ...
        Exception: Key: %s, should not be in the data dictionary!
        >>> validate_data(gdf3)
        True
        >>> validate_data(gdf4)
        True
        >>> validate_data(gdf5)
        Traceback (most recent call last):
        ...
        Exception: "strings" must be a list of strings.  List not provided!
        >>> validate_data(gdf6)
        Traceback (most recent call last):
        ...
        Exception: "vectors" must be a list of arrays (i.e. lists)!
        >>> validate_data(gdf7)
        Traceback (most recent call last):
        ...
        Exception: "emotives" must be a dict of <str, float>!
        >>> validate_data(gdf8)
        True
        
    """
    if not isinstance(data, dict):
        raise Exception("Incorrect data type.  Must be a dictionary.")
    if "vectors" not in list(data.keys()) or "emotives" not in list(data.keys()) or "strings" not in list(
            data.keys()):
        raise Exception('Dictionary requires "vectors", "emotives", and "strings" as keys!')
    for key in list(data.keys()):
        if key not in ["vectors", "emotives", "strings", "metadata"]:
            raise Exception("Key: %s, should not be in the data dictionary!")

    if not isinstance(data["strings"], list):
        raise Exception('"strings" must be a list of strings.  List not provided!')
    for item in data["strings"]:
        if not (isinstance(item, str) or isinstance(item, str)):
            raise Exception('"strings" must be a list of strings or unicode objects!')

    if not isinstance(data["emotives"], dict):
        raise Exception('"emotives" must be a dict of <str, float>. Dict not provided!')
    for item in data["emotives"].values():
        if not isinstance(item, (int, float)):
            raise Exception('"emotives" must be a dict of <str, float>!')

    if not isinstance(data["vectors"], list):
        raise Exception('"vectors" must be a list of arrays.  List not provided!')
    for item in data["vectors"]:
        if not isinstance(item, list):
            raise Exception('"vectors" must be a list of arrays (i.e. lists)!')
    return True


def raw_in_count(filename: str):
    return int(os.popen("sed -n '$=' '%s'" % filename).readline().split()[0])


def atoi(text: str):
    """Attempt to convert string to int"""
    return int(text) if text.isdigit() else text


def natural_keys(text: str):
    """
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    """
    return [atoi(c) for c in re.split(r'(\d+)', str(text))]


class DataRecords:
    """Splits data into random sets for training and testing."""

    def __init__(self, original_dataset: Union[str, Path], DR: float, DF: float, shuffle: bool, folder: bool = True):
        """
        Args:
            original_dataset (str or list, required): location of dataset to use for training and testing sets
            DR (float, required): fraction of total data to use for testing and training. 0 < DR < 100
            DF (float, required): fraction of the DR to use for training.  The rest of the DR is used for testing. 0 < DF < 100
            shuffle (bool, required): whether to shuffle the data when creating sets
            folder (bool, optional): set if the original dataset is a folder

        After creating the class, utilize the member variables `train_sequences` and `test_sequences` for the data sets

        :ivar train_sequences: the files to use for training
        :ivar test_sequences: the files to use for testing
        """
        
        if folder:
            original_dataset = [Path(original_dataset).joinpath(f) for f in os.listdir(original_dataset) if
                                not f.startswith('.') and not f.startswith('_')]
            original_dataset.sort(key=natural_keys)
        DR = DR / 100
        DF = DF / 100
        try:
            if DR == 1 and DF == 1:
                if shuffle:
                    random.shuffle(original_dataset)
                self.train_sequences = original_dataset
                self.test_sequences = []
            else:
                if shuffle:
                    random.shuffle(original_dataset)

                num_files = len(original_dataset)
                num_use_files = int(num_files * DR)  # use a fraction of the whole set

                num_train_sequences = int(num_use_files * DF)  # train 2/3rds, test 1/3rd
                num_test_sequences = num_use_files - num_train_sequences

                self.train_sequences = original_dataset[:num_train_sequences]
                self.test_sequences = original_dataset[num_train_sequences:(num_train_sequences + num_test_sequences)]
        except Exception as exception:
            print(f'DataRecords BROKE by {exception.args}')
            raise


class Data:
    def __init__(self, data_directories=None, dataset=None):
        """Supply either a list of data_directories, or a dataset."""
        self.dataset = None
        self.data_directories = None
        if data_directories is not None:
            self.data_directories = data_directories
        elif dataset is not None:
            self.dataset = dataset
        self.train_sequences = []
        self.test_sequences = []
        self.percent_of_dataset_chosen = None
        self.percent_reserved_for_training = None

    def prep(self, percent_of_dataset_chosen: float, percent_reserved_for_training: float, shuffle: bool = False):
        
        self.percent_of_dataset_chosen = percent_of_dataset_chosen
        self.percent_reserved_for_training = percent_reserved_for_training
        
        if self.data_directories:
            data = [DataRecords(Path(d), percent_of_dataset_chosen, percent_reserved_for_training, shuffle, folder=True) for d
                    in self.data_directories]  # It's a list because the user may pick several data file directories.
        elif self.dataset:
            data = [DataRecords(self.dataset, percent_of_dataset_chosen, percent_reserved_for_training, shuffle,
                                folder=False)]

        self.train_sequences = []
        self.test_sequences = []
        for d in data:
            self.train_sequences += d.train_sequences
            self.test_sequences += d.test_sequences

class PreparedData(Data):
    """Overloaded type for Data class to signify that train_sequences and test_sequences
    contain raw sequences, and not filepaths to sequences
    
    Use flag prep_enabled to determine whether prep() will be executed during training. Shuffle will not happen if pre_enabled=False
    """
    def __init__(self, data_directories=None, dataset=None, prep_enabled: bool = False):
        super().__init__(data_directories, dataset)
        self.prep_enabled = prep_enabled
        pass
    
    def prep(self, *args, **kwargs):
        
        if self.prep_enabled:
            super().prep(*args, **kwargs)
        pass
