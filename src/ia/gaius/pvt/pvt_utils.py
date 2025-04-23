"""Utilities for PVT computations"""
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
import matplotlib.pyplot as plt
from numpy import sign, isnan
import pandas as pd
import plotly.graph_objects as go
from copy import deepcopy
import logging
from itertools import chain
import math
from pathlib import Path
from ia.gaius.agent_client import AgentClient
from ia.gaius.prediction_models import most_common_ensemble_model_classification, prediction_ensemble_modeled_emotives

logger = logging.getLogger('ia.gaius.pvt.pvt_utils')

def init_emotive_on_node(emotive: str, node: str, test_step_info: dict):
    """Helper function to initialize emotive information for live messages.
    Used if new emotive is encountered during testing
    (emotive only seen in specific records, not consistently across all)

    Args:
        emotive (str): emotive name
        node (str): node to initialize emotive on
        test_step_info (dict): dictionary of live information, which should
            be initialized with new emotive
    """
    test_step_info['overall']['response_counts'][node][emotive] = 0
    test_step_info['overall']['true_positive'][node][emotive] = 0
    test_step_info['overall']['true_negative'][node][emotive] = 0
    test_step_info['overall']['false_positive'][node][emotive] = 0
    test_step_info['overall']['false_negative'][node][emotive] = 0
    test_step_info['overall']['testing_counter'][node][emotive] = 0

    # init positive and negative metrics
    test_step_info['positive']['response_counts'][node][emotive] = 0
    test_step_info['positive']['true_positive'][node][emotive] = 0
    test_step_info['positive']['true_negative'][node][emotive] = 0
    test_step_info['positive']['false_positive'][node][emotive] = 0
    test_step_info['positive']['false_negative'][node][emotive] = 0
    test_step_info['positive']['testing_counter'][node][emotive] = 0

    test_step_info['negative']['response_counts'][node][emotive] = 0
    test_step_info['negative']['true_positive'][node][emotive] = 0
    test_step_info['negative']['true_negative'][node][emotive] = 0
    test_step_info['negative']['false_positive'][node][emotive] = 0
    test_step_info['negative']['false_negative'][node][emotive] = 0
    test_step_info['negative']['testing_counter'][node][emotive] = 0
    return


def init_emotive_polarity_results():
    result_dict = {'overall': {},
                   'positive': {},
                   'negative': {}}

    for key, value in result_dict.items():
        value['true_positive'] = 0
        value['false_positive'] = 0
        value['true_negative'] = 0
        value['false_negative'] = 0
        value['unknown_percentage'] = 0.0
        value['response_percentage'] = 0.0
        value['response_counts'] = 0
        value['accuracy'] = 0.0
        value['precision'] = 0.0
        value['training_counter'] = 0
        value['testing_counter'] = 0
        value['counter'] = 0
        value['FPR'] = 0.0
        value['FDR'] = 0.0
        value['TNR'] = 0.0
        value['TPR'] = 0.0
        value['NPV'] = 0.0
        value['FNR'] = 0.0
        value['FOR'] = 0.0
        value['LR+'] = 0.0
        value['LR-'] = 0.0
        value['PT'] = 0.0
        value['TS'] = 0.0

    return result_dict


def check_answer_correctness(predicted, actual, test_type: str) -> bool:
    if test_type == 'classification':
        # predicted should be a string, actual should be a list
        return predicted in actual
    elif test_type == 'emotives_polarity':
        # predicted and actual should be numbers
        predicted_sign = sign(predicted)
        actual_sign = sign(actual)

        return predicted_sign == actual_sign
    else:
        raise Exception(
            f"Check answer correctness received invalid test_type {test_type}")


def on_error_learn(agent: AgentClient, test_type: str, query_nodes: list, predictions: dict, current_labels: list, record_emotive_set: dict):
    correct_dict = {node: False for node in query_nodes}
    if test_type == 'classification':
        for node in correct_dict:
            correct_dict[node] = check_answer_correctness(predicted=most_common_ensemble_model_classification(
                predictions[node]), actual=current_labels, test_type='classification')
        pass
    elif test_type == 'emotives_polarity':
        for node in correct_dict:
            ensemble_emotives = prediction_ensemble_modeled_emotives(
                predictions[node])
            correct_dict[node] = all([check_answer_correctness(predicted=ensemble_emotives.get(
                emotive, 0.0), actual=emotive_value, test_type='emotives_polarity') for emotive, emotive_value in record_emotive_set.items()])

        pass
    else:
        raise Exception(
            """on_error learning strategy only permitted for classification and emotives_polarity
                        """
        )
    for node, answer_correct in correct_dict.items():
        if not answer_correct:
            agent.learn(nodes=[node])

    agent.clear_wm(nodes=list(correct_dict.keys()))

