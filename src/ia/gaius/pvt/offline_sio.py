import plotly.express as px
import plotly.graph_objects as go
import json
import pandas as pd
import numpy as np
from ia.gaius.agent_client import AgentClient
from copy import deepcopy


def make_classification_pie_chart(classification_counts):
    """Return a pie chart of classification frequency distribution"""
    class_df = pd.DataFrame([dict(Classification=k, Count=v) for k, v in classification_counts.items()])
    class_df.sort_values(by=['Classification'], inplace=True)
    classification_graph = px.pie(class_df, values='Count', names="Classification", title="Classification Distribution")
    return classification_graph


class offline_sio:
    def __init__(self, agent: AgentClient = None):
        print('init offline sio')
        self.log = []
        self.agent = agent

    def emit(self, topic, message, to=None):
        # print(f'broadcasting on topic {topic} to {to}: {message}')
        self.log.append(deepcopy(message))

    def dump(self, filename):
        with open(filename, 'w') as f:
            json.dump(self.log, f)

    def load(self, filename):
        with open(filename, 'r') as f:
            self.log = json.load(f)

    def clear(self):
        self.log = []

    def make_report(self, filepath="report.html"):
        """Generate plotly report from PVT results captured in self.log

        Args:
            filepath (str, optional): Path at which to save the html report. Defaults to "report.html".

        Returns:
            str: path of html report
        """
        final_record = [x for x in self.log if x['status'] == 'finished']
        assert (len(final_record) == 1)

        # data from final entry
        final_record = final_record[0]

        print(f'{final_record.keys()}')
        print(f'{final_record["metrics"].keys()}')
        classification_counts = final_record['metrics']['classification_counter']
        cg = make_classification_pie_chart(classification_counts)

        testing_records = [deepcopy(x) for x in self.log if x['status'] == 'testing']
        print(f'{len(testing_records)=}')

        testing_records = sorted(testing_records, key=lambda x: x['current_record'])
        testing_record_count = len(testing_records)
        if self.agent:
            for tmp_record in testing_records:
                tmp_record['metrics']['recall_threshold'] = self.agent.get_gene('recall_threshold')

        nodes_df = []
        print(f"{testing_records[0]['metrics']['predicted'].keys()=}")

        node_data = self.agent.get_all_genes()
        flattened_node_data = []
        for k, v in node_data.items():
            new_v = {**v['genes']}
            new_v['node_name'] = k
            new_v['node_id'] = self.agent.genome.primitive_map[k]
            flattened_node_data.append(deepcopy(new_v))

        flattened_node_data = sorted(flattened_node_data, key=lambda x: x['node_name'])
        node_data = pd.DataFrame(flattened_node_data)
        # display(node_data)
        node_fig = go.Figure(data=[go.Table(header=dict(values=list(node_data.columns),
                                                        fill_color='paleturquoise',
                                                        align='left'),
                                            cells=dict(values=node_data.transpose().values.tolist(),
                                                       fill_color='lavender',
                                                       align='left'))])
        node_fig.show()

        for node in testing_records[0]['metrics']['predicted'].keys():
            for record in testing_records:
                tmp_record = deepcopy(record)

                del tmp_record['metrics']['classification_counter']
                del tmp_record['metrics']['idx']
                actual = tmp_record['metrics']['actual']
                del tmp_record['metrics']['actual']

                # Update record with node specific info
                # print(f'{tmp_record["metrics"]=}')
                tmp_record['metrics']['recall_threshold']['hive'] = 1.0
                tmp_record.update({k: v[node] for k, v in tmp_record['metrics'].items()})
                tmp_record['node'] = node
                tmp_record['actual'] = actual
                if 'recall_threshold' in tmp_record:
                    if isinstance(tmp_record['recall_threshold'], dict):
                        tmp_record['recall_threshold'] = tmp_record['recall_threshold']['recall_threshold']
                nodes_df.append(tmp_record)

        # make dataframe out of node specific testing records
        nodes_df = pd.DataFrame(nodes_df)
        accuracies_g = px.line(nodes_df,
                               x='current_record',
                               y='accuracy',
                               range_y=[0, 1],
                               title="Running Accuracy per Node",
                               color='node',
                               markers=False,
                               labels={"current_record": "Testing Record index",
                                       "accuracy": "Running Accuracy (0.0 to 1.0)",
                                       "node": "Cognitive Processor"
                                       }
                               )
        precisions_g = px.line(nodes_df,
                               x='current_record',
                               y='precision',
                               range_y=[0, 1],
                               title="Running Precision per Node",
                               color='node',
                               labels={"current_record": "Testing Record index",
                                       "precision": "Running Precision (0.0 to 1.0)",
                                       "node": "Cognitive Processor"
                                       }
                               )
        resp_perct_g = px.line(nodes_df,
                               x='current_record',
                               y='response_percentage',
                               range_y=[0, 1],
                               title="Response Percentage per Node",
                               color='node',
                               labels={"current_record": "Testing Record index",
                                       "response_percentage": "Response Percentage (0.0 to 1.0)",
                                       "node": "Cognitive Processor"
                                       }
                               )

        # fig2 = go.Figure(data=[go.Surface(y=nodes_df['recall_threshold'], x=nodes_df['current_record'], z=nodes_df['precision'])])
        # fig2.show()
        fig = px.scatter_3d(nodes_df, y='recall_threshold', x='current_record', z='accuracy', color='node')
        fig.update_traces(marker_size=1)

        fig2 = px.line_3d(nodes_df, y='recall_threshold', x='current_record', z='precision', line_group='node', color='node')
        fig2.update_traces(marker_size=1)

        # x = nodes_df['current_record']
        # y = nodes_df['recall_threshold']
        z = nodes_df['precision']

        z2 = nodes_df[['precision']].copy()
        z2 = np.tile(z2, [z.shape[0], 1])

        fig3 = None

        # split testing records into 100 parts
        # get round increment to nearest 10
        fig3_increment = round(testing_record_count / 100)
        fig3_increment = round(fig3_increment / 10) * 10
        # print(f'{fig3_increment=}')

        if fig3_increment >= 10:
            fig3 = go.Figure()
            for step in range(0, testing_record_count, fig3_increment):
                subset = nodes_df.loc[nodes_df['current_record'] == step]
                fig3.add_trace(go.Scatter(visible=False,
                                          line=dict(color="#00CED1", width=2),
                                          name=f'current_record={step}',
                                          x=subset['recall_threshold'],
                                          y=subset['precision'],
                                          mode='lines+markers',
                                          hoverinfo='text',
                                          text="Node: " + subset['node'].astype(str) + "<br>Running Precision: " + subset['precision'].round(4).astype(str) + "<br> Running Accuracy: " + subset['accuracy'].round(4).astype(str),
                                          )
                               )
            fig3.data[0].visible = True

            steps = []
            for i in range(len(fig3.data)):
                step = dict(
                    method="update",
                    args=[{"visible": [False] * len(fig3.data)},
                          {"title": f"Recall threshold vs Running Precision at record {str(i * fig3_increment)}"}],  # layout attribute
                    label=str(i * fig3_increment)
                )
                step["args"][0]["visible"][i] = True  # Toggle i'th trace to "visible"
                steps.append(step)

            sliders = [dict(
                active=0,
                currentvalue={"prefix": "Current Record: "},
                pad={"t": 50},
                steps=steps
            )]

            fig3.update_layout(
                sliders=sliders,
                title=dict(text="Recall threshold vs Running Precision at record 0"),
                xaxis=dict(title="Recall Threshold"),
                yaxis=dict(title="Running Precision"),
            )
            fig3.show()

        # display everything
        fig.show()
        fig2.show()
        accuracies_g.show()
        precisions_g.show()
        resp_perct_g.show()
        cg.show()

        with open(filepath, 'w') as f:
            f.write(node_fig.to_html(include_plotlyjs='True', full_html=False, default_width='80%', default_height='50%'))
            f.write(accuracies_g.to_html(include_plotlyjs=False, full_html=False, default_width='80%', default_height='50%'))
            f.write(precisions_g.to_html(include_plotlyjs=False, full_html=False, default_width='80%', default_height='50%'))
            f.write(resp_perct_g.to_html(include_plotlyjs=False, full_html=False, default_width='80%', default_height='50%'))
            f.write(cg.to_html(include_plotlyjs=False, full_html=False, default_width='80%', default_height='50%'))
            f.write(fig.to_html(include_plotlyjs=False, full_html=False, default_width='80%', default_height='50%'))
            f.write(fig2.to_html(include_plotlyjs=False, full_html=False, default_width='80%', default_height='50%'))
            if fig3:
                f.write(fig3.to_html(include_plotlyjs=False, full_html=False, default_width='80%', default_height='50%'))
        return filepath
