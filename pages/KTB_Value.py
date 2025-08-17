file_dir = 'C:\\Users\\kimju\\MPT-Quant\\MacroTrading'
css_dir = 'C:\\Users\\kimju\\MPT-Quant\\SystemMacro_App\\pages\\style.css'

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from datetime import date
import pandas as pd
import numpy as np
import sys
sys.path.append(file_dir)
#from Feature_Preprocessing import RatesData, RatesDataProcess
from Strategy_MA_Optimal_Portfolio import MultiAssetPortDataProcess
from Strategy_KTB_Optimal_Portfolio import HedgePosition
from Strategy_KTB_Optimal_Portfolio import HedgeTrade
from Strategy_KTB_Optimal_Portfolio import ExpectedReturn
from MPTSRT_StratDB import db_execute_manager as dbm_s
#dbm = dbm_s.DBExecuteManager()

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
def pull_strategy_data_series(_dp):
    strategy = _dp.strategy_cc
    strategy_tr = _dp.strategy_cc_tr
    strategy_outright = pd.concat([_dp.ktb, _dp.swap, _dp.ktbf, _dp.ktbi, _dp.ustf, _dp.bund], axis=1, sort=True).fillna(method='ffill')
    strategy_outright_tr = (1+pd.concat([_dp.ktb_tr, _dp.swap_tr, _dp.ktbf_tr, _dp.ustf_tr, _dp.bund_tr], axis=1, sort=True).fillna(method='ffill')).cumprod()
    strategy_outright_tr = strategy_outright_tr/strategy_outright_tr.shift(1)-1
    return strategy, strategy_tr, strategy_outright, strategy_outright_tr

def get_strategy_name(options):
    if len(options) == 1:
        t_1 = options[0]
        strategy_selected = t_1
        strategy_selected_tr = t_1+"_TR"

    elif len(options) == 2:
        t_1 = options[0]
        t_2 = options[1]
        for s in list(strategy.keys()):
            if len(s) == len(options) and t_1 in s and t_2 in s:
                strategy_selected = s
                strategy_selected_tr = tuple([s_+"_TR" for s_ in strategy_selected])
                break
        
    elif len(options) == 3:
        t_1 = options[0]
        t_2 = options[1]
        t_3 = options[2]
        
        for s in list(strategy.keys()):
            if len(s) == len(options) and t_1 in s and t_2 in s and t_3 in s:
                strategy_selected = s
                strategy_selected_tr = tuple([s_+"_TR" for s_ in strategy_selected])
                break

    return strategy_selected, strategy_selected_tr

def get_strategy(options):
    if len(options) == 1:
        t_1 = options[0]
        strategy_selected = tuple([t_1])
        strategy_selected_series = strategy_outright[t_1]
        strategy_selected_series_tr = strategy_outright_tr[t_1+"_TR"]

    elif len(options) == 2:
        t_1 = options[0]
        t_2 = options[1]
        for s in list(strategy.keys()):
            if len(s) == len(options) and t_1 in s and t_2 in s:
                strategy_selected = s
                strategy_selected_tr = tuple([s_+"_TR" for s_ in strategy_selected])
                break
        
        strategy_selected_series = strategy[strategy_selected]
        strategy_selected_series_tr = strategy_tr[strategy_selected_tr]
        
    elif len(options) == 3:
        t_1 = options[0]
        t_2 = options[1]
        t_3 = options[2]
        
        for s in list(strategy.keys()):
            if len(s) == len(options) and t_1 in s and t_2 in s and t_3 in s:
                strategy_selected = s
                strategy_selected_tr = tuple([s_+"_TR" for s_ in strategy_selected])
                break
        
        strategy_selected_series = strategy[strategy_selected]
        strategy_selected_series_tr = strategy_tr[strategy_selected_tr]

    return strategy_selected, strategy_selected_series, strategy_selected_series_tr

@st.cache_data(show_spinner=False)
def get_value_regime_data():
    dbm = dbm_s.DBExecuteManager()
    value_regime_q = 'SELECT DATE, REGM FROM preprocessdb.tb_scnd_ktb_valu_regm WHERE REGM_TYPE = "Market Breadth";'
    value_regime_df = pd.DataFrame(dbm.get_fetchall(value_regime_q), columns = ['Date', 'Market_Breadth'])
    return value_regime_df

@st.cache_data(show_spinner=False)
def get_value_distinct_date():
    dbm = dbm_s.DBExecuteManager()
    q = "SELECT DISTINCT RCD_DATE FROM stratdb.tb_scnd_ktb_valu;"
    dt_list = dbm.get_fetchall(q)
    dt_list = [d[0] for d in dt_list]
    dt_list = sorted(dt_list)[::-1]
    return dt_list

@st.cache_data(show_spinner=False)
def get_value_scores():
    dbm = dbm_s.DBExecuteManager()
    score_q = "SELECT RCD_DATE, TENR_1, TENR_2, TENR_3, AGG_Z, OPT_Z, PCA_Z, FUND_Z, FUND_CONF, CARY, TRGT, TRGT_SMPL, DRDN, DRDN_SMPL, VOL_TRD_SHRT, VOL_TRD_MID, VOL_TRD_LONG FROM stratdb.tb_scnd_ktb_valu"
    score_df = dbm.get_fetchall(score_q)
    score_df = pd.DataFrame(score_df, columns=['Date', 'Tenor 1', 'Tenor 2', 'Tenor 3', 'Aggregate Z', 'Optimal Z', 'PCA Z', 'Funda Z', 'Funda Conf.', 'Carry', 'Target', 'Target Sample', 'Drawdown', 'Drawdown Sample', 'Sharpe Short', 'Sharpe Mid', 'Sharpe Long'])
    return score_df

@st.cache_resource(show_spinner=False)
def get_value_modules(_dp):
    hp = HedgePosition('2012-10-01', date.today().isoformat(), _dp)
    ht = HedgeTrade(mapdp, hp)
    er = ExpectedReturn('2012-10-01', date.today().isoformat(), dp=_dp)
    return hp, ht, er