def compute_residual(predicted: float, actual: float) -> float:
    """Compute residual given predicted and actual

    Args:
        predicted (float): predicted emotive value
        actual (float): actual emotive value
    """

    return (actual - predicted)


def compute_abs_residual(predicted: float, actual: float):
    """Compute absolute residual

    Args:
        predicted (float): predicted emotive value
        actual (float): actual emotive value
    """
    return abs(actual - predicted)


def compute_squared_residual(predicted: float, actual: float):
    """Compute absolute residual

    Args:
        predicted (float): predicted emotive value
        actual (float): actual emotive value
    """
    return math.pow(actual - predicted, 2)


def smape(previous_smape: float, count: int, abs_residual: float, predicted: float, actual: float):
    """Computes the new SMAPE, given previous smape,count, predicted and actual value

    Args:
        count (int): Response count for specific emotive on node
        predicted (float): predicted emotive value
        actual (float): actual emotive value
        previous_smape (float): Previous smape.
    """
    return 100 * ((((previous_smape / 100) * count) + ((2 * abs_residual) / (abs(predicted) + abs(actual)))) / (count + 1))


def rmse(previous_rmse: float, count: int, squared_residual: float):
    """Compute new RMSE given previous RMSE value, count, and new squared residual

    Args:
        previous_rmse (float): previous RMSE value
        count (int): Response count for specific emotive on node
        squared_residual (float): current squared residual value
    """
    return math.sqrt(((math.pow(previous_rmse, 2) * count) + squared_residual) / (count + 1))


def f1_score(tp: int, fp: int, fn: int):
    """Compute F1 Score

    Args:
        tp (int): True Positive count
        fp (int): False Positive count
        fn (int): False Negative count
    """
    f1 = 0.0
    try:
        f1 = (2 * tp) / ((2 * tp) + fp + fn)
    except ZeroDivisionError:
        pass
    return f1


def false_discovery_rate(tp: int, fp: int):
    """Compute FDR

    Args:
        tp (int): True Positive count
        fp (int): False Positive count
    """
    fdr = 0.0
    try:
        fdr = 100.0 * fp / (fp + tp)
    except ZeroDivisionError:
        pass
    return fdr


def true_negative_rate(tn: int, fp: int):
    """Compute FDR

    Args:
        tn (int): True Negative count
        fp (int): False Positive count
    """
    tnr = 0.0
    try:
        tnr = 100.0 * tn / (tn + fp)
    except ZeroDivisionError:
        pass
    return tnr


def true_positive_rate(tp: int, fn: int):
    """Compute FDR

    Args:
        tp (int): True Positive count
        fn (int): False Negative count
    """
    tpr = 0.0
    try:
        tpr = 100.0 * tp / (tp + fn)
    except ZeroDivisionError:
        pass
    return tpr


def negative_predictive_value(tn: int, fn: int):
    """Compute NPV

    Args:
        tn (int): True Negative count
        fn (int): False Negative count
    """
    npv = 0.0
    try:
        npv = 100.0 * tn / (tn + fn)
    except ZeroDivisionError:
        pass
    return npv


def false_negative_rate(fn: int, tp: int):
    """Compute FNR

    Args:
        fn (int): False Negative count
        tp (int): True Positive count
    """
    fnr = 0.0
    try:
        fnr = 100.0 * fn / (fn + tp)
    except ZeroDivisionError:
        pass
    return fnr


def false_omission_rate(fn: int, tn: int):
    """Compute FOR

    Args:
        fn (int): False Negative count
        tn (int): True Negative count
    """
    false_or = 0.0
    try:
        false_or = 100.0 * fn / (fn + tn)
    except ZeroDivisionError:
        pass
    return false_or


def false_positive_rate(fp: int, tn: int):
    """Compute FPR

    Args:
        fp (int): False Positive count
        tn (int): True Negative count
    """
    fpr = 0.0
    try:
        fpr = 100.0 * fp / (fp + tn)
    except ZeroDivisionError:
        pass
    return fpr


