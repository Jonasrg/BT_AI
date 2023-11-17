# helper fucntions for statistics and visuals
import statsmodels.api as sm
from statsmodels.iolib.summary2 import summary_col


# run regressions and save results in dict
def run_regressions(data, industries, indicators, x_cols, successive=True):
    results = dict()
    for industry in industries:
        for indicator in indicators:
            tmp_df = data[
                (data["nace_r2"] == industry) & (data["indic_sb_name"] == indicator)
            ]
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
    len_results_sublists = len(results[list(results.keys())[0]][list(results[list(results.keys())[0]].keys())[0]])
    summarized = dict()
    if by == "indicator":
        for indicator in indicators:
            result_list = []
            model_names = [industry for industry in industries for interval in range(len_results_sublists)]
            for industry in industries:
                result_list += results[industry][indicator]
            summarized[indicator] = summary_col(result_list, regressor_order=result_list[-1].params.index.tolist(),
                                                stars=True, model_names=model_names)
        return summarized
    if by == "industry":
        for industry in industries:
            result_list = []
            model_names = [indicator for indicator in indicators for interval in range(len_results_sublists)]
            for indicator in indicators:
                result_list += results[industry][indicator]
            summarized[industry] = summary_col(result_list, regressor_order=result_list[-1].params.index.tolist(),
                                               stars=True, model_names=model_names)
        return summarized
    else:
        raise ValueError("Argument by either industry or indicator")
