file_dir = 'C:\\Users\\kimju\\MPT-Quant\\MacroTrading'
css_dir = 'C:\\Users\\kimju\\MPT-Quant\\SystemMacro_App\\pages\\style.css'

import streamlit as st
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import datetime
import time
from datetime import date
import pandas as pd
import numpy as np
import sys
sys.path.append(file_dir)
from Strategy_MA_Optimal_Portfolio import MultiAssetPortDataProcess
from Strategy_MA_Optimal_Portfolio import PortfolioAnalysis

if 'note' not in st.session_state:
    st.session_state.note = ''
   
st.session_state.note = st.sidebar.text_area('Note', st.session_state.note, height=300)

@st.cache_resource
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

@st.cache_resource(show_spinner=False)
def pull_strategy_data():
    mapdp =  MultiAssetPortDataProcess()
    return mapdp

@st.cache_resource(show_spinner=False)
def pull_port_functions(_mapdp):
    portfolio =  [[('1Y_KTB_TR', '3Y_KTB_TR'), 'value', 100000, 'delta', 1], 
                [('2Y_KTB_TR', '3Y_KTB_TR'), 'value', 100000, 'delta', 1], 
                [('3Y_KTB_TR', '5Y_KTB_TR'), 'value', 100000, 'delta', 1], 
                [('3Y_KTB_TR', '10Y_KTB_TR'), 'value', 100000, 'delta', 1],
                [('5Y_KTB_TR', '10Y_KTB_TR'), 'value', 100000, 'delta', 1],
                [('10Y_KTB_TR', '30Y_KTB_TR'), 'value', 100000, 'delta', 1],
                [('20Y_KTB_TR', '30Y_KTB_TR'), 'value', 100000, 'delta', 1],
                [('1Y_IRS_TR', '2Y_IRS_TR'), 'value', 100000, 'delta', 1],
                [('2Y_IRS_TR', '3Y_KTB_TR'), 'value', 100000, 'delta', 1],
                [('5Y_KTB_TR', '5Y_IRS_TR'), 'carry', 100000, 'delta', 1],
                [('7Y_KTB_TR', '7Y_IRS_TR'), 'carry', 100000, 'delta', 1],
                [('10Y_KTB_TR', '10Y_IRS_TR'), 'carry', 100000, 'delta', 1],
                ['3Y_KTB_TR', 'momentum', 100000, 'delta', 1],
                ['3Y_FUT_TR', 'momentum', 100000, 'delta', 1],
                ['10Y_KTB_TR', 'momentum', 100000, 'delta', 1]]
    pa = PortfolioAnalysis(portfolio, _mapdp)
    return pa

@st.cache_resource(show_spinner=False)
def pull_strategy_data_series(_mapdp):
    strategy_list_futures = list(_mapdp.fut_strategy_df.columns)
    strategy_list_rates = list(_mapdp.rates_strat_tr_cumprod_df.columns)
    strategy_list_rp = list(_mapdp.rp_strategy_df.columns)
    strategy_list_macrofactor = list(_mapdp.macro_factor_cum.columns)
    strategy_macrofactor = _mapdp.macro_factor_cum
    strategy_set = _mapdp.strategy_set_df.copy()
    strategy_set.index = pd.DatetimeIndex(strategy_set.index)
    strategy_set.index.name = None
    strategy_data = pd.concat([strategy_macrofactor, strategy_set], axis=1, sort=True).fillna(method='ffill')
    return strategy_list_futures, strategy_list_rates, strategy_list_rp, strategy_list_macrofactor, strategy_set, strategy_data

def get_strategy_name(options, _mapdp):
    strategy_list_rates = list(_mapdp.rates_strat_tr_cumprod_df.columns)
    if len(options) == 1:
        t_1 = options[0]+"_TR"
        strategy_selected_tr = t_1

    elif len(options) == 2:
        t_1 = options[0]+"_TR"
        t_2 = options[1]+"_TR"
        for s in strategy_list_rates:
            if len(s) == len(options) and t_1 in s and t_2 in s:
                strategy_selected = s
                strategy_selected_tr = s
                break
        
    elif len(options) == 3:
        t_1 = options[0]+"_TR"
        t_2 = options[1]+"_TR"
        t_3 = options[2]+"_TR"
        
        for s in strategy_list_rates:
            if len(s) == len(options) and t_1 in s and t_2 in s and t_3 in s:
                strategy_selected = s
                strategy_selected_tr = s
                break

    return strategy_selected_tr

def get_strategy(options, macro=False):
    if macro:
        strategy_selected = options
        strategy_selected_series_tr = strategy_data[options]
    else:
        strategy_selected = options
        strategy_selected_series_tr = strategy_set[options]

    return strategy_selected, strategy_selected_series_tr

def dict_to_df(dict):
    for i, k in enumerate(dict.items()):
        if i == 0:
            df = k[1]
        else:
            v = k[1]
            df = pd.concat([df, v], axis=1, sort=True).fillna(method='ffill')
    return df

def mean_highlighter(x):
    style_lt = "background-color: maroon; color:white;"
    style_gt = "background-color: midnightblue; color:white;"
    gt_mean = x > 0
    return [style_gt if i else style_lt for i in gt_mean]

def mean_highlighter_delta(x):
    style_lt = "background-color: maroon; color:white;"
    style_gt = "background-color: midnightblue; color:white;"
    gt_mean = x < 0
    return [style_gt if i else style_lt for i in gt_mean]

@st.cache_resource(show_spinner=False)
def get_port_opt_ret(port, opt_method, constraints, lookback, start_dt, end_dt):
    with st.spinner("Optimizing, Please Wait..."):
        expected_return_, portfolio_ret_df_, historical_weight_ = pa.calc_port_opt_ret(port, opt_method, constraints, lookback, start_dt, end_dt)
    return expected_return_, portfolio_ret_df_, historical_weight_