def positive_likelihood_ratio(tp: int, fp: int, tn: int, fn: int):
    """Compute LR+

    Args:
        tp (int): True Positive count
        fp (int): False Positive count
        tn (int): True Negative count
        fn (int): False Negative count
    """
    lr_plus = 0.0
    try:
        lr_plus = true_positive_rate(
            tp=tp, fn=fn) / false_positive_rate(fp=fp, tn=tn)
    except ZeroDivisionError:
        pass
    return lr_plus


def negative_likelihood_ratio(tp: int, fp: int, tn: int, fn: int):
    """Compute LR-

    Args:
        tp (int): True Positive count
        fp (int): False Positive count
        tn (int): True Negative count
        fn (int): False Negative count
    """
    lr_minus = 0.0
    try:
        lr_minus = false_negative_rate(
            fn=fn, tp=tp) / true_negative_rate(tn=tn, fp=fp)
    except ZeroDivisionError:
        pass
    return lr_minus


def prevalence_threshold(tp: int, fp: int, tn: int, fn: int):
    """Compute PT

    Args:
        tp (int): True Positive count
        fp (int): False Positive count
        tn (int): True Negative count
        fn (int): False Negative count
    """
    pt = 0.0
    try:
        pt = math.sqrt(false_positive_rate(fp=fp, tn=tn)) / (math.sqrt(
            true_positive_rate(tp=tp, fn=fn)) + math.sqrt(false_positive_rate(fp=fp, tn=tn)))
    except ZeroDivisionError:
        pass
    return pt


def threat_score(tp: int, fp: int, fn: int):
    """Compute TS

    Args:
        tp (int): True Positive count
        fp (int): False Positive count
        fn (int): False Negative count
    """
    ts = 0.0
    try:
        ts = 100.0 * tp / (tp + fn + fp)
    except ZeroDivisionError:
        pass
    return ts


def update_accuracy(tp: int, tn: int, overall_count: int) -> float:
    """Update accuracy metrics

    Args:
        tp (int): True Positives
        tn (int): True Negatives
        overall_count (int): current testing record count

    Returns:
        float: accuracy
    """
    accuracy = 0.0
    try:
        accuracy = 100.0 * (tp + tn) / overall_count
    except ZeroDivisionError:
        pass
    return accuracy


def update_precision(tp: int, tn: int, response_count: int) -> float:
    """Update precision metrics

    Args:
        tp (int): True Positives
        tn (int): True Negatives
        response_count (int): node response count

    Returns:
        float: precision
    """
    precision = 0.0
    try:
        precision = 100.0 * (tp + tn) / response_count
    except ZeroDivisionError:
        pass
    return precision


def plot_confusion_matrix(test_num: int, class_metrics_data_structures: dict, results_dir=None):
    """
    Takes a node classification test to create a confusion matrix.
    This version includes the i_dont_know or unknown label.
    """

    for node_name, class_metrics_data in class_metrics_data_structures.items():
        # print(f'-------------Test#{test_num}-{node_name}-Plots-------------')
        sorted_labels = set(deepcopy(class_metrics_data['labels']))
        label_set = set(sorted_labels).union(class_metrics_data['predictions'] + list(chain(*class_metrics_data['actuals'])))
        
        sorted_labels = [str(label)
                         for label in label_set if label is not None]
        sorted_labels.append(str(None))
        # sorted_labels = sorted(class_metrics_data['labels'])
        actuals = [[str(elem) for elem in act]
                   for act in class_metrics_data['actuals']]

        sorted_labels = sorted(sorted_labels)
        preds = [str(pred) for pred in class_metrics_data['predictions']]
        logger.debug('confusion_matrix preds=%s, %s',len(preds), preds)
        logger.debug('confusion_matrix actuals=%s, %s',len(actuals), actuals)
        try:
            cm = confusion_matrix(actuals,  # TODO: each "actual" is a list, to support multiclass labels. Need to find solution here
                                  preds,
                                  labels=sorted_labels)
        except ValueError as e:  # thrown when there are no predictions, and nothing to plot
            logger.exception("broke in plot_confusion_matrix")
            return
        disp = ConfusionMatrixDisplay(confusion_matrix=cm,
                                      display_labels=sorted_labels)

        disp.plot()
        disp.ax_.set_title(f'Test#{test_num}-{node_name} Confusion Matrix')
        current_figure = plt.gcf()
        if is_notebook():
            plt.show()
        if results_dir is not None:
            cf_filename = Path(results_dir).joinpath(
                f'./confusion_matrix_{node_name}_test_{test_num}.png')
            # cf_filename = f'./confusion_matrix_{node_name}_test_{test_num}.png'
            # print(f'attempting to save confusion_matrix to: {cf_filename}')
            try:
                current_figure.savefig(cf_filename)
            except Exception as error:
                print(
                    f'error saving confusion matrix to {cf_filename}: {str(error)}')
        plt.close()

