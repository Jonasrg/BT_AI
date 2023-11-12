import pandas as pd
from IPython.display import display

def style_df(df):
    display(df.style \
    .format(precision=3) \
    .set_table_styles([
        {'selector': 'th.col_heading', 'props': 'text-align: left;'},
        {'selector': 'th.col_heading.level0', 'props': 'font-size: 1.3em;'}
    ]) \
    .hide())