#데이터 불러오기
with st.spinner("Querying Data, Will take about 2 minutes, Please Wait..."):
    if 'mapdp' not in st.session_state:
        mapdp = pull_strategy_data()
        st.session_state.mapdp = mapdp
    else:
        mapdp = st.session_state.mapdp
    dp = mapdp.dp
    #hp = HedgePosition('2012-10-01', date.today().isoformat(), dp)
    #ht = HedgeTrade(mapdp, hp)
    #er = ExpectedReturn('2012-10-01', date.today().isoformat(), dp=dp)
    hp, ht, er = get_value_modules(dp)
    value_regime_df = get_value_regime_data()
    value_regime_df = value_regime_df.set_index('Date')
    dt_list = get_value_distinct_date()
    score_df_whole = get_value_scores()
    #전략리스트
    ktb = ['1Y_KTB', '2Y_KTB','3Y_KTB','4Y_KTB','5Y_KTB','7Y_KTB','10Y_KTB','20Y_KTB','30Y_KTB', 'IL10Y_KTB', 'BE10Y_KTB', '3Y_FUT', '10Y_FUT']
    swap = ['9M_IRS', '1Y_IRS', '18M_IRS','2Y_IRS','3Y_IRS','4Y_IRS','5Y_IRS','7Y_IRS','10Y_IRS']
    foreign = ['2Y_FUT_US', '5Y_FUT_US', '10Y_FUT_US', '30Y_FUT_US','2Y_FUT_GER', '5Y_FUT_GER', '10Y_FUT_GER'] 
    outright_list = ktb+swap+foreign
    #가격데이터
    strategy, strategy_tr, strategy_outright, strategy_outright_tr = pull_strategy_data_series(dp)