def plot_emotives_value_charts(test_num: int, emotive_value_results: dict, results_filepath: str, QUIET: bool = False):
    """Plot charts for emotives value charts
    """
    for node_name, node_emotive_metrics in emotive_value_results.items():
        logger.debug(
            f'-----------------Test#{test_num}-{node_name}-Plots-----------------')
        for emotive_name, data in sorted(node_emotive_metrics.items()):
            labels = 'precision', 'miss'
            if isnan(data['metrics']['1-smape']):
                continue
            if data['metrics']['1-smape'] is None:
                sizes = [0, 100]
            else:
                sizes = [data['metrics']['1-smape'],
                            100 - data['metrics']['1-smape']]
            explode = (0, 0)
            _, ax1 = plt.subplots()
            ax1.title.set_text(f'{node_name} - {emotive_name}')
            ax1.pie(sizes, explode=explode, labels=labels, autopct='%1.1f%%',
                    shadow=True, startangle=90)
            # Equal aspect ratio ensures that pie is drawn as a circle.
            ax1.axis('equal')
            colors = ['gray', 'skyblue']
            patches, texts = plt.pie(sizes, colors=colors, startangle=90)
            plt.legend(patches, labels, loc="best")
            supplementary_data = {'SMAPE Precision': data['metrics']['1-smape'],
                                    'RMSE': data['metrics']['rmse']}
            plt.figtext(0, 0, f"{pd.Series(supplementary_data).round(1).to_string()}", ha="center", fontsize=18, bbox={
                        "facecolor": "orange", "alpha": 0.5, "pad": 5})
            pie_plot_filepath = Path(f"{results_filepath}").joinpath(
                f"./test_{test_num}_{node_name}_{emotive_name}_pie.png")
            pva_plot_filepath = Path(f"{results_filepath}").joinpath(
                f"./test_{test_num}_{node_name}_{emotive_name}_pva.png")

            df = pd.DataFrame({'predicted': data['predictions'],
                                'actuals': data['actuals']})
            predicted_vs_actual = go.Figure()
            predicted_vs_actual.update_layout(title=dict(text=f"Test #{test_num}: {emotive_name} values on {node_name}"),
                                                xaxis=dict(
                                                    title="Testing Record"),
                                                yaxis=dict(
                                                    title=f"{emotive_name} Value")
                                                )
            predicted_vs_actual.add_trace(go.Scatter(
                x=df.index, y=df.actuals, fill='tozeroy', name='Actual'))
            predicted_vs_actual.add_trace(go.Scatter(
                x=df.index, y=df.predicted, fill='tonexty', name='Predicted'))
            if results_filepath is not None:
                try:
                    plt.savefig(pie_plot_filepath, dpi=300,
                                bbox_inches='tight')
                    predicted_vs_actual.write_image(file=pva_plot_filepath)
                except Exception as error:
                    logger.debug(
                        f"Not able to save figure in assigned results directory! Please add an appropriate directory: {str(error)}")
                    pass
            if is_notebook() and not QUIET:
                plt.show()
                predicted_vs_actual.show()

    plt.close('all')

def is_notebook() -> bool:  # pragma: no cover (helper function to determine if we are in a jupyter notebook)
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':
            return True   # Jupyter notebook or qtconsole
        elif shell == 'TerminalInteractiveShell':
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter

def pvt2df(overall_results: dict):
    _overall_results = deepcopy(overall_results)
    result_dicts = []
    for node, node_results in _overall_results.items():
        node_metrics = node_results['metrics']
        node_data_dict = {}
        node_data_dict['node'] = node
        for key, val in node_metrics.items():
            node_data_dict[key] = val
        result_dicts.append(node_data_dict)
    
    return pd.DataFrame.from_dict(result_dicts)
