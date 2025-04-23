"""Implements a variety of prediction models."""
from collections import Counter
from copy import deepcopy
from typing import Union


def principal_delta(principal, other, potential):
    modification = abs(principal - other) * potential
    if other < principal:
        return principal - modification
    elif other > principal:
        return principal + (abs(other - principal) * potential)


def model_per_emotive(ensemble: list, emotive: str, potential_normalization_factor: float) -> float:
    """Compute the modeled emotive value, using the prediction ensemble and potential_normalization_factor

    Identifies the principal value for the emotive by utilizing the first prediction (e.g. highest potential prediction)
    containing that emotive. For the rest of predictions in the ensemble, the modeled value is updated using the delta
    between the current emotive value and the principal value * current potential / potential_normalization_factor.
    
    The intent is to ensure that the resultant modeled emotive value is never greater than the individual value of an emotive,
    and that subsequent emotive values impact the modeled value less and less, based on their potential values.
    
    Prior to updating this function, the delta to update the modeled value was computed by subtracting the current emotive value
    from the principal value, but this resulted in a case where the modeled emotive value was greater than any individual value seen
    in the prediction ensemble.
    
    Args:
        ensemble (list): The prediction ensemble to use in computations
        emotive (str): The emotive to compute a moving average of
        potential_normalization_factor (float): Sum of potential from all predictions in ensemble

    Returns:
        float: modeled emotive value for specific emotive
    """
    # using a weighted posterior_probability = potential/marginal_probability
    # FORMULA: pv + ( (Uprediction_2-pv)*(Wprediction_2) + (Uprediction_3-pv)*(Wprediction_3)... )/mp
    _found = False
    principal_value = 0.0
    while not _found:
        for i in range(0, len(ensemble)):
            if emotive in ensemble[i]['emotives'].keys():
                _found = True
                principal_value = ensemble[i]['emotives'][emotive]  # Let's use the "best" match (i.e. first showing of this emotive) as our starting point. Alternatively, we can use,say, the average of all values before adjusting.
                break
        if i == len(ensemble):
            return principal_value
    v = principal_value
    for x in ensemble[i + 1:]:
        if emotive in x['emotives']:
            v += (x["potential"] / potential_normalization_factor) * (x['emotives'][emotive] - v)
    return v


def average_emotives(record: list) -> dict:
    """
    Averages the emotives in a list (e.g. predictions ensemble or percepts).
    The emotives in the record are of type: [{'e1': 4, 'e2': 5}, {'e2': 6}, {'e1': 5 'e3': -4}]

    Args:
        record (list): List of emotive dictionaries to average emotives of

    Returns:
        dict: Dictionary of Averaged Emotives

    Example:
        ..  code-block:: python

            from ia.gaius.prediction_models import average_emotives
            record = [{'e1': 4, 'e2': 5}, {'e2': 6}, {'e1': 5 'e3': -4}]
            averages = average_emotives(record=record)

    """
    new_dict = {}
    for bunch in record:
        for e, v in bunch.items():
            if e not in new_dict:
                new_dict[e] = [v]
            else:
                new_dict[e].append(v)
    avg_dict = {}
    for e, v in new_dict.items():
        avg_dict[e] = float(sum(v) / len(v))
    return avg_dict


def bucket_predictions(ensemble: list) -> list:
    """Buckets predictions with identical potential values
    into a single prediction, merging emotives dicts and averaging
    as necessary.
    
    This function is invoked before :func:`model_per_emotive` to ensure that there is only
    a single prediction corresponding to each potential level. This is because the model_per_emotive
    function computes a delta between predictions based on potential value. By flattening to a single
    prediction, we ensure that there are no collsions in the principal_value computed in model_per_emotive
    based on potential.

    Args:
        ensemble (list): Prediction ensemble

    Returns:
        list: Resultant ensemble
    """
    bucket_dict = {}

    for pred in ensemble:

        if pred['potential'] in bucket_dict.keys():
            bucket_dict[pred['potential']].append(pred)
        else:
            bucket_dict[pred['potential']] = [pred]

    new_ensemble = []
    for v in bucket_dict.values():

        singular_pred = v[0]
        singular_pred['emotives'] = average_emotives([p['emotives'] for p in v])

        new_ensemble.append(singular_pred)

    return new_ensemble