#데이터 불러오기
with st.spinner("Querying Data, Will take about 2 minutes, Please Wait..."):
    if 'mapdp' not in st.session_state:
        mapdp = pull_strategy_data()
        st.session_state.mapdp = mapdp
    else:
        mapdp = st.session_state.mapdp
    pa = pull_port_functions(mapdp)

    #전략리스트 및 가격데이터
    ktb = ['1Y_KTB', '2Y_KTB','3Y_KTB','4Y_KTB','5Y_KTB','7Y_KTB','10Y_KTB','20Y_KTB','30Y_KTB', 'IL10Y_KTB', 'BE10Y_KTB', '3Y_FUT', '10Y_FUT']
    swap = ['9M_IRS', '1Y_IRS','18M_IRS', '2Y_IRS','3Y_IRS','4Y_IRS','5Y_IRS','7Y_IRS','10Y_IRS']
    foreign = ['2Y_FUT_US', '5Y_FUT_US', '10Y_FUT_US', '30Y_FUT_US','2Y_FUT_GER', '5Y_FUT_GER', '10Y_FUT_GER'] 
    outright_list = ktb+swap+foreign
    strategy_list_futures, strategy_list_rates, strategy_list_rp, strategy_list_macrofactor, strategy_set, strategy_data = pull_strategy_data_series(mapdp)

