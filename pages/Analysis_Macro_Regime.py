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
from Strategy_MA_Optimal_Portfolio import RegimeDetection, RiskManagement

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
def pull_regime_functions():
    rd =  RegimeDetection(mapdp)
    rm = RiskManagement(rd)
    return rd, rm

def pull_strategy_data_series(rd):
    strategy_list_futures = list(rd.mapdp.fut_strategy_df.columns)
    strategy_list_rates = list(rd.mapdp.rates_strat_tr_cumprod_df.columns)
    strategy_list_rp = list(rd.mapdp.rp_strategy_df.columns)
    strategy_list_macrofactor = list(rd.mapdp.macro_factor_cum.columns)
    strategy_macrofactor = rd.mapdp.macro_factor_cum
    strategy_set = rd.mapdp.strategy_set_df.copy()
    strategy_set.index = pd.DatetimeIndex(strategy_set.index)
    strategy_set.index.name = None
    strategy_data = pd.concat([strategy_macrofactor, strategy_set], axis=1, sort=True).fillna(method='ffill')
    return strategy_list_futures, strategy_list_rates, strategy_list_rp, strategy_list_macrofactor, strategy_set, strategy_data

def get_strategy_name(options):
    strategy_list_rates = list(rd.mapdp.rates_strat_tr_cumprod_df.columns)
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

#데이터 불러오기
with st.spinner("Querying Data, Will take about 2 minutes, Please Wait..."):
    if 'mapdp' not in st.session_state:
        mapdp = pull_strategy_data()
        st.session_state.mapdp = mapdp
    else:
        mapdp = st.session_state.mapdp
    rd, rm = pull_regime_functions()

#전략리스트 및 가격데이터
ktb = ['1Y_KTB', '2Y_KTB','3Y_KTB','4Y_KTB','5Y_KTB','7Y_KTB','10Y_KTB','20Y_KTB','30Y_KTB', 'IL10Y_KTB', 'BE10Y_KTB', '3Y_FUT', '10Y_FUT']
swap = ['9M_IRS', '1Y_IRS', '18M_IRS','2Y_IRS','3Y_IRS','4Y_IRS','5Y_IRS','7Y_IRS','10Y_IRS']
foreign = ['2Y_FUT_US', '5Y_FUT_US', '10Y_FUT_US', '30Y_FUT_US','2Y_FUT_GER', '5Y_FUT_GER', '10Y_FUT_GER'] 
outright_list = ktb+swap+foreign
strategy_list_futures, strategy_list_rates, strategy_list_rp, strategy_list_macrofactor, strategy_set, strategy_data = pull_strategy_data_series(rd)