def prediction_ensemble_modeled_emotives(ensemble: list) -> dict:
    """The emotives in the ensemble are of type: 'emotives':[{'e1': 4, 'e2': 5}, {'e2': 6}, {'e1': 5 'e3': -4}]
    First calls :func:`average_emotives` on each prediction in the ensemble, then calls :func:`bucket_predictions` on the ensemble.
    After bucketing predictions, the function :func:`model_per_emotives` is called for each emotive present in the ensemble.
    Dict returned contains { emotive: :func:`model_per_emotive` } for each emotive in the ensemble

    The potential_normalization_factor is taken after bucketing predictions to ensure that all predictions with identical potential values
    are flattened into a single list (avoids collisions with principal_values in :func:`model_per_emotive`)
    Args:
        ensemble (list): Prediction ensemble containing emotives to model

    Returns:
        dict: Dictionary of modelled emotive values
    """

    emotives_set = set()

    filtered_ensemble = []
    for p in ensemble:
        new_record = deepcopy(p)
        new_record['emotives'] = average_emotives([new_record['emotives']])
        filtered_ensemble.append(new_record)

    filtered_ensemble = bucket_predictions(filtered_ensemble)

    potential_normalization_factor = sum([p['potential'] for p in filtered_ensemble])

    for p in filtered_ensemble:
        emotives_set = emotives_set.union(p['emotives'].keys())
    return {emotive: model_per_emotive(ensemble, emotive, potential_normalization_factor) for emotive in emotives_set}


def hive_model_emotives(ensembles: dict) -> dict:
    """Compute average of emotives in model by calling :func:`average_emotives` on `ensembles`
    Internally calls :func:`prediction_ensemble_modeled_emotives` on each ensemble,
    then calls :func:`average_emotives` on the results
    Args:
        ensembles (dict): should be dictionary of { node_name: prediction_ensemble }

    Returns:
        dict: Dictionary of Averaged Emotives
    """
    return average_emotives([prediction_ensemble_modeled_emotives(ensemble) for ensemble in ensembles.values()])


def prediction_ensemble_model_classification(ensemble: list, strip_pipes: bool = True) -> Union[Counter, None]:
    """Compute classification rankings based on the symbols present in a prediction ensemble

    Args:
        ensemble (list): Prediction Ensemble
        strip_pipes (bool): Strip pipes from classifications

    Returns:
        Counter: dictionary containing ranking of classification symbols
    """
    boosted_prediction_classes = Counter()
    for prediction in ensemble:
        if not prediction['future']:
            continue
        symbol: str
        for symbol in prediction['future'][-1]:
            if strip_pipes and "|" in symbol:
                # grab the value, remove the piped keys
                symbol = symbol.split("|")[-1]
            boosted_prediction_classes[symbol] += prediction['potential']
    if len(boosted_prediction_classes) > 0:
        return boosted_prediction_classes
    else:
        return None


def most_common_ensemble_model_classification(ensemble: list, strip_pipes: bool = True) -> Union[str, None]:
    result = prediction_ensemble_model_classification(
        ensemble=ensemble, strip_pipes=strip_pipes)
    if result is None:
        return result
    return result.most_common(1)[0][0]


def hive_model_classification(ensembles: dict, strip_pipes: bool = True) -> Union[Counter, None]:
    """Compute the "hive predicted model classification" based on the ensembles provided from each node

    Args:
        ensembles (dict): should be dictionary of { node_name: prediction_ensemble }
        strip_pipes (bool): Strip pipes from classifications

    Returns:
        str: hive predicted classification
    """
    if ensembles:
        # This just takes the first "most common", even if there are multiple that have the same frequency.
        boosted_classifications = [prediction_ensemble_model_classification(
            c, strip_pipes=strip_pipes) for c in ensembles.values()]
        votes = Counter()
        for p in boosted_classifications:
            votes.update(p)
        if votes:
            return votes
    return None