with st.container():
    tab1, tab2, tab3 = st.tabs(['Portfolio', 'Current', 'New'])
    
    with open(css_dir) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

    with tab1:
        col1, col2, col3 = st.columns(3)
        option_1_list = []
        option_2_list = []
        option_3_list = []
        option_4_list = []
        option_5_list = []

        with st.container():
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others', ['Rates', 'Others'])

                with col1_2:
                    option_2 = st.selectbox('Type', [None, 'value', 'carry', 'momentum'])
                    option_2_list.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction', [None, 1,-1])
                    option_5_list.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size', step=10)
                    option_3_list.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation', [None, 'delta', 'notional'])
                    option_4_list.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy', sorted(outright_list), default=None, max_selections=3)
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor))
                
                option_1_list.append(option_1)

        with st.container():
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others ', ['Rates', 'Others'], label_visibility="collapsed")

                with col1_2:
                    option_2 = st.selectbox('Type ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                    option_2_list.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction ', [None, 1,-1], label_visibility="collapsed")
                    option_5_list.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size ', step=10, label_visibility="collapsed")
                    option_3_list.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation ', [None, 'delta', 'notional'], label_visibility="collapsed")
                    option_4_list.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                
                option_1_list.append(option_1)
        
        with st.container():
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others  ', ['Rates', 'Others'], label_visibility="collapsed")

                with col1_2:
                    option_2 = st.selectbox('Type  ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                    option_2_list.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction  ', [None, 1,-1], label_visibility="collapsed")
                    option_5_list.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size  ', step=10, label_visibility="collapsed")
                    option_3_list.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation  ', [None, 'delta', 'notional'], label_visibility="collapsed")
                    option_4_list.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy  ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy  ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                
                option_1_list.append(option_1)

        with st.container():
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others   ', ['Rates', 'Others'], label_visibility="collapsed")

                with col1_2:
                    option_2 = st.selectbox('Type   ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                    option_2_list.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction   ', [None, 1,-1], label_visibility="collapsed")
                    option_5_list.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size   ', step=10, label_visibility="collapsed")
                    option_3_list.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation   ', [None, 'delta', 'notional'], label_visibility="collapsed")
                    option_4_list.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy   ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy   ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                
                option_1_list.append(option_1)

        with st.container():
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others    ', ['Rates', 'Others'], label_visibility="collapsed")

                with col1_2:
                    option_2 = st.selectbox('Type    ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                    option_2_list.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction    ', [None, 1,-1], label_visibility="collapsed")
                    option_5_list.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size    ', step=10, label_visibility="collapsed")
                    option_3_list.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation    ', [None, 'delta', 'notional'], label_visibility="collapsed")
                    option_4_list.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy    ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy    ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                
                option_1_list.append(option_1)

        with st.container():
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others     ', ['Rates', 'Others'], label_visibility="collapsed")

                with col1_2:
                    option_2 = st.selectbox('Type     ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                    option_2_list.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction     ', [None, 1,-1], label_visibility="collapsed")
                    option_5_list.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size     ', step=10, label_visibility="collapsed")
                    option_3_list.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation     ', [None, 'delta', 'notional'], label_visibility="collapsed")
                    option_4_list.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy     ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy     ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                
                option_1_list.append(option_1)

        with st.container():
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others            ', ['Rates', 'Others'], label_visibility="collapsed")

                with col1_2:
                    option_2 = st.selectbox('Type            ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                    option_2_list.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction            ', [None, 1,-1], label_visibility="collapsed")
                    option_5_list.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size            ', step=10, label_visibility="collapsed")
                    option_3_list.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation            ', [None, 'delta', 'notional'], label_visibility="collapsed")
                    option_4_list.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy            ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy            ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                
                option_1_list.append(option_1)
        
        with st.container():
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others             ', ['Rates', 'Others'], label_visibility="collapsed")

                with col1_2:
                    option_2 = st.selectbox('Type             ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                    option_2_list.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction             ', [None, 1,-1], label_visibility="collapsed")
                    option_5_list.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size             ', step=10, label_visibility="collapsed")
                    option_3_list.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation             ', [None, 'delta', 'notional'], label_visibility="collapsed")
                    option_4_list.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy             ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy             ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                
                option_1_list.append(option_1)

        with st.container():
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others              ', ['Rates', 'Others'], label_visibility="collapsed")

                with col1_2:
                    option_2 = st.selectbox('Type              ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                    option_2_list.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction              ', [None, 1,-1], label_visibility="collapsed")
                    option_5_list.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size              ', step=10, label_visibility="collapsed")
                    option_3_list.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation              ', [None, 'delta', 'notional'], label_visibility="collapsed")
                    option_4_list.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy              ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy              ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                
                option_1_list.append(option_1)

        with st.container():
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others               ', ['Rates', 'Others'], label_visibility="collapsed")

                with col1_2:
                    option_2 = st.selectbox('Type               ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                    option_2_list.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction               ', [None, 1,-1], label_visibility="collapsed")
                    option_5_list.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size               ', step=10, label_visibility="collapsed")
                    option_3_list.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation               ', [None, 'delta', 'notional'], label_visibility="collapsed")
                    option_4_list.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy               ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy               ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                
                option_1_list.append(option_1)
        
        st.divider()
        with st.container():
            cons_type_list = []
            weight_list = []
            direction_list = []
            strat_name_list = []
            col1_, col2_, col3_ = st.columns(3)
            with st.container():
                with col1_:
                    col1_1, col1_2 = st.columns(2)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others                   ', ['Rates', 'Others'])
                        
                    with col1_2:
                        constraint_type = st.selectbox('Constraint Type', ['eq', 'ineq'])
                        cons_type_list.append(constraint_type)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        weight = st.number_input('Weight')
                        weight_list.append(weight)
                    with col2_2:
                        direction = st.selectbox('Inequality Direction', [1,-1])
                        direction_list.append(direction)

                with col3_:
                    if 'Rates' in rates_bool:
                        strat_name = st.multiselect('Constratined Strategy', sorted(outright_list), default=None, max_selections=3)
                        if len(strat_name)>0:
                            strat_name = get_strategy_name(strat_name, mapdp)
                    else:
                        strat_name = st.selectbox('Constratined Strategy', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor))
                    strat_name_list.append(strat_name)
            
            with st.container():
                with col1_:
                    col1_1, col1_2 = st.columns(2)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others                    ', ['Rates', 'Others'], label_visibility='collapsed')
                        
                    with col1_2:
                        constraint_type = st.selectbox('Constraint Type ', ['eq', 'ineq'], label_visibility='collapsed')
                        cons_type_list.append(constraint_type)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        weight = st.number_input('Weight ', label_visibility='collapsed')
                        weight_list.append(weight)
                    with col2_2:
                        direction = st.selectbox('Inequality Direction ', [1,-1], label_visibility='collapsed')
                        direction_list.append(direction)

                with col3_:
                    if 'Rates' in rates_bool:
                        strat_name = st.multiselect('Constratined Strategy ', sorted(outright_list), default=None, max_selections=3, label_visibility='collapsed')
                        if len(strat_name)>0:
                            strat_name = get_strategy_name(strat_name, mapdp)
                    else:
                        strat_name = st.selectbox('Constratined Strategy ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility='collapsed')
                    strat_name_list.append(strat_name)
            
            with st.container():
                with col1_:
                    col1_1, col1_2 = st.columns(2)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others                     ', ['Rates', 'Others'], label_visibility='collapsed')
                        
                    with col1_2:
                        constraint_type = st.selectbox('Constraint Type  ', ['eq', 'ineq'], label_visibility='collapsed')
                        cons_type_list.append(constraint_type)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        weight = st.number_input('Weight  ', label_visibility='collapsed')
                        weight_list.append(weight)
                    with col2_2:
                        direction = st.selectbox('Inequality Direction  ', [1,-1], label_visibility='collapsed')
                        direction_list.append(direction)

                with col3_:
                    if 'Rates' in rates_bool:
                        strat_name = st.multiselect('Constratined Strategy  ', sorted(outright_list), default=None, max_selections=3, label_visibility='collapsed')
                        if len(strat_name)>0:
                            strat_name = get_strategy_name(strat_name, mapdp)
                    else:
                        strat_name = st.selectbox('Constratined Strategy  ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility='collapsed')
                    strat_name_list.append(strat_name)

            with st.container():
                with col1_:
                    col1_1, col1_2 = st.columns(2)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others                      ', ['Rates', 'Others'], label_visibility='collapsed')
                        
                    with col1_2:
                        constraint_type = st.selectbox('Constraint Type   ', ['eq', 'ineq'], label_visibility='collapsed')
                        cons_type_list.append(constraint_type)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        weight = st.number_input('Weight   ', label_visibility='collapsed')
                        weight_list.append(weight)
                    with col2_2:
                        direction = st.selectbox('Inequality Direction   ', [1,-1], label_visibility='collapsed')
                        direction_list.append(direction)

                with col3_:
                    if 'Rates' in rates_bool:
                        strat_name = st.multiselect('Constratined Strategy   ', sorted(outright_list), default=None, max_selections=3, label_visibility='collapsed')
                        if len(strat_name)>0:
                            strat_name = get_strategy_name(strat_name, mapdp)
                    else:
                        strat_name = st.selectbox('Constratined Strategy   ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility='collapsed')
                    strat_name_list.append(strat_name)

            with st.container():
                with col1_:
                    col1_1, col1_2 = st.columns(2)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others                       ', ['Rates', 'Others'], label_visibility='collapsed')
                        
                    with col1_2:
                        constraint_type = st.selectbox('Constraint Type    ', ['eq', 'ineq'], label_visibility='collapsed')
                        cons_type_list.append(constraint_type)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        weight = st.number_input('Weight    ', label_visibility='collapsed')
                        weight_list.append(weight)
                    with col2_2:
                        direction = st.selectbox('Inequality Direction    ', [1,-1], label_visibility='collapsed')
                        direction_list.append(direction)

                with col3_:
                    if 'Rates' in rates_bool:
                        strat_name = st.multiselect('Constratined Strategy    ', sorted(outright_list), default=None, max_selections=3, label_visibility='collapsed')
                        if len(strat_name)>0:
                            strat_name = get_strategy_name(strat_name, mapdp)
                    else:
                        strat_name = st.selectbox('Constratined Strategy    ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility='collapsed')
                    strat_name_list.append(strat_name)
            
            custom_constraints_sort = [[s, c, w, d] for s, c, w, d in zip(strat_name_list, cons_type_list, weight_list, direction_list) if len(s)>0]
            custom_constraints_element = [option_1_list] + [custom_constraints_sort]
            
        if len(strat_name_list)>0:
            st.session_state.custom_constraints = custom_constraints_element
        else:
            st.session_state.custom_constraints = []
        
        st.divider()
        with st.expander('Add Strategy'):
            col1_, col2_, col3_ = st.columns(3)
            with st.container():
                with col1_:
                    col1_1, col1_2, col1_3 = st.columns(3)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others      ', ['Rates', 'Others'], label_visibility="collapsed")

                    with col1_2:
                        option_2 = st.selectbox('Type      ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                        option_2_list.append(option_2)
                    
                    with col1_3:
                        option_5 = st.selectbox('Trade Direction      ', [None, 1,-1], label_visibility="collapsed")
                        option_5_list.append(option_5)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        option_3 = st.number_input('Position Size      ', step=10, label_visibility="collapsed")
                        option_3_list.append(option_3)
                    with col2_2:
                        option_4 = st.selectbox('Notation      ', [None, 'delta', 'notional'], label_visibility="collapsed")
                        option_4_list.append(option_4)

                with col3_:
                    if 'Rates' in rates_bool:
                        option_1 = st.multiselect('Strategy      ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                        if len(option_1)>0:
                            option_1 = get_strategy_name(option_1, mapdp)
                    else:
                        option_1 = st.selectbox('Strategy      ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                    
                    option_1_list.append(option_1)
            
            with st.container():
                with col1_:
                    col1_1, col1_2, col1_3 = st.columns(3)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others       ', ['Rates', 'Others'], label_visibility="collapsed")

                    with col1_2:
                        option_2 = st.selectbox('Type       ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                        option_2_list.append(option_2)
                    
                    with col1_3:
                        option_5 = st.selectbox('Trade Direction       ', [None, 1,-1], label_visibility="collapsed")
                        option_5_list.append(option_5)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        option_3 = st.number_input('Position Size       ', step=10, label_visibility="collapsed")
                        option_3_list.append(option_3)
                    with col2_2:
                        option_4 = st.selectbox('Notation       ', [None, 'delta', 'notional'], label_visibility="collapsed")
                        option_4_list.append(option_4)

                with col3_:
                    if 'Rates' in rates_bool:
                        option_1 = st.multiselect('Strategy       ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                        if len(option_1)>0:
                            option_1 = get_strategy_name(option_1, mapdp)
                    else:
                        option_1 = st.selectbox('Strategy       ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                    
                    option_1_list.append(option_1)
            
            with st.container():
                with col1_:
                    col1_1, col1_2, col1_3 = st.columns(3)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others        ', ['Rates', 'Others'], label_visibility="collapsed")

                    with col1_2:
                        option_2 = st.selectbox('Type        ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                        option_2_list.append(option_2)
                    
                    with col1_3:
                        option_5 = st.selectbox('Trade Direction        ', [None, 1,-1], label_visibility="collapsed")
                        option_5_list.append(option_5)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        option_3 = st.number_input('Position Size        ', step=10, label_visibility="collapsed")
                        option_3_list.append(option_3)
                    with col2_2:
                        option_4 = st.selectbox('Notation        ', [None, 'delta', 'notional'], label_visibility="collapsed")
                        option_4_list.append(option_4)

                with col3_:
                    if 'Rates' in rates_bool:
                        option_1 = st.multiselect('Strategy        ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                        if len(option_1)>0:
                            option_1 = get_strategy_name(option_1, mapdp)
                    else:
                        option_1 = st.selectbox('Strategy        ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                    
                    option_1_list.append(option_1)

            with st.container():
                with col1_:
                    col1_1, col1_2, col1_3 = st.columns(3)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others         ', ['Rates', 'Others'], label_visibility="collapsed")

                    with col1_2:
                        option_2 = st.selectbox('Type         ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                        option_2_list.append(option_2)
                    
                    with col1_3:
                        option_5 = st.selectbox('Trade Direction         ', [None, 1,-1], label_visibility="collapsed")
                        option_5_list.append(option_5)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        option_3 = st.number_input('Position Size         ', step=10, label_visibility="collapsed")
                        option_3_list.append(option_3)
                    with col2_2:
                        option_4 = st.selectbox('Notation         ', [None, 'delta', 'notional'], label_visibility="collapsed")
                        option_4_list.append(option_4)

                with col3_:
                    if 'Rates' in rates_bool:
                        option_1 = st.multiselect('Strategy         ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                        if len(option_1)>0:
                            option_1 = get_strategy_name(option_1, mapdp)
                    else:
                        option_1 = st.selectbox('Strategy         ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                    
                    option_1_list.append(option_1)

            with st.container():
                with col1_:
                    col1_1, col1_2, col1_3 = st.columns(3)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others          ', ['Rates', 'Others'], label_visibility="collapsed")

                    with col1_2:
                        option_2 = st.selectbox('Type          ', [None, 'value', 'carry', 'momentum'], label_visibility="collapsed")
                        option_2_list.append(option_2)
                    
                    with col1_3:
                        option_5 = st.selectbox('Trade Direction          ', [None, 1,-1], label_visibility="collapsed")
                        option_5_list.append(option_5)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        option_3 = st.number_input('Position Size          ', step=10, label_visibility="collapsed")
                        option_3_list.append(option_3)
                    with col2_2:
                        option_4 = st.selectbox('Notation          ', [None, 'delta', 'notional'], label_visibility="collapsed")
                        option_4_list.append(option_4)

                with col3_:
                    if 'Rates' in rates_bool:
                        option_1 = st.multiselect('Strategy          ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                        if len(option_1)>0:
                            option_1 = get_strategy_name(option_1, mapdp)
                    else:
                        option_1 = st.selectbox('Strategy          ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                    
                    option_1_list.append(option_1)
        
        portfolio = [[strat, strat_type, notional, notation, direction] for strat, strat_type, notional, notation, direction in zip(option_1_list, option_2_list, option_3_list, option_4_list, option_5_list) if strat is not None and strat_type is not None and notional != 0 and notation is not None and direction is not None]
        if len(portfolio)>0:
            st.session_state.opt_port = portfolio
       
    with tab2:
        col1, col2, col3 = st.columns(3)
        with col1:
            col1_1, col1_2 = st.columns(2)
            with col1_1:
                opt_type = st.selectbox('Optimization Method', ['Risk Parity', 'Mean Variance', 'Minimum Variance', 'Equal Risk Contribution'])
            with col1_2:
                lookback = st.number_input('Lookback Period', value=250, step=10)
           
        with col2:
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                start_dt = datetime.strftime(st.date_input('Start Date', date(2022,1,1)), '%Y-%m-%d')
                
            with col2_2:
                end_dt = datetime.strftime(st.date_input('End Date'), '%Y-%m-%d')
        
        with col3:
            st.write('')
            st.write('')
            start_button = st.button('Optimize')
        st.divider()

        if start_button:

            if opt_type == 'Risk Parity':
                expected_return, portfolio_ret_df, historical_weight = get_port_opt_ret(st.session_state.opt_port, 'RP', st.session_state.custom_constraints, lookback, start_dt, end_dt)
                
            elif opt_type == 'Mean Variance':
                expected_return, portfolio_ret_df, historical_weight = get_port_opt_ret(st.session_state.opt_port, 'MS', st.session_state.custom_constraints, lookback, start_dt, end_dt)

            elif opt_type == 'Minimum Variance':
                expected_return, portfolio_ret_df, historical_weight = get_port_opt_ret(st.session_state.opt_port, 'MV', st.session_state.custom_constraints, lookback, start_dt, end_dt)

            elif opt_type == 'Equal Risk Contribution':
                expected_return, portfolio_ret_df, historical_weight = get_port_opt_ret(st.session_state.opt_port, 'ERC', st.session_state.custom_constraints, lookback, start_dt, end_dt)
            
            #현재 포트폴리오 현황
            current_notional, current_weight = pa.portfolio_weight(st.session_state.opt_port)
            #Delta Weight 표시 위한 작업
            current_weight_to_df = [[str(c[0])+"_"+c[1], c[2]] for c in current_weight]
            current_weight_series = pd.DataFrame(current_weight_to_df, columns=['Strategy', 'Weight']).set_index('Strategy')['Weight']
            current_delta = pa.wgt_to_delta(st.session_state.opt_port, current_weight_series, start_dt, end_dt, portfolio_size=sum([abs(n[2]) for n in current_notional]))
            current_delta_df = pd.DataFrame([[str(cd[0]), cd[2]] for cd in current_delta], columns=['Strategy', 'Delta']).set_index('Strategy')
            current_delta_df['Delta Weight'] = np.round(current_delta_df['Delta']/current_delta_df['Delta'].sum(),2)
            #신규 포트 및 성격
            portfolio_correlation = pa.correlation(st.session_state.opt_port , lookback, date.today().isoformat())
            port_delta = pa.wgt_to_delta(st.session_state.opt_port, historical_weight.iloc[-1,:], start_dt, end_dt, portfolio_size=sum([abs(s[2]) for s in current_notional]))
            strategy_df_cum, selected_strategy_df_ret = pa.strategy_direction_applied(st.session_state.opt_port)
            selected_strategy_df_ret = selected_strategy_df_ret[selected_strategy_df_ret.index>=start_dt]
            #신규 포트 표시 위한 작업
            opt_delta_df = pd.DataFrame([[str(pd[0]), pd[2]] for pd in port_delta], columns=['Strategy', 'Delta']).set_index('Strategy')
            opt_delta_df['Delta Weight'] = np.round(opt_delta_df['Delta']/opt_delta_df['Delta'].sum(),2)
            opt_notional_weight = historical_weight.iloc[-1,:]
            opt_notional_weight.index = [s.replace('_momentum', '').replace('_carry', '').replace('_value', '') for s in opt_notional_weight.index]
            opt_notional = historical_weight.iloc[-1,:] * sum([abs(n[2]) for n in current_notional])
            opt_notional.index = [s.replace('_momentum', '').replace('_carry', '').replace('_value', '') for s in opt_notional.index]
            opt_delta_df['Notional'] = opt_notional.astype(int)
            opt_delta_df['Weight'] = np.round(opt_notional_weight,2)
            opt_port = opt_delta_df[['Notional', 'Weight', 'Delta', 'Delta Weight']].copy()

            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Current Portfolio**")
                    current_port = pd.DataFrame([[str(x[0]),x[1], x[2], np.round(y[2],2)] for x, y in zip(current_notional, current_weight)], columns=['Strategy', 'Type', 'Notional', 'Weight']).set_index('Strategy')
                    current_port = pd.concat([current_port, current_delta_df], axis=1)
                    current_port['Delta'] = current_port['Delta']*np.sign(current_port['Notional'])*-1
                    st.dataframe(current_port, use_container_width=True)
                    vol_c = (selected_strategy_df_ret *[w[2] for w in current_weight]).sum(axis=1).std()*np.sqrt(252)*100
                    current_port_er = [e[2] for e in expected_return]
                    er_c = sum([e*w for e,w in zip(current_port_er, [w[2] for w in current_weight])])
                    sharpe_c = er_c/vol_c
                    er_sharpe_c = [[str(x), np.round(z,2), np.round(y*np.sqrt(252)*100,2), np.round(z/(y*np.sqrt(252)*100),2)] for x,y,z in zip(list(selected_strategy_df_ret.std().index), list(selected_strategy_df_ret.std().values), [x[2] for x in expected_return])]
                    er_sharpe_c.append(['Portfolio', np.round(er_c,2), np.round(vol_c, 2), np.round(sharpe_c, 2)])
                    current_df = pd.DataFrame(er_sharpe_c, columns = ['Strategy', 'Expected Return', 'Volatility', 'IR']).set_index('Strategy')
                    st.dataframe(current_df, use_container_width=True)
                
                with col2:
                    st.markdown("**Optimized Portfolio**")
                    #opt_port = pd.DataFrame([[y[0], y[1], y[2], np.round(x[1],4)] for x,y in zip([[str(x), y] for x,y in zip(historical_weight.iloc[-1,:].index, historical_weight.iloc[-1,:].values)], [[str(x[0]), x[1], x[2]] for x in port_delta])], columns=['Strategy', 'Type', 'Delta', 'Weight']).set_index('Strategy')
                    vol_l = (selected_strategy_df_ret *historical_weight.iloc[-1,:].values).sum(axis=1).std()*np.sqrt(252)*100
                    if opt_type in ['Risk Parity', 'Equal Risk Contribution']:
                        leverage = vol_c/vol_l
                    else:
                        leverage = 1
                    opt_port['Notional'] = (leverage*opt_port['Notional']*np.sign(current_port['Notional'])).astype(int)
                    opt_port['Weight'] = leverage*opt_port['Weight']
                    opt_port['Delta'] = np.round(leverage*opt_port['Delta']*np.sign(opt_port['Notional'])*-1,2)
                    opt_port['Delta Weight'] = leverage*opt_port['Delta Weight']
                    opt_port['Weight Change'] = np.round(opt_port['Weight'],2) - np.round(current_port['Weight'],2)
                    opt_port['Delta Change'] = np.round(opt_port['Delta'],2) - np.round(current_port['Delta'],2)
                    opt_port = opt_port.style.apply(mean_highlighter, subset='Weight Change').apply(mean_highlighter_delta, subset='Delta Change').format(precision=2, thousands=",")
                    st.dataframe(opt_port, use_container_width=True)
                    vol = (selected_strategy_df_ret * leverage * historical_weight.iloc[-1,:].values).sum(axis=1).std()*np.sqrt(252)*100
                    er = sum([e*w for e,w in zip(current_port_er, historical_weight.iloc[-1,:].values)])
                    sharpe = er/vol
                    er_sharpe = [[str(x), np.round(z,2), np.round(y*np.sqrt(252)*100,2), np.round(z/(y*np.sqrt(252)*100),2)] for x,y,z in zip(list(selected_strategy_df_ret.std().index), list(selected_strategy_df_ret.std().values), [x[2] for x in expected_return])]
                    er_sharpe.append(['Portfolio', np.round(er,2), np.round(vol, 2), np.round(sharpe, 2)])
                    opt_df = pd.DataFrame(er_sharpe, columns = ['Strategy', 'Expected Return', 'Volatility', 'IR']).set_index('Strategy')
                    st.dataframe(opt_df, use_container_width=True)
                    if opt_type in ['Risk Parity', 'Equal Risk Contribution']:
                        st.markdown("*Volatility targeted to original port volatility. Leverage is {}".format(np.round(leverage,3)))

            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Correlation**")
                    st.markdown("")
                    st.markdown("")
                    port_corr = portfolio_correlation.copy()
                    port_corr.index = [str(x) for x in port_corr.index]
                    st.dataframe(port_corr.style.background_gradient(cmap='RdBu'), use_container_width=True)

                with col2:
                    st.markdown("**Portfolio Performance**")
                    port_chart = (1+portfolio_ret_df.rename(columns={'Strategy':'Portfolio'})).cumprod().reset_index()
                    fig = px.line(port_chart, x='Date', y=port_chart.columns,height=450)    
                    fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig, use_container_width=True)

    with tab3:
        with st.container():
            col1, col2, col3 = st.columns(3)
            option_1_list_new = []
            option_2_list_new = []
            option_3_list_new = []
            option_4_list_new = []
            option_5_list_new = []
            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    rates_bool = st.selectbox('Rates or Others                ', ['Rates', 'Others'])

                with col1_2:
                    option_2 = st.selectbox('Type                ', [None, 'value', 'carry', 'momentum'])
                    option_2_list_new.append(option_2)
                
                with col1_3:
                    option_5 = st.selectbox('Trade Direction                ', [None, 1,-1])
                    option_5_list_new.append(option_5)
                    
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    option_3 = st.number_input('Position Size                ', step=10)
                    option_3_list_new.append(option_3)
                with col2_2:
                    option_4 = st.selectbox('Notation                ', [None, 'delta', 'notional'])
                    option_4_list_new.append(option_4)

            with col3:
                if 'Rates' in rates_bool:
                    option_1 = st.multiselect('Strategy                ', sorted(outright_list), default=None, max_selections=3)
                    if len(option_1)>0:
                        option_1 = get_strategy_name(option_1, mapdp)
                else:
                    option_1 = st.selectbox('Strategy                ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor))
                
                option_1_list_new.append(option_1)
        
        with st.expander('Add Strategy'):
            col1_, col2_, col3_ = st.columns(3)
            with st.container():
                with col1_:
                    col1_1, col1_2, col1_3 = st.columns(3)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others                 ', ['Rates', 'Others'], label_visibility='collapsed')

                    with col1_2:
                        option_2 = st.selectbox('Type                 ', [None, 'value', 'carry', 'momentum'], label_visibility='collapsed')
                        option_2_list_new.append(option_2)
                    
                    with col1_3:
                        option_5 = st.selectbox('Trade Direction                 ', [None, 1,-1], label_visibility='collapsed')
                        option_5_list_new.append(option_5)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        option_3 = st.number_input('Position Size                 ', step=10, label_visibility='collapsed')
                        option_3_list_new.append(option_3)
                    with col2_2:
                        option_4 = st.selectbox('Notation                 ', [None, 'delta', 'notional'], label_visibility='collapsed')
                        option_4_list_new.append(option_4)

                with col3_:
                    if 'Rates' in rates_bool:
                        option_1 = st.multiselect('Strategy                 ', sorted(outright_list), default=None, max_selections=3, label_visibility='collapsed')
                        if len(option_1)>0:
                            option_1 = get_strategy_name(option_1, mapdp)
                    else:
                        option_1 = st.selectbox('Strategy                 ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility='collapsed')
                    
                    option_1_list_new.append(option_1)
            
            with st.container():
                with col1_:
                    col1_1, col1_2, col1_3 = st.columns(3)
                    with col1_1:
                        rates_bool = st.selectbox('Rates or Others                  ', ['Rates', 'Others'], label_visibility='collapsed')

                    with col1_2:
                        option_2 = st.selectbox('Type                  ', [None, 'value', 'carry', 'momentum'], label_visibility='collapsed')
                        option_2_list_new.append(option_2)
                    
                    with col1_3:
                        option_5 = st.selectbox('Trade Direction                  ', [None, 1,-1], label_visibility='collapsed')
                        option_5_list_new.append(option_5)
                        
                with col2_:
                    col2_1, col2_2 = st.columns(2)
                    with col2_1:
                        option_3 = st.number_input('Position Size                  ', step=10, label_visibility='collapsed')
                        option_3_list_new.append(option_3)
                    with col2_2:
                        option_4 = st.selectbox('Notation                  ', [None, 'delta', 'notional'], label_visibility='collapsed')
                        option_4_list_new.append(option_4)

                with col3_:
                    if 'Rates' in rates_bool:
                        option_1 = st.multiselect('Strategy                  ', sorted(outright_list), default=None, max_selections=3, label_visibility='collapsed')
                        if len(option_1)>0:
                            option_1 = get_strategy_name(option_1, mapdp)
                    else:
                        option_1 = st.selectbox('Strategy                  ', [None]+sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility='collapsed')
                    
                    option_1_list_new.append(option_1)

        portfolio_new = [[strat, strat_type, notional, notation, direction] for strat, strat_type, notional, notation, direction in zip(option_1_list_new, option_2_list_new, option_3_list_new, option_4_list_new, option_5_list_new) if strat is not None and strat_type is not None and notional != 0 and notation is not None and direction is not None]
        if 'opt_port' in st.session_state:
            portfolio_assessment = st.session_state.opt_port + portfolio_new

        st.divider()
        with st.container(): 
            col1, col2, col3 = st.columns(3)
            with col1:
                col1_1, col1_2 = st.columns(2)
                with col1_1:
                    opt_type_n = st.selectbox('Optimization Method ', ['Risk Parity', 'Mean Variance', 'Minimum Variance', 'Equal Risk Contribution'])
                with col1_2:
                    lookback_n = st.number_input('Lookback Period ', value=250, step=10)
            
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    start_dt_n = datetime.strftime(st.date_input('Start Date ', date(2022,1,1)), '%Y-%m-%d')
                    
                with col2_2:
                    end_dt_n = datetime.strftime(st.date_input('End Date '), '%Y-%m-%d')
            
            with col3:
                st.write('')
                st.write('')
                start_button_n = st.button('Optimize ')
        
        st.divider()
        if start_button_n:
            if opt_type_n == 'Risk Parity':
                expected_return_n, portfolio_ret_df_n, historical_weight_n = get_port_opt_ret(portfolio_assessment, 'RP', st.session_state.custom_constraints, lookback_n, start_dt_n, end_dt_n)
                
            elif opt_type_n == 'Mean Variance':
                expected_return_n, portfolio_ret_df_n, historical_weight_n = get_port_opt_ret(portfolio_assessment, 'MS', st.session_state.custom_constraints, lookback_n, start_dt_n, end_dt_n)

            elif opt_type_n == 'Minimum Variance':
                expected_return_n, portfolio_ret_df_n, historical_weight_n = get_port_opt_ret(portfolio_assessment, 'MV', st.session_state.custom_constraints, lookback_n, start_dt_n, end_dt_n)
            
            elif opt_type == 'Equal Risk Contribution':
                expected_return_n, portfolio_ret_df_n, historical_weight_n = get_port_opt_ret(portfolio_assessment, 'ERC', st.session_state.custom_constraints, lookback_n, start_dt_n, end_dt_n)
            
            #current_notional_n, current_weight_n = pa.portfolio_weight(portfolio_assessment)
            #portfolio_correlation_n = pa.correlation(portfolio_assessment , lookback_n, date.today().isoformat())
            #port_delta_n = pa.wgt_to_delta(portfolio_assessment, historical_weight_n.iloc[-1,:], start_dt_n, end_dt_n, portfolio_size=sum([abs(s[2]) for s in current_notional_n]))
            #strategy_df_cum_n, selected_strategy_df_ret_n = pa.strategy_direction_applied(portfolio_assessment)
            #selected_strategy_df_ret_n = selected_strategy_df_ret_n[selected_strategy_df_ret_n.index>=start_dt_n]
 
            #현재 포트폴리오 현황
            current_notional_n, current_weight_n = pa.portfolio_weight(portfolio_assessment)
            #Delta Weight 표시 위한 작업
            current_weight_to_df_n = [[str(c[0])+"_"+c[1], c[2]] for c in current_weight_n]
            current_weight_series_n = pd.DataFrame(current_weight_to_df_n, columns=['Strategy', 'Weight']).set_index('Strategy')['Weight']
            current_delta_n = pa.wgt_to_delta(portfolio_assessment, current_weight_series_n, start_dt_n, end_dt_n, portfolio_size=sum([abs(n[2]) for n in current_notional_n]))
            current_delta_df_n = pd.DataFrame([[str(cd[0]), cd[2]] for cd in current_delta_n], columns=['Strategy', 'Delta']).set_index('Strategy')
            current_delta_df_n['Delta Weight'] = np.round(current_delta_df_n['Delta']/current_delta_df_n['Delta'].sum(),2)
            #신규 포트 및 성격
            portfolio_correlation_n = pa.correlation(portfolio_assessment , lookback_n, date.today().isoformat())
            port_delta_n = pa.wgt_to_delta(portfolio_assessment, historical_weight_n.iloc[-1,:], start_dt_n, end_dt_n, portfolio_size=sum([abs(s[2]) for s in current_notional_n]))
            strategy_df_cum_n, selected_strategy_df_ret_n = pa.strategy_direction_applied(portfolio_assessment)
            selected_strategy_df_ret_n = selected_strategy_df_ret_n[selected_strategy_df_ret_n.index>=start_dt_n]
            #신규 포트 표시 위한 작업
            opt_delta_df_n = pd.DataFrame([[str(pd[0]), pd[2]] for pd in port_delta_n], columns=['Strategy', 'Delta']).set_index('Strategy')
            opt_delta_df_n['Delta Weight'] = np.round(opt_delta_df_n['Delta']/opt_delta_df_n['Delta'].sum(),2)
            opt_notional_weight_n = historical_weight_n.iloc[-1,:]
            opt_notional_weight_n.index = [s.replace('_momentum', '').replace('_carry', '').replace('_value', '') for s in opt_notional_weight_n.index]
            opt_notional_n = historical_weight_n.iloc[-1,:] * sum([abs(n[2]) for n in current_notional_n])
            opt_notional_n.index = [s.replace('_momentum', '').replace('_carry', '').replace('_value', '') for s in opt_notional_n.index]
            opt_delta_df_n['Notional'] = opt_notional_n.astype(int)
            opt_delta_df_n['Weight'] = np.round(opt_notional_weight_n,2)
            opt_port_n = opt_delta_df_n[['Notional', 'Weight', 'Delta', 'Delta Weight']].copy()

            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Current Portfolio**")
                    #current_port_n = pd.DataFrame([[str(x[0]),x[1], x[2], np.round(y[2],4)] for x, y in zip(current_notional_n, current_weight_n)], columns=['Strategy', 'Type', 'Notional', 'Weight']).set_index('Strategy')
                    current_port_n = pd.DataFrame([[str(x[0]),x[1], x[2], np.round(y[2],2)] for x, y in zip(current_notional_n, current_weight_n)], columns=['Strategy', 'Type', 'Notional', 'Weight']).set_index('Strategy')
                    current_port_n = pd.concat([current_port_n, current_delta_df_n], axis=1)
                    current_port_n['Delta'] = current_port_n['Delta']*np.sign(current_port_n['Notional'])*-1
                    st.dataframe(current_port_n, use_container_width=True)
                    vol_c_n = (selected_strategy_df_ret_n *[w[2] for w in current_weight_n]).sum(axis=1).std()*np.sqrt(252)*100
                    current_port_er_n = [e[2] for e in expected_return_n]
                    er_c_n = sum([e*w for e,w in zip(current_port_er_n, [w[2] for w in current_weight_n])])
                    sharpe_c_n = er_c_n/vol_c_n
                    er_sharpe_c_n = [[str(x), np.round(z,4), np.round(y*np.sqrt(252)*100,4), np.round(z/(y*np.sqrt(252)*100),4)] for x,y,z in zip(list(selected_strategy_df_ret_n.std().index), list(selected_strategy_df_ret_n.std().values), [x[2] for x in expected_return_n])]
                    er_sharpe_c_n.append(['Portfolio', np.round(er_c_n,4), np.round(vol_c_n, 4), np.round(sharpe_c_n, 4)])
                    st.dataframe(pd.DataFrame(er_sharpe_c_n, columns = ['Strategy', 'Expected Return', 'Volatility', 'IR']).set_index('Strategy'), use_container_width=True)
                
                with col2:
                    st.markdown("**Optimized Portfolio**")
                    #opt_port_n = pd.DataFrame([[y[0], y[1], y[2], np.round(x[1],4)] for x,y in zip([[str(x), y] for x,y in zip(historical_weight_n.iloc[-1,:].index, historical_weight_n.iloc[-1,:].values)], [[str(x[0]), x[1], x[2]] for x in port_delta_n])], columns=['Strategy', 'Type', 'Delta', 'Weight']).set_index('Strategy')
                    #opt_port_n['Weight Change'] = np.round(opt_port_n['Weight'],4) - np.round(current_port_n['Weight'],4)
                    #opt_port_n = opt_port_n.style.apply(mean_highlighter, subset='Weight Change')
                    vol_l_n = (selected_strategy_df_ret_n *historical_weight_n.iloc[-1,:].values).sum(axis=1).std()*np.sqrt(252)*100
                    if opt_type_n in ['Risk Parity', 'Equal Risk Contribution']:
                        leverage_n = vol_c_n/vol_l_n
                    else:
                        leverage_n = 1
                    opt_port_n['Notional'] = (leverage_n*opt_port_n['Notional']*np.sign(current_port_n['Notional'])).astype(int)
                    opt_port_n['Weight'] = leverage_n*opt_port_n['Weight']
                    opt_port_n['Delta'] = np.round(leverage_n*opt_port_n['Delta']*np.sign(opt_port_n['Notional'])*-1,2)
                    opt_port_n['Delta Weight'] = leverage_n*opt_port_n['Delta Weight']
                    opt_port_n['Weight Change'] = np.round(opt_port_n['Weight'],2) - np.round(current_port_n['Weight'],2)
                    opt_port_n['Delta Change'] = np.round(opt_port_n['Delta'],2) - np.round(current_port_n['Delta'],2)
                    opt_port_n = opt_port_n.style.apply(mean_highlighter, subset='Weight Change').apply(mean_highlighter_delta, subset='Delta Change').format(precision=2, thousands=",")
                    st.dataframe(opt_port_n, use_container_width=True)
                    vol_n = (selected_strategy_df_ret_n * leverage_n * historical_weight_n.iloc[-1,:].values).sum(axis=1).std()*np.sqrt(252)*100
                    er_n = sum([e*w for e,w in zip(current_port_er_n, historical_weight_n.iloc[-1,:].values)])
                    sharpe_n = er_n/vol_n
                    er_sharpe_n = [[str(x), np.round(z,4), np.round(y*np.sqrt(252)*100,4), np.round(z/(y*np.sqrt(252)*100),4)] for x,y,z in zip(list(selected_strategy_df_ret_n.std().index), list(selected_strategy_df_ret_n.std().values), [x[2] for x in expected_return_n])]
                    er_sharpe_n.append(['Portfolio', np.round(er_n,4), np.round(vol_n, 4), np.round(sharpe_n, 4)])
                    st.dataframe(pd.DataFrame(er_sharpe_n, columns = ['Strategy', 'Expected Return', 'Volatility', 'IR']).set_index('Strategy'), use_container_width=True)
                    if opt_type_n in ['Risk Parity', 'Equal Risk Contribution']:
                        st.markdown("Volatility targeted to original port volatility. Leverage is {}".format(np.round(leverage_n,3)))

            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Correlation**")
                    st.markdown("")
                    st.markdown("")
                    port_corr_n = portfolio_correlation_n.copy()
                    port_corr_n.index = [str(x) for x in port_corr_n.index]
                    st.dataframe(port_corr_n.style.background_gradient(cmap='RdBu'), use_container_width=True)

                with col2:
                    st.markdown("**Portfolio Performance**")
                    port_chart_n = (1+portfolio_ret_df_n.rename(columns={'Strategy':'Portfolio'})).cumprod().reset_index()
                    fig_n = px.line(port_chart_n, x='Date', y=port_chart_n.columns,height=450)    
                    fig_n.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig_n, use_container_width=True)



        
