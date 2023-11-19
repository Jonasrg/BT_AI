# helper fucntions for statistics and visuals
import statsmodels.api as sm
from statsmodels.iolib.summary2 import summary_col
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd


# run regressions and save results in dict
def run_regressions(data, industries, indicators, x_cols, successive=True):
    results = dict()
    for industry in industries:
        for indicator in indicators:
            tmp_df = data[(data["NACE"] == industry) & (data["Indicator"] == indicator)]
            sub_results = []
            if successive:
                for i in range(0, len(x_cols)):
                    exogenous = x_cols[: i + 1]
                    x = tmp_df[exogenous]
                    x = sm.add_constant(x)
                    y = tmp_df["OBS_VALUE"]
                    sub_results.append(sm.OLS(y, x).fit())
            else:
                exogenous = x_cols
                x = tmp_df[exogenous]
                x = sm.add_constant(x)
                y = tmp_df["OBS_VALUE"]
                sub_results.append(sm.OLS(y, x).fit())

            if industry not in results.keys():
                results[industry] = dict()
            results[industry][indicator] = sub_results
    return results


# summarize results saved in dict returned from run_regression()
def summarize_results(results, indicators, industries, by="indicator"):
    len_results_sublists = len(
        results[list(results.keys())[0]][
            list(results[list(results.keys())[0]].keys())[0]
        ]
    )
    summarized = dict()
    if by == "indicator":
        for indicator in indicators:
            result_list = []
            model_names = [
                industry
                for industry in industries
                for interval in range(len_results_sublists)
            ]
            for industry in industries:
                result_list += results[industry][indicator]
            summarized[indicator] = summary_col(
                result_list,
                regressor_order=result_list[-1].params.index.tolist(),
                stars=True,
                model_names=model_names,
                float_format="%.1f",
            )
        return summarized
    if by == "industry":
        for industry in industries:
            result_list = []
            model_names = [
                indicator
                for indicator in indicators
                for interval in range(len_results_sublists)
            ]
            for indicator in indicators:
                result_list += results[industry][indicator]
            summarized[industry] = summary_col(
                result_list,
                regressor_order=result_list[-1].params.index.tolist(),
                stars=True,
                model_names=model_names,
                float_format="%.1f",
            )
        return summarized
    else:
        raise ValueError("Argument by either industry or indicator")


PLOTLY_TEMPLATE = "plotly_white"


def subplots_two_yaxes(
    df: pd.DataFrame,
    x: str,
    x_name: str,
    y1: str,
    y2: str,
    y1_name: str,
    y2_name: str,
    by: str,
    rows: int,
    cols: int,
):
    fig = make_subplots(
        rows=rows,
        cols=cols,
        specs=[[{"secondary_y": True}] * cols for i in range(rows)],
        subplot_titles=list(df[by].unique()),
    )
    # add traces
    for index, value in enumerate(df[by].unique()):
        row = int(index / 2) + 1
        col = 1 if index % 2 == 0 else 2
        # add trace for left y-axis
        fig.add_trace(
            go.Scatter(
                x=df[df[by] == value]["Year"],
                y=df[df[by] == value][y1],
                mode="lines",
                line=dict(color="royalblue"),
                name=y1_name,
            ),
            secondary_y=False,
            row=row,
            col=col,
        )
        # add trace for right y-axis
        fig.add_trace(
            go.Scatter(
                x=df[df[by] == value][x],
                y=df[df[by] == value][y2],
                mode="lines",
                line=dict(color="firebrick", dash="dash"),
                name=y2_name,
            ),
            secondary_y=True,
            row=row,
            col=col,
        )
    # Set y-axes titles
    axes_dict = dict(size=11)
    # left y-axis
    row = rows // 2 + 1 if rows % 2 != 0 else rows / 2
    fig.update_yaxes(
        title_text=y1_name,
        secondary_y=False,
        title_font=axes_dict,
        row=row,
        col=1,
        overwrite=True,
    )
    # right y-axis
    fig.update_yaxes(
        title_text=y2_name,
        secondary_y=True,
        title_font=axes_dict,
        row=row,
        col=cols,
        overwrite=True,
    )

    # set font size and color for subplot titles
    fig.update_annotations(font_size=11)

    # set x-axis title
    for i in range(1, cols + 1):
        fig.update_xaxes(title_text=x_name, title_font=axes_dict, row=3, col=i)
        fig.update_xaxes(
            title_text=x_name, title_font=axes_dict, row=3, col=i, overwrite=False
        )

    # hide duplicate legend entries
    names = set()
    fig.for_each_trace(
        lambda trace: trace.update(showlegend=False)
        if (trace.name in names)
        else names.add(trace.name)
    )
    # set legend position
    fig.update_layout(showlegend=True)
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="right", x=1)
    )
    fig.update_layout(template=PLOTLY_TEMPLATE)
    return fig
