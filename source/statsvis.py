# helper fucntions for statistics and visuals
import statsmodels.api as sm
from statsmodels.iolib.summary2 import summary_col
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from statsmodels.stats.stattools import durbin_watson, jarque_bera
from statsmodels.stats.diagnostic import het_breuschpagan

FLOAT_FORMAT = '%.4f'


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
                float_format=FLOAT_FORMAT,
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
                float_format=FLOAT_FORMAT,
            )
        return summarized
    else:
        raise ValueError("Argument by either industry or indicator")


def extract_pvalues(results, decimals=5, stars=True, threshold=0.05) -> list:
    # create table of pvalues
    # round decimals
    # create stars if coefficient is positive
    # return only pvalues that are underneath the threshold
    pvalues = []
    for industry in results.keys():
        for indicator in results[industry].keys():
            if len(results[industry][indicator]) == 1:
                pval = results[industry][indicator][0].pvalues["Sum patents"].round(decimals)
                coef = results[industry][indicator][0].params["Sum patents"]
                if pval < threshold:
                    if stars is True:
                        pval = f"{pval}*" if coef >= 0 else f"{pval}"
                else:
                    pval = ""
                pvalues.append(
                    {
                        "Industry": industry,
                        "Indicator": indicator,
                        "P value": pval,
                    }
                )
            else:
                pvals = [results[industry][indicator][i].pvalues["Sum patents"].round(decimals) for i in range(0, len(results[industry][indicator]))]
                coef = [results[industry][indicator][i].params["Sum patents"].round(decimals) for i in range(0, len(results[industry][indicator]))]
                for index, value in enumerate(pvals):
                    if pvals[index] < threshold:
                        if stars is True:
                            pvals[index] = f"{pvals[index]}*" if coef[index] >= 0 else f"{pval[index]}"
                    else:
                        pvals[index] = ""
                pvalues.append(
                    {
                        "Industry": industry,
                        "Indicator": indicator,
                        "P value": pvals,
                    }
                )
    pvalues = pd.DataFrame.from_dict(pvalues)
    pvalues = pvalues.pivot(index="Indicator", columns="Industry", values="P value")
    return pvalues


def sample_size(df:pd.DataFrame, by:str):
    samples = dict()
    samples["sum"] = dict()
    samples["count"] = dict()
    if by == "nace":
        for nace in df["NACE"].unique():
            samples["sum"][nace] = [int(df[df["NACE"] == nace].drop_duplicates(subset="Year")["Sum patents"].sum())]
            samples["count"][nace] = [int(df[df["NACE"] == nace].drop_duplicates(subset="Year")["Sum patents"].count())]
    if by == "indicator":
        for indicator in df["Indicator"].unique():
            samples["sum"][indicator] = [int(df[df["Indicator"] == indicator]["Sum patents"].sum())]
            samples["count"][indicator] = [int(df[df["Indicator"] == indicator]["Sum patents"].count())]
    return samples


def extent_pvalues(pvalues, prepped_df, sum_name="Patents (sum)", count_name="Sample size"):
    # create DataFrames holding sum of patents for industries and indicators
    ss_indic = pd.DataFrame.from_dict(sample_size(prepped_df, by="indicator")["sum"], orient="index").rename(columns={0: sum_name})
    ss_nace = pd.DataFrame.from_dict(sample_size(prepped_df, by="nace")["sum"], orient="columns").rename(index={0: sum_name})
    # create dataframes holdung sample count for industries and indicators
    sc_indic = pd.DataFrame.from_dict(sample_size(prepped_df, by="indicator")["count"], orient="index").rename(columns={0: count_name})
    sc_nace = pd.DataFrame.from_dict(sample_size(prepped_df, by="nace")["count"], orient="columns").rename(index={0: count_name})
    # merge dataframes along index and columns
    df = pd.concat([pvalues, ss_nace])
    df = pd.concat([df, sc_nace])
    df = df.merge(ss_indic, left_index=True, right_index=True, how="left")
    df = df.merge(sc_indic, left_index=True, right_index=True, how="left")
    return df


def create_summary_statistics(results, cols, decimals=3, index=0) -> dict:
    """
    utility function to summarize main regression tests and key figures by industry

    PARAMS
    ------
    results: dict
        dictionary containing OLS result instances
    cols: list
        list of variables for which coefficients, p values and conf. interval is retrieved
    decimals: int
        Number of decimal places to round results to
    index: int
        If multiple result instances for each indicator, indicate which one to summarize
    """
    summary_statistics = dict()
    for industry in results.keys():
        industry_stats = None
        for indicator in results[industry].keys():
            res = results[industry][indicator][index]
            data = {
                "F-statistic": res.fvalue,
                "Prob (F-statistic)": res.f_pvalue,
                "Observations": res.nobs,
                "R-squared": res.rsquared,
                "Adj. R-squared": res.rsquared_adj,
                "Jarque-Bera": jarque_bera(res.resid)[1],
                "Skew": jarque_bera(res.resid)[2],
                "Kurtosis": jarque_bera(res.resid)[3],
                "Durbin-Watson": durbin_watson(res.resid),
                "Breusch-Pagan": het_breuschpagan(resid=res.resid, exog_het=res.model.exog)[1]
            }
            for i in cols:
                data[i + " Coef."] = res.pvalues[i]
                data[i + " p value"] = res.pvalues[i]
                data[i + " SE"] = res.bse[i]
                data[i + " Conf. lower"] = res.conf_int().at[i, 0]
                data[i + " Conf. upper"] = res.conf_int().at[i, 1]
            series = pd.Series(data=data)           
            tmp_df = series.to_frame(name=indicator).round(3)
            if industry_stats is None:
                industry_stats = tmp_df
            else:
                industry_stats = industry_stats.merge(tmp_df, left_index=True, right_index=True)
                industry_stats = industry_stats.round(decimals)
        summary_statistics[industry] = industry_stats
    return summary_statistics


# descriptives
def descriptives(df):
    data = {
        "len_df": len(df),
        "num_industries": len(df["Industry"].unique()),
        "industries": list(df["Industry"].unique()),
        "num_indicators": len(df["Indicator"].unique()),
        "indicators": list(df["Indicator"].unique()),
        "max_years": np.max(df.groupby(by=["NACE", "Indicator"]).size()),
        "min_years": np.min(df.groupby(by=["NACE", "Indicator"]).size()),
        "average_years": round(np.average(df.groupby(by=["NACE", "Indicator"]).size())),
    }
    for nace in df["NACE"].unique():
        data[f"{nace}_n_patents"] = (
            df[df["NACE"] == nace].drop_duplicates(subset="Year")["Sum patents"].sum()
        )
        data[f"{nace}_n_years"] = (
            df[(df["NACE"] == nace) & (df["Year"] != 0)]
            .drop_duplicates(subset="Year")["Year"]
            .count()
        )
    return data


# plotly visuals
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