with st.container():
    tab1, tab2, tab3, tab4, tab5 = st.tabs(['Score', 'Technical', 'Hedge Position', 'Hedge Trade', 'Regime'])

    with open(css_dir) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

    with tab1:
        with st.container():
            #q = "SELECT DISTINCT RCD_DATE FROM stratdb.tb_scnd_ktb_valu;"
            #dt_list = dbm.get_fetchall(q)
            #dt_list = [d[0] for d in dt_list]
            #dt_list = sorted(dt_list)[::-1]
            
            col1, col2 = st.columns(2)
            with col1:
                date_selected = st.selectbox('Select date below', dt_list)
            with col2:
                ktbi = st.selectbox('Include KTBI', [True, False])

            #dbm = dbm_s.DBExecuteManager()
            #score_q = "SELECT TENR_1, TENR_2, TENR_3, AGG_Z, OPT_Z, PCA_Z, FUND_Z, FUND_CONF, CARY, TRGT, TRGT_SMPL, DRDN, DRDN_SMPL, VOL_TRD_SHRT, VOL_TRD_MID, VOL_TRD_LONG FROM stratdb.tb_scnd_ktb_valu WHERE DATE_FORMAT(STR_TO_DATE(RCD_DATE, '%Y-%m-%d'),'%Y-%m-%d') = DATE_FORMAT(STR_TO_DATE('{}', '%Y-%m-%d'),'%Y-%m-%d')".format(date_selected)
            #score_df = dbm.get_fetchall(score_q)
            #score_df = pd.DataFrame(score_df, columns=['Tenor 1', 'Tenor 2', 'Tenor 3', 'Aggregate Z', 'Optimal Z', 'PCA Z', 'Funda Z', 'Funda Conf.', 'Carry', 'Target', 'Target Sample', 'Drawdown', 'Drawdown Sample', 'Sharpe Short', 'Sharpe Mid', 'Sharpe Long']).sort_values(by='Aggregate Z').set_index('Tenor 1').reset_index()
            score_df = score_df_whole[score_df_whole['Date']==date_selected]
            score_df = score_df[['Tenor 1', 'Tenor 2', 'Tenor 3', 'Aggregate Z', 'Optimal Z', 'PCA Z', 'Funda Z', 'Funda Conf.', 'Carry', 'Target', 'Target Sample', 'Drawdown', 'Drawdown Sample', 'Sharpe Short', 'Sharpe Mid', 'Sharpe Long']].sort_values(by='Aggregate Z').set_index('Tenor 1').reset_index()
            if ktbi:
                st.dataframe(score_df, hide_index=True, height=900, column_config={"widgets": st.column_config.Column(width='large')})
            else:
                score_df = score_df[(score_df['Tenor 1']!='IL10Y_KTB')&(score_df['Tenor 2']!='IL10Y_KTB')&(score_df['Tenor 3']!='IL10Y_KTB')]
                st.dataframe(score_df, hide_index=True, height=900, column_config={"widgets": st.column_config.Column(width='large')})

            st.download_button(label="Download data as CSV",data= convert_df(score_df),file_name='KTB_Value_{}.csv'.format(date_selected), mime='text/csv')
        
    with tab2:
        col1, col2, col3 = st.columns(3)
        with col1:
            option_1 = st.multiselect('First Strategy', outright_list, default=None, max_selections=3)
        with col2: 
            option_2 = st.multiselect('Second Strategy', outright_list, default=None, max_selections=3)
        with col3:
            option_3 = st.multiselect('Third Strategy', outright_list, default=None, max_selections=3)
        
        strategy_selected = []
        strategy_series_to_chart = {}
        strategy_series_tr_to_chart = {}
        if len(option_1) > 0:
            strategy_selected_1, strategy_selected_series_1, strategy_selected_series_tr_1 = get_strategy(option_1)
            strategy_selected_series_tr_1 = (1+strategy_selected_series_tr_1).cumprod()
            strategy_selected.append(strategy_selected_1)
            strategy_series_to_chart[strategy_selected_1] = strategy_selected_series_1
            strategy_series_tr_to_chart[strategy_selected_1] = strategy_selected_series_tr_1
        if len(option_2) > 0:
            strategy_selected_2, strategy_selected_series_2, strategy_selected_series_tr_2 = get_strategy(option_2)
            strategy_selected_series_tr_2 = (1+strategy_selected_series_tr_2).cumprod()
            strategy_selected.append(strategy_selected_2)
            strategy_series_to_chart[strategy_selected_2] = strategy_selected_series_2
            strategy_series_tr_to_chart[strategy_selected_2] = strategy_selected_series_tr_2
            
        if len(option_3) > 0:
            strategy_selected_3, strategy_selected_series_3, strategy_selected_series_tr_3 = get_strategy(option_3)
            strategy_selected_series_tr_3 = (1+strategy_selected_series_tr_3).cumprod()
            strategy_selected.append(strategy_selected_3)
            strategy_series_to_chart[strategy_selected_3] = strategy_selected_series_3
            strategy_series_tr_to_chart[strategy_selected_3] = strategy_selected_series_tr_3
            
        if len(strategy_selected)>0:
            strategy_series_to_chart_df = pd.DataFrame(strategy_series_to_chart).fillna(method='ffill')
            strategy_series_tr_to_chart_df = pd.DataFrame(strategy_series_tr_to_chart).fillna(method='ffill')
            strategy_series_to_chart_df.columns = [str(c) for c in strategy_selected]
            strategy_series_tr_to_chart_df.columns = [str(c) for c in strategy_selected]
            
            with st.container():
                strategy_series_to_chart_df_ = strategy_series_to_chart_df.reset_index()
                strategy_series_to_chart_df_ = strategy_series_to_chart_df_.rename(columns={'index':'date'})

                fig = px.line(strategy_series_to_chart_df_, x='date', y=strategy_series_to_chart_df_.columns,hover_data={'date': "|%B %d, %Y"},title='Strategy in bp')    
                fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                st.plotly_chart(fig, use_container_width=True)

            with st.expander('Scale Adjusted'):
                if len(strategy_selected) == 1:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_to_chart_df_['date'], y=strategy_series_to_chart_df_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]))
                elif len(strategy_selected) == 2:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_to_chart_df_['date'], y=strategy_series_to_chart_df_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_to_chart_df_['date'], y=strategy_series_to_chart_df_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.update_layout(xaxis=dict(domain=[0.1, 0.9]),
                                       yaxis2=dict(anchor="x",overlaying="y",side="right"))
                elif len(strategy_selected) == 3:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_to_chart_df_['date'], y=strategy_series_to_chart_df_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_to_chart_df_['date'], y=strategy_series_to_chart_df_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_to_chart_df_['date'], y=strategy_series_to_chart_df_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                       yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                       yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))
                fig_.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                
                st.plotly_chart(fig_, use_container_width=True)

            with st.container():
                strategy_series_tr_to_chart_df_ = strategy_series_tr_to_chart_df.reset_index()
                strategy_series_tr_to_chart_df_ = strategy_series_tr_to_chart_df_.rename(columns={'Date':'date'})
                
                fig = px.line(strategy_series_tr_to_chart_df_, x='date', y=strategy_series_tr_to_chart_df_.columns,hover_data={'date': "|%B %d, %Y"},title='Strategy in %')    
                fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                
                st.plotly_chart(fig, use_container_width=True)

            with st.expander('Scale Adjusted'):
                if len(strategy_selected) == 1:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_['date'], y=strategy_series_tr_to_chart_df_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines'))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]))
                elif len(strategy_selected) == 2:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_['date'], y=strategy_series_tr_to_chart_df_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_['date'], y=strategy_series_tr_to_chart_df_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', yaxis="y2"))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                       yaxis2=dict(anchor="x",overlaying="y",side="right"))
                elif len(strategy_selected) == 3:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_['date'], y=strategy_series_tr_to_chart_df_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_['date'], y=strategy_series_tr_to_chart_df_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_['date'], y=strategy_series_tr_to_chart_df_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                       yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                       yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))
                fig_.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                
                st.plotly_chart(fig_, use_container_width=True)
            
            with st.container():
                strategy_selected_vol = [s for s in strategy_selected if len(s)>1]
                if len(strategy_selected_vol)>0:
                    for i, strat in enumerate(strategy_selected_vol):
                        if i == 0:
                            strategy_vol_trade_to_chart_df = ht.strategy_expected_capital_vol_trading_single(strat)
                            strategy_vol_trade_to_chart_df.columns = [str(strat)]
                        else:
                            strategy_vol_trade_to_chart_df_ = ht.strategy_expected_capital_vol_trading_single(strat)
                            strategy_vol_trade_to_chart_df_.columns = [str(strat)]
                            strategy_vol_trade_to_chart_df = pd.concat([strategy_vol_trade_to_chart_df, strategy_vol_trade_to_chart_df_], axis=1, sort=True).fillna(method='ffill')

                    strategy_vol_trade_to_chart_df = strategy_vol_trade_to_chart_df.reset_index().rename(columns={'Date':'date'}).fillna(1)
                    
                    fig = px.line(strategy_vol_trade_to_chart_df, x='date', y=strategy_vol_trade_to_chart_df.columns,hover_data={'date': "|%B %d, %Y"},title='Strategy with Trading')    
                    fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig, use_container_width=True)

                    with st.expander('Scale Adjusted'):
                        if len(strategy_selected_vol) == 1:
                            fig_ = go.Figure()
                            fig_.add_trace(go.Scatter(x=strategy_vol_trade_to_chart_df['date'], y=strategy_vol_trade_to_chart_df[[str(c) for c in strategy_selected_vol][0]], name=[str(c) for c in strategy_selected_vol][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                            fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]))
                        elif len(strategy_selected_vol) == 2:
                            fig_ = go.Figure()
                            fig_.add_trace(go.Scatter(x=strategy_vol_trade_to_chart_df['date'], y=strategy_vol_trade_to_chart_df[[str(c) for c in strategy_selected_vol][0]], name=[str(c) for c in strategy_selected_vol][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                            fig_.add_trace(go.Scatter(x=strategy_vol_trade_to_chart_df['date'], y=strategy_vol_trade_to_chart_df[[str(c) for c in strategy_selected_vol][1]], name=[str(c) for c in strategy_selected_vol][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                            fig_.update_layout(xaxis=dict(domain=[0.1, 0.9]),
                                            yaxis2=dict(anchor="x",overlaying="y",side="right"))
                        elif len(strategy_selected_vol) == 3:
                            fig_ = go.Figure()
                            fig_.add_trace(go.Scatter(x=strategy_vol_trade_to_chart_df['date'], y=strategy_vol_trade_to_chart_df[[str(c) for c in strategy_selected_vol][0]], name=[str(c) for c in strategy_selected_vol][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                            fig_.add_trace(go.Scatter(x=strategy_vol_trade_to_chart_df['date'], y=strategy_vol_trade_to_chart_df[[str(c) for c in strategy_selected_vol][1]], name=[str(c) for c in strategy_selected_vol][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                            fig_.add_trace(go.Scatter(x=strategy_vol_trade_to_chart_df['date'], y=strategy_vol_trade_to_chart_df[[str(c) for c in strategy_selected_vol][2]], name=[str(c) for c in strategy_selected_vol][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                            fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                            yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                            yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))
                        fig_.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                            rangeselector = dict(
                                            buttons=list([
                                            dict(count=1, label="1m", step="month", stepmode="backward"),
                                            dict(count=6, label="6m", step="month", stepmode="backward"),
                                            dict(count=1, label="YTD", step="year", stepmode="todate"),
                                            dict(count=1, label="1y", step="year", stepmode="backward"),
                                            dict(step="all")])))
                        
                        st.plotly_chart(fig_, use_container_width=True)
                    st.download_button(label="Download data as CSV",data= convert_df(pd.concat([strategy_series_to_chart_df_.set_index('date'), strategy_series_tr_to_chart_df_.set_index('date'), strategy_vol_trade_to_chart_df.set_index('date')], axis=1, sort=True)),file_name='KTB_Strat_{}.csv'.format(date_selected), mime='text/csv')
                else:
                    st.download_button(label="Download data as CSV",data= convert_df(pd.concat([strategy_series_to_chart_df_.set_index('date'), strategy_series_tr_to_chart_df_.set_index('date')], axis=1, sort=True)),file_name='KTB_Strat_{}.csv'.format(date_selected), mime='text/csv')

            st.divider()
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat = st.selectbox('Strategy Selected', strategy_selected)
                with col2:
                    col2_1, col2_2, col2_3 = st.columns(3)
                    with col2_1:
                        optz = st.number_input('Optimal', 0.0, 1.0, step=0.05)
                    with col2_2:
                        pcaz = st.number_input('PCA', 0.0, 1.0, step=0.05)
                    with col2_3:
                        fundaz = st.number_input('Fundamental', 0.0, 1.0, step=0.05)
                with col3:
                    col3_1, col3_2, col3_3 = st.columns(3)
                    with col3_1:
                        lf = st.number_input('Lookforward', 0,1000, step=1)
                    with col3_2:
                        lt = st.number_input('Lower Threshold', -10.0,10.0, step=0.01)
                    with col3_3:
                        ut = st.number_input('Upper Threshold', -10.0,10.0, step=0.01)
            
                if optz+pcaz+fundaz>0 and lf >0 and lt<ut:
                    chart_data, past_data = er.trading_assessment(strat, [optz,pcaz,fundaz], lf, lt, ut)
                    chart_data.index.name = 'Date'
                    chart_data = chart_data.reset_index('Date')
                    #st.dataframe(chart_data, height = 900, use_container_width=True)
                    
                    fig_z = go.Figure()
                    fig_z.add_trace(go.Scatter(x=chart_data['Date'], y=chart_data['Z score'], name='Z score', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_z.add_trace(go.Scatter(x=chart_data['Date'], y=chart_data['Strategy'], name=str(strat), mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_z.update_layout(xaxis=dict(domain=[0.1, 0.9]),
                                    yaxis2=dict(anchor="x",overlaying="y",side="right"))
                    
                    st.plotly_chart(fig_z, use_container_width=True)  

                    st.dataframe(past_data, height = 900, use_container_width=True)
                    st.download_button(label="Download data as CSV",data= convert_df(past_data),file_name='KTB_Value_Data_{}.csv'.format(strat), mime='text/csv')

            st.divider()

    with tab3:
        similar_regime_list = [False, True]
        unlikely_regime_list = [None, 'Bull_Steep', 'Bull_Flat', 'Bear_Steep', 'Bear_Flat']
        all_regime_list = [False, True]
        regime_curve_degree = [False, True]
        regime_direction_degree = [False, True]

        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                col1_, col2_ = st.columns(2)
                with col1_:
                    start_dt = datetime.strftime(st.date_input('Regime Calculation Start', date(2023, 1, 2)), '%Y-%m-%d')
                with col2_:
                    end_dt = datetime.strftime(st.date_input('Regime Calculation End'), '%Y-%m-%d')
    
            with col2:
                all_regime = True if st.selectbox('Remove Regime', all_regime_list) == False else False

            with col3:
                regime_curve_degree = st.selectbox('Curve Extreme', regime_curve_degree)
                
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                similar_regime = st.selectbox('Distance Regime', similar_regime_list)

            with col2:
                unlikely_regime = st.selectbox('Unlikely Regime', unlikely_regime_list)

            with col3:
                regime_direction_degree = st.selectbox('Direction Extreme', regime_direction_degree)
        
        st.divider()

        position = {}
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                strat_ = st.multiselect('Strategy', outright_list, default=None, max_selections=3)
                if len(strat_)==1:
                    st.write('Choose at least 2 tenors!')
                
            with col2:
                delta = st.number_input('Absolute Delta', step=100)
                
            with col3:
                direction = st.selectbox('Trade Direction', [1, -1])

                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
                
        with st.expander('Add Strategy'):
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('Strategy ', outright_list, default=None, max_selections=3)
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('Absolute Delta ', step=100)
                
                with col3:
                    direction = st.selectbox('Trade Direction ', [1, -1])
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect(' ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input(' ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox(' ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('  ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('  ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('  ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('   ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('   ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('   ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('    ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('    ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('    ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]

            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('     ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('     ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('     ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]

            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('      ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('      ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('      ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('       ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('       ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('       ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('        ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('        ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('        ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('         ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('         ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('         ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('          ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('          ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('          ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('           ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('           ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('           ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]

            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('            ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('            ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('            ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    strat_ = st.multiselect('             ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    delta = st.number_input('             ', step=100, label_visibility='collapsed')
                
                with col3:
                    direction = st.selectbox('             ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    strat = get_strategy_name(strat_)[0]
                    position[strat] = [delta, direction]
        
        st.divider()
        
        @st.cache_resource(show_spinner=False)
        def quad_regime_calc(position, start_dt, end_dt, similar_regime, unlikely_regime, all_regime, regime_direction_degree,regime_curve_degree):
            with st.spinner("Processing, Please Wait..."):
                strategy_regime, sim_hist_dict, regime_prob, quad_regime_hedge_equal_weight, quad_regime_hedge_prob_weight = hp.quad_regime_hedge_portfolio(position, start_dt, end_dt, similar_regime = similar_regime, unlikely_regime = unlikely_regime, all_regime=all_regime, regime_direction_degree=regime_direction_degree, regime_curve_degree=regime_curve_degree)
            return strategy_regime, sim_hist_dict, regime_prob, quad_regime_hedge_equal_weight, quad_regime_hedge_prob_weight
        
        placeholder = st.empty()
        start_button = placeholder.button('Calculate')
        
        if start_button:
            placeholder.empty()
            strategy_regime, sim_hist_dict, regime_prob, quad_regime_hedge_equal_weight, quad_regime_hedge_prob_weight = quad_regime_calc(position, start_dt, end_dt, similar_regime, unlikely_regime, all_regime, regime_direction_degree, regime_curve_degree)
            quad_regime_hedge_equal_weight.index = [str(i) for i in quad_regime_hedge_equal_weight.index]
            quad_regime_hedge_prob_weight.index = [str(i) for i in quad_regime_hedge_prob_weight.index]

            with st.container():
                col1, col2  = st.columns(2)
                with col1:
                    st.markdown('**Portfolio Performance**')
                    st.dataframe(strategy_regime, use_container_width=True)
                with col2:
                    st.markdown('**Regime Probability**')
                    st.dataframe(regime_prob)

            with st.container():
                st.markdown('**Equal Weight Sharpe**')
                quad_regime_hedge_equal_weight = pd.concat([quad_regime_hedge_equal_weight[(quad_regime_hedge_equal_weight['Z']==0)], quad_regime_hedge_equal_weight[(np.sign(quad_regime_hedge_equal_weight['Z'])==np.sign(quad_regime_hedge_equal_weight['Hedge_Direction']))]], axis=0).sort_values(by='Sharpe', ascending=False)
                st.dataframe(quad_regime_hedge_equal_weight, use_container_width=True)
                st.markdown('**Probability Weight Sharpe**')
                quad_regime_hedge_prob_weight = pd.concat([quad_regime_hedge_prob_weight[(quad_regime_hedge_prob_weight['Z']==0)], quad_regime_hedge_prob_weight[(np.sign(quad_regime_hedge_prob_weight['Z'])==np.sign(quad_regime_hedge_prob_weight['Hedge_Direction']))]], axis=0).sort_values(by='Sharpe', ascending=False)
                st.dataframe(quad_regime_hedge_prob_weight, use_container_width=True)
                st.write('')
                st.download_button(label="Download EqW data as CSV",data= convert_df(quad_regime_hedge_equal_weight),file_name='EqualWeight_Hedge_{}.csv'.format(date.today().isoformat()), mime='text/csv')
                st.download_button(label="Download PrW data as CSV",data= convert_df(quad_regime_hedge_prob_weight),file_name='ProbWeight_Hedge_{}.csv'.format(date.today().isoformat()), mime='text/csv')
    
    with tab4:
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                col1_, col2_, col3_ = st.columns(3)
                with col1_:
                    ht_start_dt = datetime.strftime(st.date_input('Statistics Start', date(2023, 1, 2)), '%Y-%m-%d')
                with col2_:
                    ht_end_dt = datetime.strftime(st.date_input('Statistics End'), '%Y-%m-%d')
                with col3_:
                    ht_search_dt = datetime.strftime(st.date_input('Search Date'), '%Y-%m-%d')
    
            with col2:
                col1_, col2_ = st.columns(2)
                with col1_:
                    ht_future_tenor = st.selectbox('Future Tenor', ('3Y_FUT', '10Y_FUT'))
                with col2_:
                    ht_portfolio_bool_ = st.radio("Type", ['Strategy', 'Portfolio'])
                    if ht_portfolio_bool_ == 'Portfolio':
                        ht_portfolio_bool = True
                    else:
                        ht_portfolio_bool = False

        st.divider()

        ht_position = {}
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                ht_strat_ = st.multiselect('Strategy  ', outright_list, default=None, max_selections=3)
                if len(ht_strat_)==1:
                    st.write('Choose at least 2 tenors!')
                
            with col2:
                ht_delta = st.number_input('Absolute Delta  ', step=100)
                
            with col3:
                ht_direction = st.selectbox('Trade Direction  ', [1, -1])

                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
                
        with st.expander('Add Strategy'):
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('Strategy   ', outright_list, default=None, max_selections=3)
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('Absolute Delta   ', step=100)
                
                with col3:
                    ht_direction = st.selectbox('Trade Direction   ', [1, -1])
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1  ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1  ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1  ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1   ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1   ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1   ', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1    ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1    ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1    ', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]

            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1     ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1     ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1     ', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]

            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1      ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1      ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1      ', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1       ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1       ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1       ', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1        ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1        ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1        ', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1         ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1         ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1         ', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1          ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1          ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1          ', [1, -1], label_visibility='collapsed')
                
                if len(strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1           ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1           ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1           ', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]

            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1            ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1            ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1            ', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
            
            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ht_strat_ = st.multiselect('s1             ', outright_list, default=None, max_selections=3, label_visibility='collapsed')
                    if len(ht_strat_)==1:
                        st.write('Choose at least 2 tenors!')

                with col2:
                    ht_delta = st.number_input('d1             ', step=100, label_visibility='collapsed')
                
                with col3:
                    ht_direction = st.selectbox('di1             ', [1, -1], label_visibility='collapsed')
                
                if len(ht_strat_) >0:
                    ht_strat = get_strategy_name(ht_strat_)[0]
                    ht_position[ht_strat] = [ht_delta, ht_direction]
        
        st.divider()
        if len(ht_position)>0 and len([1 for x in list(ht_position.keys()) if len(x)>1 and type(x)!=str]) == len(list(ht_position.keys())):
            ht_beta = ht.calc_beta_quad_regime(ht_start_dt, ht_end_dt, ht_position, ht_portfolio_bool, ht_future_tenor)
            ht_beta_df = pd.DataFrame(ht_beta, columns=list(ht_beta.keys()), index=['All', 'Bull Steep', 'Bull Flat', 'Bear Steep', 'Bear Flat'])
            _, strategy_beta, _, _, _, _, _, strategy_regression_fitness, delta_regression_fitness = ht.calc_decomposition(ht_start_dt, ht_end_dt, ht_position, ht_portfolio_bool)
            
            if ht_portfolio_bool == True:
                strat_name = 'Portfolio'
            else:
                strat_name = list(ht_position.keys())[0]

            with st.container():
                col1_t, col2_t, col3_t = st.columns(3)
                with col1_t:
                    strategy_change_ = st.number_input('Strategy Change in bp')
                    strategy_change = strategy_change_/100
                with col2_t:
                    delta_change_ = st.number_input('Delta Change in bp')
                    delta_change = delta_change_/100
                with col3_t:
                    curve_change_ = st.number_input('Curve Change in bp')
                    curve_change = curve_change_/100
            
            curve_decomp, curve_decomp_name, _, _ = ht.today_strat_estimate(ht_start_dt, ht_end_dt, ht_search_dt, ht_position, ht_portfolio_bool, strat_name, strategy_change, delta_change, curve_change)
            curve_decomp_df = pd.DataFrame(curve_decomp, index=curve_decomp_name).T
            st.table(pd.DataFrame(curve_decomp, index=curve_decomp_name).T)
            
            st.divider()
            with st.container():
                col1_df, col2_df = st.columns(2)
                with col1_df:        
                    st.markdown('**Simple Regression Beta**')
                    ht_beta_df.index.name = 'Regime'
                    st.dataframe(ht_beta_df[[strat_name]], use_container_width=True)
                with col2_df:
                    st.markdown('**Multivariate Regression Beta**')
                    multi_var_beta = pd.DataFrame(strategy_beta[strat_name])
                    multi_var_beta = multi_var_beta[[0,2]].rename(columns={2:strat_name})
                    multi_var_beta = multi_var_beta.set_index(0)
                    multi_var_beta.index.name = 'Regime'
                    st.dataframe(multi_var_beta, use_container_width=True)
            
            with st.container():
                col1_df, col2_df = st.columns(2)
                with col1_df:        
                    st.markdown('**Strategy Beta Goodness of Fit**')
                    st.dataframe(pd.DataFrame(strategy_regression_fitness[strat_name], columns=['Regime', 'R-Squared', 'P-Val']).set_index('Regime'), use_container_width=True)
                with col2_df:
                    st.markdown('**Delta Beta Goodness of Fit**')
                    st.dataframe(pd.DataFrame(delta_regression_fitness[strat_name], columns=['Regime', 'R-Squared', 'P-Val']).set_index('Regime'), use_container_width=True)

            with st.container():
                if ht_portfolio_bool != True:
                    beta, optz = ht.beta_multiplier(ht_search_dt, strat_name)
                    optz = optz[['Aggregate Z', 'Multiplier']].dropna()
                    optz = optz.reset_index('Date')
                    st.markdown('**Beta Multiplier: {}**'.format(np.round(beta, 4)))
                    
                    fig = px.line(optz, x='Date', y=optz.columns, hover_data={"Date": "|%B %d, %Y"})
                    fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
                    st.plotly_chart(fig, use_container_width=True)
                        #st.line_chart(optz, use_container_width=True)

                else:
                    whole_position = sum([v[0] for k, v in ht_position.items()])
                    for i in range(len(list(ht_position.keys()))):
                        strat_name_ = list(ht_position.keys())[i]
                        if i == 0:
                            beta, optz = ht.beta_multiplier(ht_search_dt, strat_name_)
                            optz = optz[['Aggregate Z', 'Multiplier']].dropna()
                            optz = optz*(ht_position[strat_name_][0]/whole_position)
                            beta = beta*(ht_position[strat_name_][0]/whole_position)
                        else:
                            beta_, optz_ = ht.beta_multiplier(ht_search_dt, strat_name_)
                            optz_ = optz_[['Aggregate Z', 'Multiplier']].dropna()
                            optz = optz.add(optz_*(ht_position[strat_name_][0]/whole_position))
                            beta += beta_*(ht_position[strat_name_][0]/whole_position)
                    
                    optz = optz.reset_index('Date')
                    st.markdown('**Beta Multiplier: {}**'.format(np.round(beta, 4)))
                    
                    fig = px.line(optz, x='Date', y=optz.columns, hover_data={"Date": "|%B %d, %Y"})
                    fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
                    st.plotly_chart(fig, use_container_width=True)
            
            st.download_button(label="Download data as CSV",data= convert_df(optz),file_name='OPTZ_{}.csv'.format(date.today().isoformat()), mime='text/csv')
            st.divider()

    with tab5:
        
        with st.container():
            col1, col2, col3 = st.columns(3)
            regime_strat = []
            with col1:
                selected_strat = st.multiselect('Select Strategy 1', outright_list, default=None, max_selections=3)
                if len(selected_strat)>0:
                    regime_selected_strat, regime_selected_strat_series, regime_selected_strat_series_tr = get_strategy(selected_strat)
                    regime_selected_strat_series = pd.DataFrame(regime_selected_strat_series, columns=[regime_selected_strat])
                    regime_selected_strat_series_tr = pd.DataFrame((1+regime_selected_strat_series_tr).cumprod(), columns=[regime_selected_strat])
                    regime_strat.append(regime_selected_strat)
            with col2:
                selected_strat_2 = st.multiselect('Select Strategy 2', outright_list, default=None, max_selections=3)
                if len(selected_strat_2)>0:
                    regime_selected_strat_2, regime_selected_strat_series_2, regime_selected_strat_series_tr_2 = get_strategy(selected_strat_2)
                    regime_selected_strat_series_2 = pd.DataFrame(regime_selected_strat_series_2, columns=[regime_selected_strat_2])
                    regime_selected_strat_series_tr_2 = pd.DataFrame((1+regime_selected_strat_series_tr_2).cumprod(), columns=[regime_selected_strat_2])
                    regime_strat.append(regime_selected_strat_2)
                    
            with col3:
                col3_1, col3_2 = st.columns(2)
                with col3_1:
                    text_input = st.text_input("Threshold", placeholder="-1.5, -1.0, -0.5, 0.5, 1.0, 1.5")
                    if len(text_input)==0:
                        threshold_list = [-1.5, -1.0, -0.5, 0.5, 1.0, 1.5]
                    else:
                        threshold_list = [float(t.replace(' ', '')) for t in text_input.split(',')]

                with col3_2:
                    st.markdown("")
                    st.markdown("")
                    start_button = st.button('Calculate Value Regime')
        
        with st.container():
            if start_button:
                for i, strat in enumerate(regime_strat):
                    if i == 0:
                        strategy_vol_trade_to_chart_df = ht.strategy_expected_capital_vol_trading_single(strat)
                        strategy_vol_trade_to_chart_df.columns = [strat]
                    else:
                        strategy_vol_trade_to_chart_df_ = ht.strategy_expected_capital_vol_trading_single(strat)
                        strategy_vol_trade_to_chart_df_.columns = [strat]
                        strategy_vol_trade_to_chart_df = pd.concat([strategy_vol_trade_to_chart_df, strategy_vol_trade_to_chart_df_], axis=1, sort=True).fillna(method='ffill')
            else:
                v_fig = px.line(value_regime_df.reset_index(), x='Date', y=value_regime_df.columns,hover_data={'Date': "|%B %d, %Y"},title='Value Regime')    
                v_fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                
                st.plotly_chart(v_fig, use_container_width=True)
                
                #st.line_chart(value_regime_df, use_container_width=True)
            #strategy_vol_trade_to_chart_df = strategy_vol_trade_to_chart_df.reset_index().rename(columns={'Date':'date'}).fillna(1)
        #st.write(strategy_vol_trade_to_chart_df)
        
        with st.container():
            if start_button:
                if len(selected_strat)>0 and len(selected_strat_2)==0:
                    regime_data = pd.concat([value_regime_df, regime_selected_strat_series], axis=1, sort=True).fillna(method='ffill').dropna()
                    regime_data_tr = pd.concat([value_regime_df, strategy_vol_trade_to_chart_df], axis=1, sort=True).fillna(method='ffill').dropna()
                
                elif len(selected_strat_2)>0 and len(selected_strat)==0:
                    regime_data = pd.concat([value_regime_df, regime_selected_strat_series_2], axis=1, sort=True).fillna(method='ffill').dropna()
                    regime_data_tr = pd.concat([value_regime_df, strategy_vol_trade_to_chart_df], axis=1, sort=True).fillna(method='ffill').dropna()
                
                elif len(selected_strat)>0 and len(selected_strat_2)>0:
                    regime_data = pd.concat([value_regime_df, regime_selected_strat_series, regime_selected_strat_series_2], axis=1, sort=True).fillna(method='ffill').dropna()
                    regime_data_tr = pd.concat([value_regime_df, strategy_vol_trade_to_chart_df], axis=1, sort=True).fillna(method='ffill').dropna()
                
        with st.container():
            if start_button:
                regime_data.index.name = 'Date'
                regime_data = regime_data.reset_index()
                regime_data_tr.index.name = 'Date'
                regime_data_tr = regime_data_tr.reset_index()

                if len(regime_strat) == 1:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=regime_data['Date'], y=regime_data['Market_Breadth'], name='Market_Breadth', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', fill='tozeroy'))
                    fig_.add_trace(go.Scatter(x=regime_data['Date'], y=regime_data[regime_data.columns.tolist()[2]], name=str(regime_data.columns.tolist()[2]), hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', yaxis="y2"))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"))
                elif len(regime_strat) == 2:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=regime_data['Date'], y=regime_data['Market_Breadth'], name='Market_Breadth', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', fill='tozeroy'))
                    fig_.add_trace(go.Scatter(x=regime_data['Date'], y=regime_data[regime_data.columns.tolist()[2]], name=str(regime_data.columns.tolist()[2]), hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=regime_data['Date'], y=regime_data[regime_data.columns.tolist()[3]], name=str(regime_data.columns.tolist()[3]), hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', yaxis="y3"))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                fig_.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
            
                if len(regime_strat) == 1:
                    fig_r = go.Figure()
                    fig_r.add_trace(go.Scatter(x=regime_data_tr['Date'], y=regime_data_tr['Market_Breadth'], name='Market_Breadth', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', fill='tozeroy'))
                    fig_r.add_trace(go.Scatter(x=regime_data_tr['Date'], y=regime_data_tr[regime_data_tr.columns.tolist()[2]], name=str(regime_data_tr.columns.tolist()[2]), hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', yaxis="y2"))
                    fig_r.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"))
                elif len(regime_strat) == 2:
                    fig_r = go.Figure()
                    fig_r.add_trace(go.Scatter(x=regime_data_tr['Date'], y=regime_data_tr['Market_Breadth'], name='Market_Breadth', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', fill='tozeroy'))
                    fig_r.add_trace(go.Scatter(x=regime_data_tr['Date'], y=regime_data_tr[regime_data_tr.columns.tolist()[2]], name=str(regime_data_tr.columns.tolist()[2]), hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', yaxis="y2"))
                    fig_r.add_trace(go.Scatter(x=regime_data_tr['Date'], y=regime_data_tr[regime_data_tr.columns.tolist()[3]], name=str(regime_data_tr.columns.tolist()[3]), hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', mode='lines', yaxis="y3"))
                    fig_r.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                fig_r.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                st.markdown("**Spread in bp**")
                st.plotly_chart(fig_, use_container_width=True)

                st.markdown("**Strategy in %**")
                st.plotly_chart(fig_r, use_container_width=True)

                #st.write(regime_data)
        
        with st.container():
            if start_button:
                if len(regime_strat) == 1:
                    regime_data_diff = pd.DataFrame()
                    regime_data_diff['Market_Breadth'] = regime_data.set_index('Date')['Market_Breadth']
                    regime_data_diff[regime_data.columns.tolist()[2]] = regime_data.set_index('Date')[regime_data.columns.tolist()[2]]-regime_data.set_index('Date')[regime_data.columns.tolist()[2]].shift(1)
                    
                    regime_data_tr_diff = pd.DataFrame()
                    regime_data_tr_diff['Market_Breadth'] = regime_data_tr.set_index('Date')['Market_Breadth']
                    regime_data_tr_diff[regime_data_tr.columns.tolist()[2]] = regime_data_tr.set_index('Date')[regime_data_tr.columns.tolist()[2]]/regime_data_tr.set_index('Date')[regime_data_tr.columns.tolist()[2]].shift(1)-1
                    strat_col = regime_data_diff.columns.tolist()[1:]

                elif len(regime_strat) == 2:
                    regime_data_diff = pd.DataFrame()
                    regime_data_diff['Market_Breadth'] = regime_data.set_index('Date')['Market_Breadth']
                    regime_data_diff[regime_data.columns.tolist()[2]] = regime_data.set_index('Date')[regime_data.columns.tolist()[2]] - regime_data.set_index('Date')[regime_data.columns.tolist()[2]].shift(1)
                    regime_data_diff[regime_data.columns.tolist()[3]] = regime_data.set_index('Date')[regime_data.columns.tolist()[3]] - regime_data.set_index('Date')[regime_data.columns.tolist()[3]].shift(1)

                    regime_data_tr_diff = pd.DataFrame()
                    regime_data_tr_diff['Market_Breadth'] = regime_data_tr.set_index('Date')['Market_Breadth']
                    regime_data_tr_diff[regime_data_tr.columns.tolist()[2]] = regime_data_tr.set_index('Date')[regime_data_tr.columns.tolist()[2]]/regime_data_tr.set_index('Date')[regime_data_tr.columns.tolist()[2]].shift(1)-1
                    regime_data_tr_diff[regime_data_tr.columns.tolist()[3]] = regime_data_tr.set_index('Date')[regime_data_tr.columns.tolist()[3]]/regime_data_tr.set_index('Date')[regime_data_tr.columns.tolist()[3]].shift(1)-1
                    strat_col = regime_data_diff.columns.tolist()[1:]

                for i, threshold in enumerate(threshold_list):
                    if threshold<0:
                        average = regime_data_diff[regime_data_diff['Market_Breadth']<=threshold][strat_col].mean()
                        annualized_avg = average*365
                        stdev = regime_data_diff[regime_data_diff['Market_Breadth']<=threshold][strat_col].std()*np.sqrt(252)
                        sharpe = annualized_avg/stdev

                        ret_average = regime_data_tr_diff[regime_data_tr_diff['Market_Breadth']<=threshold][strat_col].mean()
                        ret_annualized_avg = ret_average*365
                        ret_stdev = regime_data_tr_diff[regime_data_tr_diff['Market_Breadth']<=threshold][strat_col].std()*np.sqrt(252)
                        ret_sharpe = ret_annualized_avg/ret_stdev
                    
                    elif threshold>=0:
                        average = regime_data_diff[regime_data_diff['Market_Breadth']>=threshold][strat_col].mean()
                        annualized_avg = average*365
                        stdev = regime_data_diff[regime_data_diff['Market_Breadth']>=threshold][strat_col].std()*np.sqrt(252)
                        sharpe = annualized_avg/stdev

                        ret_average = regime_data_tr_diff[regime_data_tr_diff['Market_Breadth']>=threshold][strat_col].mean()
                        ret_annualized_avg = ret_average*365
                        ret_stdev = regime_data_tr_diff[regime_data_tr_diff['Market_Breadth']>=threshold][strat_col].std()*np.sqrt(252)
                        ret_sharpe = ret_annualized_avg/ret_stdev

                    if i == 0:
                        diff_avg = pd.DataFrame(average, columns = [threshold])
                        diff_sharpe = pd.DataFrame(sharpe, columns = [threshold])
                        ret_diff_avg = pd.DataFrame(ret_average, columns = [threshold])
                        ret_diff_sharpe = pd.DataFrame(ret_sharpe, columns = [threshold])
                    
                    else:
                        diff_avg = pd.concat([diff_avg, pd.DataFrame(average, columns = [threshold])], axis=1) 
                        diff_sharpe = pd.concat([diff_sharpe, pd.DataFrame(sharpe, columns = [threshold])], axis=1)
                        ret_diff_avg = pd.concat([ret_diff_avg, pd.DataFrame(ret_average, columns = [threshold])], axis=1) 
                        ret_diff_sharpe = pd.concat([ret_diff_sharpe, pd.DataFrame(ret_sharpe, columns = [threshold])], axis=1)


                bcol_1, bcol_2 = st.columns(2)
                with bcol_1:
                    st.write("**Spread Average**")
                    if len(strat_col)==1:
                        fig_bar_avg = go.Figure(data=[go.Bar(name=str(strat_col[0]), x=threshold_list, y=diff_avg.values.tolist()[0])])
                        fig_bar_avg.update_layout(barmode='group')
                        st.plotly_chart(fig_bar_avg, use_container_width=True)
                    elif len(strat_col)==2:
                        fig_bar_avg = go.Figure(data=[go.Bar(name=str(strat_col[0]), x=threshold_list, y=diff_avg.values.tolist()[0])
                                                    ,go.Bar(name=str(strat_col[1]), x=threshold_list, y=diff_avg.values.tolist()[1])])
                        fig_bar_avg.update_layout(barmode='group')
                        st.plotly_chart(fig_bar_avg, use_container_width=True)
                
                with bcol_2:
                    st.write("**Spread Sharpe**")
                    if len(strat_col)==1:
                        fig_bar_sharpe = go.Figure(data=[go.Bar(name=str(strat_col[0]), x=threshold_list, y=diff_sharpe.values.tolist()[0])])
                        fig_bar_sharpe.update_layout(barmode='group')
                        st.plotly_chart(fig_bar_sharpe, use_container_width=True)
                    elif len(strat_col)==2:
                        fig_bar_sharpe = go.Figure(data=[go.Bar(name=str(strat_col[0]), x=threshold_list, y=diff_sharpe.values.tolist()[0])
                                                    ,go.Bar(name=str(strat_col[1]), x=threshold_list, y=diff_sharpe.values.tolist()[1])])
                        fig_bar_sharpe.update_layout(barmode='group')
                        st.plotly_chart(fig_bar_sharpe, use_container_width=True)

        with st.container():
            if start_button:
                bcol_1, bcol_2 = st.columns(2)
                with bcol_1:
                    st.write("**Strategy Average**")
                    if len(strat_col)==1:
                        fig_bar_ret_avg = go.Figure(data=[go.Bar(name=str(strat_col[0]), x=threshold_list, y=ret_diff_avg.values.tolist()[0])])
                        fig_bar_ret_avg.update_layout(barmode='group')
                        st.plotly_chart(fig_bar_ret_avg, use_container_width=True)
                    elif len(strat_col)==2:
                        fig_bar_ret_avg = go.Figure(data=[go.Bar(name=str(strat_col[0]), x=threshold_list, y=ret_diff_avg.values.tolist()[0])
                                                    ,go.Bar(name=str(strat_col[1]), x=threshold_list, y=ret_diff_avg.values.tolist()[1])])
                        fig_bar_ret_avg.update_layout(barmode='group')
                        st.plotly_chart(fig_bar_ret_avg, use_container_width=True)
                
                with bcol_2:
                    st.write("**Strategy Sharpe**")
                    if len(strat_col)==1:
                        fig_bar_ret_sharpe = go.Figure(data=[go.Bar(name=str(strat_col[0]), x=threshold_list, y=ret_diff_sharpe.values.tolist()[0])])
                        fig_bar_ret_sharpe.update_layout(barmode='group')
                        st.plotly_chart(fig_bar_ret_sharpe, use_container_width=True)
                    elif len(strat_col)==2:
                        fig_bar_ret_sharpe = go.Figure(data=[go.Bar(name=str(strat_col[0]), x=threshold_list, y=ret_diff_sharpe.values.tolist()[0])
                                                    ,go.Bar(name=str(strat_col[1]), x=threshold_list, y=ret_diff_sharpe.values.tolist()[1])])
                        fig_bar_ret_sharpe.update_layout(barmode='group')
                        st.plotly_chart(fig_bar_ret_sharpe, use_container_width=True)

            

 
 