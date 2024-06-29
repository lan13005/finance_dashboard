import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

import sys
sys.path.append("../")

import dash
from dash import dcc, html, Input, Output
import plotly.graph_objs as go


def is_convertible_to_float(value):
    if pd.isnull(value):
        return False
    try:
        float(value)
        return True
    except ValueError:
        return False


# load the data
df_chase = pd.read_csv("Chase_WF_total_aggregated.CSV")

# convert the date types of Transaction Date
df_chase["Transaction Date"] = pd.to_datetime(df_chase["Transaction Date"])
df_chase = df_chase[df_chase["Amount"].apply(is_convertible_to_float)]
df_chase["Amount"] = df_chase["Amount"].astype(float)

categories = df_chase["Category"].unique()
cmap = plt.get_cmap("tab20", len(categories))
category_colors = {
    category: mcolors.rgb2hex(cmap(i / len(categories)))
    for i, category in enumerate(categories)
}

df_groups = []
for df_group, date_shift in zip(
    [df_chase[df_chase["Amount"] > 0], df_chase[df_chase["Amount"] <= 0]], [-5, 5]
):
    df_group["Transaction Date"] = (
        df_group["Transaction Date"].dt.to_period("M").dt.to_timestamp()
    )
    groups = ["Transaction Date", "Category"]
    df_grouped = df_group.groupby(groups)["Amount"].sum().reset_index()
    date_sums = df_grouped.groupby("Transaction Date")["Amount"].sum().reset_index()
    date_sums.rename(columns={"Amount": "Total_Amount"}, inplace=True)
    df_grouped = pd.merge(df_grouped, date_sums, on="Transaction Date")
    df_grouped["Percent Spend"] = df_grouped["Amount"] / df_grouped["Total_Amount"]
    df_grouped.rename(columns={"Amount": "Absolute Spend"}, inplace=True)
    # df_grouped.drop(columns=["Total_Amount"], inplace=True)
    df_grouped["Transaction Date"] = df_grouped["Transaction Date"] + pd.DateOffset(
        days=date_shift
    )

    df_groups.append(df_grouped)

# calculate the net amount
df_total = df_chase.copy()
df_total["Transaction Date"] = (
    df_total["Transaction Date"].dt.to_period("M").dt.to_timestamp()
)
df_totaled = df_total.groupby("Transaction Date")["Amount"].sum().reset_index()

# line_plot = go.Scatter(
#     x=date_sums["Transaction Date"],
#     y=date_sums["Total_Amount"],
#     mode='lines+markers',
#     name='Total Amount',
#     yaxis='y2',
#     marker=dict(color='black')
# )
# data = [line_plot]
# for category in df_grouped["Category"].unique():
#     category_data = df_grouped[df_grouped["Category"] == category]
#     data.append(go.Bar(
#         x=category_data["Transaction Date"],
#         y=category_data["Percent Spend"],
#         name=category
#     ))

# # Create the Dash app
# app = dash.Dash(__name__)

# app.layout = html.Div([
#     dcc.Graph(
#         id='Amount',
#         figure={
#             'data': data,
#             'layout': go.Layout(
#                 title='Balance Changes Over Time',
#                 xaxis=dict(title='Transaction Date'),
#                 yaxis=dict(title='Percent Spend', side='left'),
#                 yaxis2=dict(
#                     title='Total Amount',
#                     overlaying='y',
#                     side='right',
#                     showgrid=False  # Optional: hide grid for secondary y-axis
#                 ),
#                 barmode='stack',  # 'group' for grouped bars
#                 showlegend=True,
#             )
#         }
#     )
# ])

# if __name__ == '__main__':
#     app.run_server(debug=True)


################################################################
# Stock ticker Balance changes
################################################################

# Create the Dash app
app = dash.Dash(__name__)

app.layout = html.Div(
    [
        dcc.RadioItems(
            id="groupby-radio",
            options=[
                {"label": "Percentage", "value": "Percent Spend"},
                {"label": "Absolute", "value": "Absolute Spend"},
            ],
            value="Percent Spend",
            labelStyle={"display": "inline-block"},
        ),
        dcc.Checklist(
            id="show-total-amount",
            options=[{"label": "Show Total Amount", "value": "show"}],
            value=["show"],
            style={"margin-top": "10px"},
        ),
        dcc.Graph(id="amount-plot"),
    ]
)


@app.callback(
    Output("amount-plot", "figure"),
    [Input("groupby-radio", "value"), Input("show-total-amount", "value")],
)
def update_graph(field, show_total):

    data = []
    if "show" in show_total:
        # y = np.zeros(len(df_groups[0]["Transaction Date"]))
        # print(df_groups[0]["Total_Amount"].values.shape)
        # print(df_groups[1]["Total_Amount"].values.shape)
        # y += df_groups[0]["Total_Amount"].values
        # y += df_groups[1]["Total_Amount"].values
        line_plot = go.Scatter(
            x=df_totaled["Transaction Date"],
            y=df_totaled["Amount"],
            mode="lines+markers",
            name="Total Amount",
            yaxis="y2",
            marker=dict(color="black"),
        )
        data.append(line_plot)

    df_gain, df_spent = df_groups[0], df_groups[1]
    for category in df_gain["Category"].unique():
        category_data = df_gain[df_gain["Category"] == category]
        data.append(
            go.Bar(
                x=category_data["Transaction Date"],
                y=category_data[field],
                name=category,
                marker=dict(color=category_colors[category]),
            )
        )
    for category in df_spent["Category"].unique():
        category_data = df_spent[df_spent["Category"] == category]
        data.append(
            go.Bar(
                x=category_data["Transaction Date"],
                y=category_data[field],
                name=category,
                marker=dict(color=category_colors[category]),
            )
        )

    # lim_total = np.max(np.abs(df_totaled["Amount"]))
    lim_category = np.max(
        [
            df_groups[0].groupby("Transaction Date").sum()["Absolute Spend"].max(),
            -df_groups[1].groupby("Transaction Date").sum()["Absolute Spend"].min(),
        ]
    )

    lims = [-lim_category, lim_category] if field == "Absolute Spend" else [0, 1]
    figure = {
        "data": data,
        "layout": go.Layout(
            title="Monthly Spending by Category",
            xaxis=dict(title=""),
            yaxis=dict(
                title=field,
                side="left",
                range=lims,
            ),
            yaxis2=dict(
                title="Total Amount",
                overlaying="y",
                side="right",
                range=[-lim_category, lim_category],
                showgrid=False,  # Optional: hide grid for secondary y-axis
            ),
            barmode="stack",  # 'group' for grouped bars
            showlegend=True,
        ),
    }

    return figure


if __name__ == "__main__":
    app.run_server(debug=True)