with st.container():
    tab1, tab2, tab3, tab4, tab5 = st.tabs(['Spec', 'Regime', 'Factor', 'Risk', 'Map'])
    
    with open(css_dir) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

    with tab1:
        volatility_list = []
        with st.container():
            col1_, col2_, col3_ = st.columns(3)
            
            with col1_:
                lb = st.slider("Lookback Period", 20,250,(20,250), step=10)
                lb_list = [lb[0], int((lb[0]+lb[1])/2), lb[1]]
            with col2_:
                ref_date = st.date_input('Reference Date')
                ref_date = datetime.strftime(ref_date, "%Y-%m-%d")
            with col3_:
                portfolio_bool = st.radio('Analysis Type', ['Strategy', 'Portfolio'])
                
        col1, col2, col3 = st.columns(3)
        with col1:
            rates_bool = st.selectbox('Rates or Others', ['Rates', 'Others'])
        with col2: 
            if 'Rates' in rates_bool:
                option_2 = st.multiselect('Strategy', sorted(outright_list), default=None, max_selections=3)
                if len(option_2)>0:
                    option_2 = [get_strategy_name(option_2)]
            else:
                option_2 = st.selectbox('Strategy', sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor))
                option_2 = [option_2]
        with col3: 
            option_3 = st.selectbox('Trade Direction', [1, -1])
        
        if len(option_2)>0:
            if option_3 == 1:
                volatility_list.append((strategy_data[option_2][-60:].dropna()/strategy_data[option_2][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252))
                st.write("{}'s Annual Volatility : ".format(option_2[0]) + "{:.3%}".format((strategy_data[option_2][-60:].dropna()/strategy_data[option_2][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252)))
            else:
                volatility_list.append((strategy_data[option_2][-60:].dropna().shift(1)/strategy_data[option_2][-60:].dropna()-1).std().values[0]*np.sqrt(252))
                st.write("{}'s Annual Volatility : ".format(option_2[0]) + "{:.3%}".format((strategy_data[option_2][-60:].dropna().shift(1)/strategy_data[option_2][-60:].dropna()-1).std().values[0]*np.sqrt(252)))

        with st.expander('Add Strategy'):
            with st.container():
                col1_e, col2_e, col3_e = st.columns(3)
                with col1_e:
                    rates_bool_e = st.selectbox('Rates or Others ', ['Rates', 'Others'])
                with col2_e: 
                    if 'Rates' in rates_bool_e:
                        option_2_e = st.multiselect('Strategy ', sorted(outright_list), default=None, max_selections=3)
                        if len(option_2_e)>0:   
                            option_2_e = [get_strategy_name(option_2_e)]
                    else:
                        option_2_e = st.selectbox('Strategy ', sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor))
                        option_2_e = [option_2_e]
                with col3_e: 
                    option_3_e = st.selectbox('Trade Direction ',[1, -1])
                if len(option_2_e)>0:  
                    if option_3_e == 1:
                        volatility_list.append((strategy_data[option_2_e][-60:].dropna()/strategy_data[option_2_e][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252))
                        st.write("{}'s Annual Volatility : ".format(option_2_e[0]) + "{:.3%}".format((strategy_data[option_2_e][-60:].dropna()/strategy_data[option_2_e][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252)))
                    else:
                        volatility_list.append((strategy_data[option_2_e][-60:].dropna().shift(1)/strategy_data[option_2_e][-60:].dropna()-1).std().values[0]*np.sqrt(252))
                        st.write("{}'s Annual Volatility : ".format(option_2_e[0]) + "{:.3%}".format((strategy_data[option_2_e][-60:].dropna().shift(1)/strategy_data[option_2_e][-60:].dropna()-1).std().values[0]*np.sqrt(252)))

            with st.container():
                col1_e, col2_e, col3_e = st.columns(3)
                with col1_e:
                    rates_bool_e_1 = st.selectbox('Rates or Others  ', ['Rates', 'Others'], label_visibility="collapsed")
                with col2_e: 
                    if 'Rates' in rates_bool_e_1:
                        option_2_e_1 = st.multiselect('Strategy  ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                        if len(option_2_e_1)>0:   
                            option_2_e_1 = [get_strategy_name(option_2_e_1)]
                    else:
                        option_2_e_1 = st.selectbox('Strategy  ', sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                        option_2_e_1 = [option_2_e_1]
                with col3_e: 
                    option_3_e_1 = st.selectbox('Trade Direction  ', [1, -1], label_visibility="collapsed")
                if len(option_2_e_1)>0:  
                    if option_3_e_1 == 1:
                        volatility_list.append((strategy_data[option_2_e_1][-60:].dropna()/strategy_data[option_2_e_1][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252))
                        st.write("{}'s Annual Volatility : ".format(option_2_e_1[0]) + "{:.3%}".format((strategy_data[option_2_e_1][-60:].dropna()/strategy_data[option_2_e_1][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252)))
                    else:
                        volatility_list.append((strategy_data[option_2_e_1][-60:].dropna().shift(1)/strategy_data[option_2_e_1][-60:].dropna()-1).std().values[0]*np.sqrt(252))
                        st.write("{}'s Annual Volatility : ".format(option_2_e_1[0]) + "{:.3%}".format((strategy_data[option_2_e_1][-60:].dropna().shift(1)/strategy_data[option_2_e_1][-60:].dropna()-1).std().values[0]*np.sqrt(252)))
            
            with st.container():
                col1_e, col2_e, col3_e = st.columns(3)
                with col1_e:
                    rates_bool_e_2 = st.selectbox('Rates or Others   ', ['Rates', 'Others'], label_visibility="collapsed")
                with col2_e: 
                    if 'Rates' in rates_bool_e_2:
                        option_2_e_2 = st.multiselect('Strategy   ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                        if len(option_2_e_2)>0:   
                            option_2_e_2 = [get_strategy_name(option_2_e_2)]
                    else:
                        option_2_e_2 = st.selectbox('Strategy   ', sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                        option_2_e_2 = [option_2_e_2]
                with col3_e: 
                    option_3_e_2 = st.selectbox('Trade Direction   ', [1, -1], label_visibility="collapsed")
                if len(option_2_e_2)>0:  
                    if option_3_e_2 == 1:
                        volatility_list.append((strategy_data[option_2_e_2][-60:].dropna()/strategy_data[option_2_e_2][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252))
                        st.write("{}'s Annual Volatility : ".format(option_2_e_2[0]) + "{:.3%}".format((strategy_data[option_2_e_2][-60:].dropna()/strategy_data[option_2_e_2][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252)))
                    else:
                        volatility_list.append((strategy_data[option_2_e_2][-60:].dropna().shift(1)/strategy_data[option_2_e_2][-60:].dropna()-1).std().values[0]*np.sqrt(252))
                        st.write("{}'s Annual Volatility : ".format(option_2_e_2[0]) + "{:.3%}".format((strategy_data[option_2_e_2][-60:].dropna().shift(1)/strategy_data[option_2_e_2][-60:].dropna()-1).std().values[0]*np.sqrt(252)))
            
            with st.container():
                col1_e, col2_e, col3_e = st.columns(3)
                with col1_e:
                    rates_bool_e_3 = st.selectbox('Rates or Others    ', ['Rates', 'Others'], label_visibility="collapsed")
                with col2_e: 
                    if 'Rates' in rates_bool_e_3:
                        option_2_e_3 = st.multiselect('Strategy    ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                        if len(option_2_e_3)>0:   
                            option_2_e_3 = [get_strategy_name(option_2_e_3)]
                    else:
                        option_2_e_3 = st.selectbox('Strategy    ', sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                        option_2_e_3 = [option_2_e_3]
                with col3_e: 
                    option_3_e_3 = st.selectbox('Trade Direction    ', [1, -1], label_visibility="collapsed")
                if len(option_2_e_3)>0:  
                    if option_3_e_3 == 1:
                        volatility_list.append((strategy_data[option_2_e_3][-60:].dropna()/strategy_data[option_2_e_3][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252))
                        st.write("{}'s Annual Volatility : ".format(option_2_e_3[0]) + "{:.3%}".format((strategy_data[option_2_e_3][-60:].dropna()/strategy_data[option_2_e_3][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252)))
                    else:
                        volatility_list.append((strategy_data[option_2_e_3][-60:].dropna().shift(1)/strategy_data[option_2_e_3][-60:].dropna()-1).std().values[0]*np.sqrt(252))
                        st.write("{}'s Annual Volatility : ".format(option_2_e_3[0]) + "{:.3%}".format((strategy_data[option_2_e_3][-60:].dropna().shift(1)/strategy_data[option_2_e_3][-60:].dropna()-1).std().values[0]*np.sqrt(252)))
            
            with st.container():
                col1_e, col2_e, col3_e = st.columns(3)
                with col1_e:
                    rates_bool_e_4 = st.selectbox('Rates or Others     ', ['Rates', 'Others'], label_visibility="collapsed")
                with col2_e: 
                    if 'Rates' in rates_bool_e_4:
                        option_2_e_4 = st.multiselect('Strategy     ', sorted(outright_list), default=None, max_selections=3, label_visibility="collapsed")
                        if len(option_2_e_4)>0:   
                            option_2_e_4 = [get_strategy_name(option_2_e_4)]
                    else:
                        option_2_e_4 = st.selectbox('Strategy     ', sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), label_visibility="collapsed")
                        option_2_e_4 = [option_2_e_4]
                with col3_e: 
                    option_3_e_4 = st.selectbox('Trade Direction     ',[1, -1], label_visibility="collapsed")
                if len(option_2_e_4)>0:  
                    if option_3_e_4 == 1:
                        volatility_list.append((strategy_data[option_2_e_4][-60:].dropna()/strategy_data[option_2_e_4][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252))
                        st.write("{}'s Annual Volatility : ".format(option_2_e_4[0]) + "{:.3%}".format((strategy_data[option_2_e_4][-60:].dropna()/strategy_data[option_2_e_4][-60:].dropna().shift(1)-1).std().values[0]*np.sqrt(252)))
                    else:
                        volatility_list.append((strategy_data[option_2_e_4][-60:].dropna().shift(1)/strategy_data[option_2_e_4][-60:].dropna()-1).std().values[0]*np.sqrt(252))
                        st.write("{}'s Annual Volatility : ".format(option_2_e_4[0]) + "{:.3%}".format((strategy_data[option_2_e_4][-60:].dropna().shift(1)/strategy_data[option_2_e_4][-60:].dropna()-1).std().values[0]*np.sqrt(252)))

        st.session_state.lookback = lb_list
        st.session_state.refdate = ref_date
        st.session_state.strats = option_2 + option_2_e + option_2_e_1 + option_2_e_2 + option_2_e_3 + option_2_e_4 
        st.session_state.tradedirection = [option_3] + [option_3_e] + [option_3_e_1] + [option_3_e_2] + [option_3_e_3] + [option_3_e_4]
        st.session_state.volatility = volatility_list
        st.session_state.portbool = portfolio_bool
        
        with tab2:
            col1, col2 = st.columns(2)
            with col1:
                if len(st.session_state.strats)>0:
                    if st.session_state.portbool == 'Strategy':
                        strat = st.selectbox('Select Strategy', st.session_state.strats)
                        ix = st.session_state.strats.index(strat)
                        strategy_selected = strategy_set.copy()[[strat]]
                        strategy_index = strategy_selected[[strat]]
                        if st.session_state.tradedirection[ix] == 1:
                            strategy_index_direction = (1+(strategy_index/strategy_index.shift(1)-1)).cumprod().fillna(1)
                        elif st.session_state.tradedirection[ix] == -1:
                            strategy_index_direction = (1+(strategy_index.shift(1)/strategy_index-1)).cumprod().fillna(1)
                    elif st.session_state.portbool == 'Portfolio':
                        strat = st.selectbox('Select Strategy',['Portfolio'])
                        strategy_selected = strategy_set.copy()[st.session_state.strats]
                        strategy_index  = strategy_selected[st.session_state.strats]
                        weight = [1/v for v in st.session_state.volatility]
                        weight = [np.round(w/sum(weight),2) for w in weight]

                        for i, strt in enumerate(st.session_state.strats):
                            w = weight[i]
                            if i == 0:
                                if st.session_state.tradedirection[i] == 1:
                                    strategy_index_direction = (strategy_index[strt]/strategy_index[strt].shift(1)-1)*w
                                    strategy_index_direction.name = 'Portfolio'
                                elif st.session_state.tradedirection[i] == -1:
                                    strategy_index_direction = (strategy_index[strt].shift(1)/strategy_index[strt]-1)*w
                                    strategy_index_direction.name = 'Portfolio'
                            else:
                                if st.session_state.tradedirection[i] == 1:
                                    strategy_index_direction_ = (strategy_index[strt]/strategy_index[strt].shift(1)-1)*w
                                    strategy_index_direction_.name = 'Portfolio'
                                elif st.session_state.tradedirection[i] == -1:
                                    strategy_index_direction_ = (strategy_index[strt].shift(1)/strategy_index[strt]-1)*w
                                    strategy_index_direction_.name = 'Portfolio'
                                strategy_index_direction += strategy_index_direction_
                        strategy_index_direction = (1+pd.DataFrame(strategy_index_direction)).cumprod().fillna(1)
                        st.session_state.portfolio = strategy_index_direction

            with col2:
                col2_1, col2_2, col2_3 = st.columns(3)
                with col2_3:
                    st.write('')
                    st.write('')
                    start_button = st.button('Print Report')
            
            @st.cache_resource(show_spinner=False)
            def get_quad_regime(strategy_index, macro_factor_index, lookup_date, manual_lookback_list):
                _, _, gmm_df_recalc, _, strategy_regime_, _, _, strategy_distance_sharpe_df, macro_regime_mean_df, macro_regime_std_df, macro_regime_sharpe_df, strategy_regime_mean_df, strategy_regime_std_df, strategy_regime_sharpe_df, _ = rd.quad_regime(strategy_index, macro_factor_index, lookup_date, manual_lookback_list)
                return gmm_df_recalc, strategy_regime_, strategy_distance_sharpe_df, macro_regime_mean_df, macro_regime_std_df, macro_regime_sharpe_df, strategy_regime_mean_df, strategy_regime_std_df, strategy_regime_sharpe_df
            
            if start_button:
                progress_bar = st.progress(0.0, 'Calculating')
                #sim_hist_dict, transition_matrix_df, gmm_df_recalc, regime_probability, strategy_regime_, strategy_distance_mean_df, strategy_distance_std_df, strategy_distance_sharpe_df, macro_regime_mean_df, macro_regime_std_df, macro_regime_sharpe_df, strategy_regime_mean_df, strategy_regime_std_df, strategy_regime_sharpe_df, strategy_preference = rd.quad_regime(strategy_index, rd.macro_factor_index, st.session_state.ref_date, st.session_state.lookback)
                strategy_index_direction.columns = [str(c) for c in list(strategy_index_direction.columns)]
                strat = str(strat)
                progress_bar.progress(0.25, text='Calculating')
                #_, _, gmm_df_recalc, _, strategy_regime_, _, _, strategy_distance_sharpe_df, macro_regime_mean_df, _, macro_regime_sharpe_df, strategy_regime_mean_df, _, strategy_regime_sharpe_df, _ = rd.quad_regime(strategy_index_direction, rd.macro_factor_index, st.session_state.refdate, st.session_state.lookback)
                gmm_df_recalc, strategy_regime_, strategy_distance_sharpe_df, macro_regime_mean_df, macro_regime_std_df, macro_regime_sharpe_df, strategy_regime_mean_df, strategy_regime_std_df, strategy_regime_sharpe_df = get_quad_regime(strategy_index_direction, rd.macro_factor_index, st.session_state.refdate, st.session_state.lookback)
                progress_bar.progress(1.0, text='Calculating')
                time.sleep(0.5)
                progress_bar.empty()
                start_button = False

                with st.container():
                    strategy_regime_df = strategy_regime_[[strat, 'Distance_Count']].copy()
                    strategy_regime_df[strat] = (1+strategy_regime_df[strat]).cumprod().values
                    strategy_regime_df = strategy_regime_df.reset_index()
                    strategy_regime_df = strategy_regime_df.rename(columns={'index':'date','Distance_Count':'Distance Similarity'})

                    #Distance Regime Plot
                    fig = make_subplots(specs=[[{"secondary_y":True}]])
                    fig.add_trace(go.Scatter(x=strategy_regime_df['date'], y=strategy_regime_df[strat], name=str(strat), mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ str(strat) + ': %{y:.3f}'), secondary_y=True)
                    fig.add_trace(go.Bar(x=strategy_regime_df['date'], y=strategy_regime_df['Distance Similarity'], name='Similarity', hovertemplate='<br>date: %{x:|%B %d, %Y}<br> Similarity Count: %{y:.1f}'), secondary_y=False)
                    
                    fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
                    fig.update_yaxes(title_text='Similarity', secondary_y=False)
                    fig.update_yaxes(title_text=str(strat), secondary_y=True)
                    
                    st.markdown('**Distance Regime**')
                    st.plotly_chart(fig, use_container_width=True)

                    #GMM Regime Bar Plot
                    gmm_df_recalc_ = pd.concat([gmm_df_recalc.copy(), strategy_regime_df.set_index('date')[[strat]]], axis=1, sort=True).fillna(method='ffill')
                    gmm_df_recalc_ = gmm_df_recalc_.reset_index()
                    gmm_df_recalc_ = gmm_df_recalc_.rename(columns={'index':'date', 'Regime_1':'Regime 1', 'Regime_2':'Regime 2', 'Regime_3':'Regime 3', 'Regime_4':'Regime 4'})
                    
                    fig_r = make_subplots(specs=[[{"secondary_y":True}]], subplot_titles=['GMM Regime'])
                    fig_r.add_trace(go.Bar(x=gmm_df_recalc_['date'], y=gmm_df_recalc_['Regime 1'], name='Regime 1', hovertemplate='<br>date: %{x:|%B %d, %Y}<br> Regime 1: %{y:.3f}'), secondary_y=False)
                    fig_r.add_trace(go.Bar(x=gmm_df_recalc_['date'], y=gmm_df_recalc_['Regime 2'], name='Regime 2', hovertemplate='<br>date: %{x:|%B %d, %Y}<br> Regime 2: %{y:.3f}'), secondary_y=False)
                    fig_r.add_trace(go.Bar(x=gmm_df_recalc_['date'], y=gmm_df_recalc_['Regime 3'], name='Regime 3', hovertemplate='<br>date: %{x:|%B %d, %Y}<br> Regime 3: %{y:.3f}'), secondary_y=False)
                    fig_r.add_trace(go.Bar(x=gmm_df_recalc_['date'], y=gmm_df_recalc_['Regime 4'], name='Regime 4', hovertemplate='<br>date: %{x:|%B %d, %Y}<br> Regime 4: %{y:.3f}'), secondary_y=False)
                    fig_r.add_trace(go.Scatter(x=gmm_df_recalc_['date'], y=gmm_df_recalc_[strat], name=str(strat), mode='lines', line=dict(color='#3366cc'), hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ str(strat) + ': %{y:.3f}'), secondary_y=True)
                    
                    fig_r.update_layout(barmode='stack')
                    fig_r.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
                    fig_r.update_yaxes(title_text='GMM', secondary_y=False)
                    fig_r.update_yaxes(title_text=str(strat), secondary_y=True)
                    st.markdown('**GMM Regime**')
                    st.plotly_chart(fig_r, use_container_width=True)

                st.divider() 
                with st.container():  
                    regime_mean = pd.concat([strategy_regime_mean_df,macro_regime_mean_df], axis=0)
                    regime_mean = regime_mean.rename(columns={'index':'date', 'Regime_1':'Regime 1', 'Regime_2':'Regime 2', 'Regime_3':'Regime 3', 'Regime_4':'Regime 4'})
                    strategy_regime_sharpe_df_ = strategy_regime_sharpe_df[['Regime_1', 'Regime_2', 'Regime_3', 'Regime_4']]
                    regime_sharpe = pd.concat([strategy_regime_sharpe_df_, macro_regime_sharpe_df], axis=0)
                    regime_sharpe = regime_sharpe.rename(columns={'index':'date', 'Regime_1':'Regime 1', 'Regime_2':'Regime 2', 'Regime_3':'Regime 3', 'Regime_4':'Regime 4'})
                    regime_sharpe_ = regime_sharpe.reset_index()
                    regime_sharpe_ = regime_sharpe_.rename(columns={'index':'Factors'})

                    #st.markdown('**Daily Mean/Vol**')
                    #regime_sharpe_df.index = [c.replace("_", " ") for c in regime_sharpe_df.index]
                    #st.table(regime_sharpe_df.T.style.set_properties(**{'width':'10em', 'text-align':'center'}).background_gradient(cmap='RdBu', axis=1))
                
                 
                    col1, col2 = st.columns(2)
                    regime_mean_scatter = regime_mean.copy()
                    regime_mean_scatter.index.name = 'Factors'
                    regime_sharpe_scatter = regime_sharpe_.copy().set_index('Factors')
                    
                    with col1:
                        regime_select_1 = 'Regime 1'
                        
                        regime_scatter_1 = pd.concat([regime_mean_scatter[[regime_select_1]].rename(columns={regime_select_1:'Avg'}), regime_sharpe_scatter[[regime_select_1]].rename(columns={regime_select_1:'Std'})], axis=1)
                        regime_scatter_1['Avg/Std'] = regime_scatter_1['Avg']/regime_scatter_1['Std']
                        regime_scatter_1 = regime_scatter_1.reset_index()
                        
                        fig_scatter_1 = px.scatter(regime_scatter_1, x='Avg', y = 'Std', size='Avg/Std', color='Factors', size_max=20, title='Regime 1 Quadrant')
                        fig_scatter_1.update_xaxes(zeroline=True, zerolinecolor='#222A2A')
                        fig_scatter_1.update_yaxes(zeroline=True, zerolinecolor='#222A2A')
                        st.plotly_chart(fig_scatter_1)

                        regime_select_3 = 'Regime 3'

                        regime_scatter_3 = pd.concat([regime_mean_scatter[[regime_select_3]].rename(columns={regime_select_3:'Avg'}), regime_sharpe_scatter[[regime_select_3]].rename(columns={regime_select_3:'Std'})], axis=1)
                        regime_scatter_3['Avg/Std'] = regime_scatter_3['Avg']/regime_scatter_3['Std']
                        regime_scatter_3 = regime_scatter_3.reset_index()
                        
                        fig_scatter_3 = px.scatter(regime_scatter_3, x='Avg', y = 'Std', size='Avg/Std', color='Factors', size_max=20, title='Regime 3 Quadrant')
                        fig_scatter_3.update_xaxes(zeroline=True, zerolinecolor='#222A2A')
                        fig_scatter_3.update_yaxes(zeroline=True, zerolinecolor='#222A2A')
                        st.plotly_chart(fig_scatter_3)
                        
                    with col2:
                        regime_select_2 = 'Regime 2'
                        
                        regime_scatter_2 = pd.concat([regime_mean_scatter[[regime_select_2]].rename(columns={regime_select_2:'Avg'}), regime_sharpe_scatter[[regime_select_2]].rename(columns={regime_select_2:'Std'})], axis=1)
                        regime_scatter_2['Avg/Std'] = regime_scatter_2['Avg']/regime_scatter_2['Std']
                        regime_scatter_2 = regime_scatter_2.reset_index()
                        
                        fig_scatter_2 = px.scatter(regime_scatter_2, x='Avg', y = 'Std', size='Avg/Std', color='Factors', size_max=20, title='Regime 2 Quadrant')
                        fig_scatter_2.update_xaxes(zeroline=True, zerolinecolor='#222A2A')
                        fig_scatter_2.update_yaxes(zeroline=True, zerolinecolor='#222A2A')
                        st.plotly_chart(fig_scatter_2)

                        regime_select_4 = 'Regime 4'

                        regime_scatter_4 = pd.concat([regime_mean_scatter[[regime_select_4]].rename(columns={regime_select_4:'Avg'}), regime_sharpe_scatter[[regime_select_4]].rename(columns={regime_select_4:'Std'})], axis=1)
                        regime_scatter_4['Avg/Std'] = regime_scatter_4['Avg']/regime_scatter_4['Std']
                        regime_scatter_4 = regime_scatter_4.reset_index()
                        
                        fig_scatter_4 = px.scatter(regime_scatter_4, x='Avg', y = 'Std', size='Avg/Std', color='Factors', size_max=20, title='Regime 4 Quadrant')
                        fig_scatter_4.update_xaxes(zeroline=True, zerolinecolor='#222A2A')
                        fig_scatter_4.update_yaxes(zeroline=True, zerolinecolor='#222A2A')
                        st.plotly_chart(fig_scatter_4)
                
                st.divider() 
                with st.container():
                    col1, col2 = st.columns(2)
                    with col1:
                        fig1 = px.bar(regime_sharpe_, x='Factors', y='Regime 1', color='Regime 1')
                        fig1.update_yaxes(title_text='Perform. Measure')
                        fig3 = px.bar(regime_sharpe_, x='Factors', y='Regime 3', color='Regime 3')
                        fig3.update_yaxes(title_text='Perform. Measure')
                        st.markdown('**Regime 1 Performance Measure**')
                        st.plotly_chart(fig1, use_container_width=True)
                        st.markdown('**Regime 3 Performance Measure**')
                        st.plotly_chart(fig3, use_container_width=True)

                    with col2:
                        fig2 = px.bar(regime_sharpe_, x='Factors', y='Regime 2', color='Regime 2')
                        fig2.update_yaxes(title_text='Perform. Measure')
                        fig4 = px.bar(regime_sharpe_, x='Factors', y='Regime 4', color='Regime 4')
                        fig4.update_yaxes(title_text='Perform. Measure')
                        st.markdown('**Regime 2 Performance Measure**')
                        st.plotly_chart(fig2, use_container_width=True)
                        st.markdown('**Regime 4 Performance Measure**')
                        st.plotly_chart(fig4, use_container_width=True)
                
                st.download_button(label="Download data as CSV",data= convert_df(regime_sharpe),file_name='Regime_Sharpe_{}.csv'.format(date.today().isoformat()), mime='text/csv')
    
        with tab3:
            with st.expander('Macro Factor Chart'):
                if st.session_state.portbool == 'Strategy':
                    macro_factor_selected = st.multiselect("Choose Macro Factor", st.session_state.strats + strategy_list_macrofactor)
                    macro_series = strategy_data[macro_factor_selected]
                if st.session_state.portbool == 'Portfolio':
                    macro_factor_selected = st.multiselect("Choose Macro Factor", st.session_state.strats + ['Portfolio'] + strategy_list_macrofactor) 
                    macro_series = pd.concat([strategy_data, st.session_state.portfolio], axis=1, sort=True).fillna(method='ffill')[macro_factor_selected]
                                    
                macro_series = macro_series.reset_index().rename(columns={'index': 'date'})
                macro_series.columns = [str(c) for c in macro_series.columns]
                
                if len(macro_factor_selected)>0:
                    if len(macro_factor_selected) == 1:
                        fig_ = go.Figure()
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][0]], name=[str(c) for c in macro_factor_selected][0], mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][0] + ': %{y:.3f}'))
                        fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]))
                    
                    elif len(macro_factor_selected) == 2:
                        fig_ = go.Figure()
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][0]], name=[str(c) for c in macro_factor_selected][0], mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][0] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][1]], name=[str(c) for c in macro_factor_selected][1], mode='lines', yaxis="y2", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][1] + ': %{y:.3f}'))
                        fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"))
                    
                    elif len(macro_factor_selected) == 3:
                        fig_ = go.Figure()
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][0]], name=[str(c) for c in macro_factor_selected][0], mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][0] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][1]], name=[str(c) for c in macro_factor_selected][1], mode='lines', yaxis="y2", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][1] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][2]], name=[str(c) for c in macro_factor_selected][2], mode='lines', yaxis="y3", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][2] + ': %{y:.3f}'))
                        fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))
                    
                    elif len(macro_factor_selected) == 4:
                        fig_ = go.Figure()
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][0]], name=[str(c) for c in macro_factor_selected][0], mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][0] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][1]], name=[str(c) for c in macro_factor_selected][1], mode='lines', yaxis="y2", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][1] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][2]], name=[str(c) for c in macro_factor_selected][2], mode='lines', yaxis="y3", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][2] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][3]], name=[str(c) for c in macro_factor_selected][3], mode='lines', yaxis="y4", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][3] + ': %{y:.3f}'))
                        
                        fig_.update_layout(xaxis=dict(domain=[0.05, 0.92]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.99))
                    
                    elif len(macro_factor_selected) == 5:
                        fig_ = go.Figure()
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][0]], name=[str(c) for c in macro_factor_selected][0], mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][0] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][1]], name=[str(c) for c in macro_factor_selected][1], mode='lines', yaxis="y2", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][1] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][2]], name=[str(c) for c in macro_factor_selected][2], mode='lines', yaxis="y3", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][2] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][3]], name=[str(c) for c in macro_factor_selected][3], mode='lines', yaxis="y4", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][3] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][4]], name=[str(c) for c in macro_factor_selected][4], mode='lines', yaxis="y5", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][4] + ': %{y:.3f}'))
                        
                        fig_.update_layout(xaxis=dict(domain=[0.05, 0.92]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.015),
                                        yaxis3=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.99))
                    
                    elif len(macro_factor_selected) == 6:
                        fig_ = go.Figure()
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][0]], name=[str(c) for c in macro_factor_selected][0], mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][0] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][1]], name=[str(c) for c in macro_factor_selected][1], mode='lines', yaxis="y2", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][1] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][2]], name=[str(c) for c in macro_factor_selected][2], mode='lines', yaxis="y3", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][2] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][3]], name=[str(c) for c in macro_factor_selected][3], mode='lines', yaxis="y4", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][3] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][4]], name=[str(c) for c in macro_factor_selected][4], mode='lines', yaxis="y5", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][4] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][5]], name=[str(c) for c in macro_factor_selected][5], mode='lines', yaxis="y6", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][5] + ': %{y:.3f}'))
                        
                        fig_.update_layout(xaxis=dict(domain=[0.05, 0.90]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.015),
                                        yaxis3=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.93),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.955), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.98))
                    
                    elif len(macro_factor_selected) == 7:
                        fig_ = go.Figure()
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][0]], name=[str(c) for c in macro_factor_selected][0], mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][0] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][1]], name=[str(c) for c in macro_factor_selected][1], mode='lines', yaxis="y2", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][1] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][2]], name=[str(c) for c in macro_factor_selected][2], mode='lines', yaxis="y3", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][2] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][3]], name=[str(c) for c in macro_factor_selected][3], mode='lines', yaxis="y4", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][3] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][4]], name=[str(c) for c in macro_factor_selected][4], mode='lines', yaxis="y5", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][4] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][5]], name=[str(c) for c in macro_factor_selected][5], mode='lines', yaxis="y6", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][5] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][6]], name=[str(c) for c in macro_factor_selected][6], mode='lines', yaxis="y7", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][6] + ': %{y:.3f}'))
                        
                        fig_.update_layout(xaxis=dict(domain=[0.065, 0.90]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                        yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                        yaxis4=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.93), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.98))
                        
                    elif len(macro_factor_selected) == 8:
                        fig_ = go.Figure()
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][0]], name=[str(c) for c in macro_factor_selected][0], mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][0] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][1]], name=[str(c) for c in macro_factor_selected][1], mode='lines', yaxis="y2", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][1] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][2]], name=[str(c) for c in macro_factor_selected][2], mode='lines', yaxis="y3", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][2] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][3]], name=[str(c) for c in macro_factor_selected][3], mode='lines', yaxis="y4", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][3] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][4]], name=[str(c) for c in macro_factor_selected][4], mode='lines', yaxis="y5", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][4] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][5]], name=[str(c) for c in macro_factor_selected][5], mode='lines', yaxis="y6", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][5] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][6]], name=[str(c) for c in macro_factor_selected][6], mode='lines', yaxis="y7", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][6] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][7]], name=[str(c) for c in macro_factor_selected][7], mode='lines', yaxis="y8", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][7] + ': %{y:.3f}'))
                        
                        fig_.update_layout(xaxis=dict(domain=[0.065, 0.865]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                        yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                        yaxis4=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.90), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.93),
                                        yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.96), 
                                        yaxis8=dict(anchor="free",overlaying="y",side="right", position=0.99))
                    
                    elif len(macro_factor_selected) == 9:
                        fig_ = go.Figure()
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][0]], name=[str(c) for c in macro_factor_selected][0], mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][0] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][1]], name=[str(c) for c in macro_factor_selected][1], mode='lines', yaxis="y2", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][1] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][2]], name=[str(c) for c in macro_factor_selected][2], mode='lines', yaxis="y3", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][2] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][3]], name=[str(c) for c in macro_factor_selected][3], mode='lines', yaxis="y4", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][3] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][4]], name=[str(c) for c in macro_factor_selected][4], mode='lines', yaxis="y5", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][4] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][5]], name=[str(c) for c in macro_factor_selected][5], mode='lines', yaxis="y6", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][5] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][6]], name=[str(c) for c in macro_factor_selected][6], mode='lines', yaxis="y7", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][6] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][7]], name=[str(c) for c in macro_factor_selected][7], mode='lines', yaxis="y8", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][7] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][8]], name=[str(c) for c in macro_factor_selected][8], mode='lines', yaxis="y9", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][8] + ': %{y:.3f}'))
                        
                        fig_.update_layout(xaxis=dict(domain=[0.095, 0.865]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.06),
                                        yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                        yaxis4=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                        yaxis5=dict(anchor="x",overlaying="y",side="right"), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.90),
                                        yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.93), 
                                        yaxis8=dict(anchor="free",overlaying="y",side="right", position=0.96),
                                        yaxis9=dict(anchor="free",overlaying="y",side="right", position=0.99))
                    
                    elif len(macro_factor_selected) == 10:
                        fig_ = go.Figure()
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][0]], name=[str(c) for c in macro_factor_selected][0], mode='lines', hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][0] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][1]], name=[str(c) for c in macro_factor_selected][1], mode='lines', yaxis="y2", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][1] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][2]], name=[str(c) for c in macro_factor_selected][2], mode='lines', yaxis="y3", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][2] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][3]], name=[str(c) for c in macro_factor_selected][3], mode='lines', yaxis="y4", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][3] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][4]], name=[str(c) for c in macro_factor_selected][4], mode='lines', yaxis="y5", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][4] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][5]], name=[str(c) for c in macro_factor_selected][5], mode='lines', yaxis="y6", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][5] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][6]], name=[str(c) for c in macro_factor_selected][6], mode='lines', yaxis="y7", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][6] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][7]], name=[str(c) for c in macro_factor_selected][7], mode='lines', yaxis="y8", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][7] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][8]], name=[str(c) for c in macro_factor_selected][8], mode='lines', yaxis="y9", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][8] + ': %{y:.3f}'))
                        fig_.add_trace(go.Scatter(x=macro_series['date'], y=macro_series[[str(c) for c in macro_factor_selected][9]], name=[str(c) for c in macro_factor_selected][9], mode='lines', yaxis="y10", hovertemplate='<br>date: %{x:|%B %d, %Y}<br>'+ [str(c) for c in macro_factor_selected][9] + ': %{y:.3f}'))
                        
                        fig_.update_layout(xaxis=dict(domain=[0.095, 0.835]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.06),
                                        yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                        yaxis4=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                        yaxis5=dict(anchor="x",overlaying="y",side="right"), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.87),
                                        yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.90), 
                                        yaxis8=dict(anchor="free",overlaying="y",side="right", position=0.93),
                                        yaxis9=dict(anchor="free",overlaying="y",side="right", position=0.96),
                                        yaxis10=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                    fig_.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")]))) 
                    
                    st.plotly_chart(fig_, use_container_width=True)
                
            col1, col2 = st.columns(2)
            with col1:
                rf_lookback = st.slider('Random Forest Lookback', 0, 500, step=10)
            with col2:
                reg_lookback = st.slider('Regression Lookback', 0, 1250, step=10)
            
            if rf_lookback>0 and reg_lookback>0:
                if st.session_state.portbool == 'Strategy':
                    selected_strategy_position = [[s[0], s[1]] for s in zip(st.session_state.strats, st.session_state.tradedirection)]
                    factor_sensitivity = rd.macro_factor_sensitivity_strategy(rf_lookback, reg_lookback,selected_strategy_position)
                    
                elif st.session_state.portbool == 'Portfolio':
                    selected_strategy_position = [[s[0], s[1]] for s in zip(st.session_state.strats, st.session_state.tradedirection)]
                    factor_sensitivity = rd.macro_factor_sensitivity_portfolio(rf_lookback, reg_lookback, selected_strategy_position, port_cumulative_series = st.session_state.portfolio)
                
                col_1, col_2 = st.columns(2)     
                with col_1:
                    if st.session_state.portbool == 'Portfolio':
                        st.markdown('**Portfolio**')
                        st.dataframe(factor_sensitivity.set_index('Factor'), width = 630, height = 630)
                    elif st.session_state.portbool == 'Strategy':
                        if len(factor_sensitivity.keys())==1:
                            st.markdown('**{}**'.format(selected_strategy_position[0][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[0][0]].set_index('Factor'), width = 630, height = 630)
                        elif len(factor_sensitivity.keys())==2:
                            st.markdown('**{}**'.format(selected_strategy_position[0][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[0][0]].set_index('Factor'), width = 630, height = 630)
                        elif len(factor_sensitivity.keys())==3:
                            st.markdown('**{}**'.format(selected_strategy_position[0][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[0][0]].set_index('Factor'), width = 630, height = 630)
                            st.markdown('**{}**'.format(selected_strategy_position[2][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[2][0]].set_index('Factor'), width = 630, height = 630)
                        elif len(factor_sensitivity.keys())==4:
                            st.markdown('**{}**'.format(selected_strategy_position[0][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[0][0]].set_index('Factor'), width = 630, height = 630)
                            st.markdown('**{}**'.format(selected_strategy_position[2][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[2][0]].set_index('Factor'), width = 630, height = 630)
                        elif len(factor_sensitivity.keys())==5:
                            st.markdown('**{}**'.format(selected_strategy_position[0][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[0][0]].set_index('Factor'), width = 630, height = 630)
                            st.markdown('**{}**'.format(selected_strategy_position[2][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[2][0]].set_index('Factor'), width = 630, height = 630)
                            st.markdown('**{}**'.format(selected_strategy_position[4][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[4][0]].set_index('Factor'), width = 630, height = 630)
                        elif len(factor_sensitivity.keys())==6:
                            st.markdown('**{}**'.format(selected_strategy_position[0][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[0][0]].set_index('Factor'), width = 630, height = 630)
                            st.markdown('**{}**'.format(selected_strategy_position[2][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[2][0]].set_index('Factor'), width = 630, height = 630)
                            st.markdown('**{}**'.format(selected_strategy_position[4][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[4][0]].set_index('Factor'), width = 630, height = 630)
                with col_2:
                    if st.session_state.portbool == 'Strategy':
                        if len(factor_sensitivity.keys())==2:
                            st.markdown('**{}**'.format(selected_strategy_position[1][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[1][0]].set_index('Factor'), width = 630, height = 630)
                        elif len(factor_sensitivity.keys())==3:
                            st.markdown('**{}**'.format(selected_strategy_position[1][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[1][0]].set_index('Factor'), width = 630, height = 630)
                        elif len(factor_sensitivity.keys())==4:
                            st.markdown('**{}**'.format(selected_strategy_position[1][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[1][0]].set_index('Factor'), width = 630, height = 630)
                            st.markdown('**{}**'.format(selected_strategy_position[3][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[3][0]].set_index('Factor'), width = 630, height = 630)
                        elif len(factor_sensitivity.keys())==5:
                            st.markdown('**{}**'.format(selected_strategy_position[1][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[1][0]].set_index('Factor'), width = 630, height = 630)
                            st.markdown('**{}**'.format(selected_strategy_position[3][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[3][0]].set_index('Factor'), width = 630, height = 630)
                        elif len(factor_sensitivity.keys())==6:
                            st.markdown('**{}**'.format(selected_strategy_position[1][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[1][0]].set_index('Factor'), width = 630, height = 630)
                            st.markdown('**{}**'.format(selected_strategy_position[3][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[3][0]].set_index('Factor'), width = 630, height = 630)
                            st.markdown('**{}**'.format(selected_strategy_position[5][0]))
                            st.dataframe(factor_sensitivity[selected_strategy_position[5][0]].set_index('Factor'), width = 630, height = 630)

        with tab4:
            st.markdown('**Cumulative Return Divergence Probability**')
            #cumulative_return_divergence_probability(self, strategy, start_dt, end_dt, regime_lookup_date, strategy_performance_end_date, estimation_horizon, rates, *manual_lookback_list):

            @st.cache_resource(show_spinner=False)
            def get_cum_ret_distribution(strategy, start_dt, end_dt, regime_lookup_date, strategy_performance_end_date, estimation_horizon, rates, *manual_lookback_list, **portfolio_input):
                if len(manual_lookback_list)>0:
                    if strategy == 'Portfolio':
                        prob_dist, prob_quad = rm.cumulative_return_divergence_probability(strategy, start_dt, end_dt, regime_lookup_date, strategy_performance_end_date, estimation_horizon, rates, manual_lookback_list[0], portfolio_index=portfolio_input['portfolio_index'])
                    else:
                        prob_dist, prob_quad = rm.cumulative_return_divergence_probability(strategy, start_dt, end_dt, regime_lookup_date, strategy_performance_end_date, estimation_horizon, rates, manual_lookback_list[0])
                else:
                    if strategy == 'Portfolio':
                        prob_dist, prob_quad = rm.cumulative_return_divergence_probability(strategy, start_dt, end_dt, regime_lookup_date, strategy_performance_end_date, estimation_horizon, rates, portfolio_index=portfolio_input['portfolio_index'])
                    else:
                        prob_dist, prob_quad = rm.cumulative_return_divergence_probability(strategy, start_dt, end_dt, regime_lookup_date, strategy_performance_end_date, estimation_horizon, rates)
                return prob_dist, prob_quad

            colr_1, colr_2 = st.columns(2)
            with colr_1:
                colr_1_, colr_2_, colr_3_ = st.columns(3)
                with colr_1_:
                    st.write('')
                    st.write('')
                    calculate_button = st.button('Calculate')
                    
                with colr_2_:
                    portfolio_bool = st.radio('Analysis Type ', ['Strategy', 'Portfolio'])
                with colr_3_:
                    rates_bool_ = st.selectbox('Rates or Others      ', ['Rates', 'Others'])
                    
                assessment_reference_date = datetime.strftime(st.date_input('Assessment Reference Date'), "%Y-%m-%d")
                regime_reference_date = datetime.strftime(st.date_input('Regime Reference Date'), "%Y-%m-%d")

            with colr_2: 
                if portfolio_bool == 'Strategy':
                    if 'Rates' in rates_bool_:
                        rates_bool_ = True
                        option_2 = st.multiselect('Strategy      ', sorted(outright_list), default=None, max_selections=3)
                        if len(option_2)>0:
                            option_2 = [get_strategy_name(option_2)]
                    else:
                        rates_bool_ = False
                        option_2 = st.multiselect('Strategy      ', sorted(strategy_list_futures) + sorted(strategy_list_rp) + sorted(strategy_list_macrofactor), max_selections=1)
                        option_2 = option_2
                else:
                    if 'Rates' in rates_bool_:
                        rates_bool_ = True
                    else:
                        rates_bool_ = False
                
                performance_assessment_lookback = st.slider('Performance Assessment Lookback',20,2500,20,10)

                colr_1___, colr_2___ = st.columns(2)
                with colr_1___:
                    start_dt = datetime.strftime(st.date_input('Distribution Calculation Start'), '%Y-%m-%d')
                    
                with colr_2___:
                    end_dt = datetime.strftime(st.date_input('Distribution Calculation End'), '%Y-%m-%d')

            if calculate_button:
                if len(option_2)>0 or portfolio_bool == 'Portfolio':
                    if portfolio_bool == 'Strategy':
                        strategy = option_2[0]
                        progress_bar = st.progress(0.0, 'Calculating')
                        progress_bar.progress(0.25, text='Calculating')
                        prob_dist, prob_quad = get_cum_ret_distribution(strategy, start_dt, end_dt, regime_reference_date, assessment_reference_date, performance_assessment_lookback, rates_bool_)
                        progress_bar.progress(1.0, text='Calculating')
                        time.sleep(0.5)
                        progress_bar.empty()

                    elif portfolio_bool == 'Portfolio':
                        strategy = 'Portfolio'
                        port = st.session_state.portfolio
                        progress_bar = st.progress(0.0, 'Calculating')
                        progress_bar.progress(0.25, text='Calculating')
                        prob_dist, prob_quad = get_cum_ret_distribution(strategy, start_dt, end_dt, regime_reference_date, assessment_reference_date, performance_assessment_lookback, rates_bool_, portfolio_index=port)
                        progress_bar.progress(1.0, text='Calculating')
                        time.sleep(0.5)
                        progress_bar.empty() 
                    
                    calculate_button = False
                    
                    col1_p, col2_p = st.columns(2)
                    with col1_p:
                        if portfolio_bool == 'Strategy':
                            prob_strat = strategy_set[[strategy]]
                            prob_strat.columns =  [str(strategy)]

                        elif portfolio_bool == 'Portfolio':
                            prob_strat = port.copy()
                        
                        prob_strat= prob_strat.reset_index().rename(columns={'index': 'Date'})
                        fig_ps = px.line(prob_strat, x='Date', y=prob_strat.columns, hover_data={'Date': "|%B %d, %Y"},title='Strategy')    
                        fig_ps.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                            rangeselector = dict(
                                            buttons=list([
                                            dict(count=1, label="1m", step="month", stepmode="backward"),
                                            dict(count=6, label="6m", step="month", stepmode="backward"),
                                            dict(count=1, label="YTD", step="year", stepmode="todate"),
                                            dict(count=1, label="1y", step="year", stepmode="backward"),
                                            dict(step="all")])))
                        st.plotly_chart(fig_ps, use_container_width=True)

                    with col2_p:
                        prob = pd.concat([prob_dist, prob_quad], axis=1, sort=True)
                        prob.columns = [c.replace('_', " ") for c in prob.columns]
                        prob['Diveregence Probability Average'] = prob.mean(axis=1)
                        prob = prob.reset_index().rename(columns={'index': 'Date'})

                        fig_prob = px.line(prob, x='Date', y=prob.columns, hover_data={'Date': "|%B %d, %Y"},title='Divergence Probability')    
                        fig_prob.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                            rangeselector = dict(
                                            buttons=list([
                                            dict(count=1, label="1m", step="month", stepmode="backward"),
                                            dict(count=6, label="6m", step="month", stepmode="backward"),
                                            dict(count=1, label="YTD", step="year", stepmode="todate"),
                                            dict(count=1, label="1y", step="year", stepmode="backward"),
                                            dict(step="all")])))
                        st.plotly_chart(fig_prob, use_container_width=True)

            st.divider()
            st.markdown('**Correlation Analysis**')
            col_r_1, cor_r_2 = st.columns(2)
            with col_r_1:
                colr_r_1_, colr_r_2_ = st.columns(2)
                with colr_r_1_:
                    corr_start_dt = datetime.strftime(st.date_input('Correlation Calculation Start', date(2022,1,1)), '%Y-%m-%d')
                    
                with colr_r_2_:
                    corr_end_dt = datetime.strftime(st.date_input('Correlation Calculation End'), '%Y-%m-%d')

            strategy_selected_corr = strategy_data[st.session_state.strats+strategy_list_macrofactor]
            strategy_selected_corr = strategy_selected_corr/strategy_selected_corr.shift(1)-1
            strategy_selected_corr = strategy_selected_corr[(strategy_selected_corr.index<=corr_end_dt)&(strategy_selected_corr.index>=corr_start_dt)]
            strategy_selected_corr.columns = [str(x) for x in strategy_selected_corr.columns]
            st.dataframe(strategy_selected_corr.corr().style.background_gradient(cmap='RdBu'), height = 650)
            st.divider()

        with tab5:
            with st.container():
                vyc_df, vkyc_df = rd.mf.vix_yc()
                vkyc_df['Month'] = vkyc_df.index.year.astype(str) +"."+ vkyc_df.index.month.astype(str)
                vkyc_df_m = vkyc_df.resample('M').last()
                vkyc_df_m['Country'] = 'Korea'
                vkyc_df_m_c = vkyc_df_m.reset_index()[['Month', 'YC', 'Vol', 'Country']].dropna()

                vyc_df['Month'] = vyc_df.index.year.astype(str) +"."+ vyc_df.index.month.astype(str)
                vyc_df_m = vyc_df.resample('M').last()
                vyc_df_m['Country'] = 'US'
                vyc_df_m_c  = vyc_df_m.reset_index()[['Month', 'YC', 'Vol', 'Country']].dropna()

                vxy_yc = pd.concat([vkyc_df_m_c, vyc_df_m_c], axis=0)

                fig_vyc = px.line(vxy_yc, x="Vol", y="YC", color="Country", text="Month", title='Volatility-YC Map')
                fig_vyc.update_traces(textposition="bottom right")
                fig_vyc.update_layout(height=800)
                st.plotly_chart(fig_vyc, use_container_width=True, height=800)
            
            st.divider()
           
            with st.container():
                vol_q = "SELECT CLPR_DATE, TCKR, CLPR FROM macrodb.tb_mcro_clpr WHERE (TCKR = 'VIX Index' OR TCKR = 'MOVE Index' OR TCKR = 'OVX Index' OR TCKR = 'USDJPYV1M Curncy');"
                vol = mapdp.dbm_m_.get_fetchall(vol_q)
                vol_df = pd.DataFrame([list(x) for x in vol], columns=['Date', 'Ticker', 'Index'])
                vol_df = vol_df.pivot_table(index='Date', columns='Ticker', values='Index')
                vol_df.columns.name = None
                vol_df = vol_df.fillna(method='ffill')
                #vol_df = (vol_df - vol_df.mean())/vol_df.std()
                #vol_df.index = pd.DatetimeIndex(vol_df.index)
                vol_df_m = vol_df.reset_index()
                
                fig_vol = go.Figure()
                fig_vol.add_trace(go.Scatter(x=vol_df_m['Date'], y=vol_df_m[vol_df_m.columns[1]], name='SPX Vol', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                fig_vol.add_trace(go.Scatter(x=vol_df_m['Date'], y=vol_df_m[vol_df_m.columns[2]], name='UST Vol', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                fig_vol.add_trace(go.Scatter(x=vol_df_m['Date'], y=vol_df_m[vol_df_m.columns[3]], name='Oil Vol', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                fig_vol.add_trace(go.Scatter(x=vol_df_m['Date'], y=vol_df_m[vol_df_m.columns[4]], name='JPY Vol', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                fig_vol.update_layout(xaxis=dict(domain=[0.05, 0.93]),
                                    yaxis2=dict(anchor="x",overlaying="y",side="right", position=0.95),
                                    yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.97),
                                    yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                fig_vol.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")]))) 
                st.write("**Volatility**")
                st.plotly_chart(fig_vol, use_container_width=True, height=1200)

#rm.cumulative_return_divergence_probability(('1Y_IRS_TR', '3Y_IRS_TR'), '2012-12-31', '2023-07-03', '2023-07-03', '2023-07-03', 500, True)