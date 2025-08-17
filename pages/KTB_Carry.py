file_dir = 'C:\\Users\\kimju\\MPT-Quant\\MacroTrading'
css_dir = 'C:\\Users\\kimju\\MPT-Quant\\SystemMacro_App\\pages\\style.css'

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from datetime import date
import pandas as pd
import numpy as np
import sys
sys.path.append(file_dir)
#from Feature_Preprocessing import RatesData, RatesDataProcess
from Strategy_MA_Optimal_Portfolio import MultiAssetPortDataProcess
from Strategy_KTB_Optimal_Carry_Portfolio import FairCarryPrice, FairCarryRegime, FairCarryDataLite
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
def pull_carry_data():
    fcdl = FairCarryDataLite('2012-10-01', date.today().isoformat())
    fcp = FairCarryPrice('2012-10-01', date.today().isoformat(), fcdl)
    fcr = FairCarryRegime( date.today().isoformat(),fcp)
    return fcdl, fcp, fcr

@st.cache_resource(show_spinner=False)
def pull_strategy_data_series(_dp):
    strategy = _dp.strategy_cc
    strategy_tr = _dp.strategy_cc_tr
    strategy_outright = pd.concat([_dp.ktb, _dp.swap, _dp.ktbf, _dp.ktbi, _dp.ustf, _dp.bund], axis=1, sort=True).fillna(method='ffill')
    strategy_outright_tr = (1+pd.concat([_dp.ktb_tr, _dp.swap_tr, _dp.ktbf_tr, _dp.ustf_tr, _dp.bund_tr], axis=1, sort=True).fillna(method='ffill')).cumprod()
    strategy_outright_tr = strategy_outright_tr/strategy_outright_tr.shift(1)-1
    return strategy, strategy_tr, strategy_outright, strategy_outright_tr

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

@st.cache_resource(show_spinner=False)
def get_distinct_date():
    dbm = dbm_s.DBExecuteManager()
    q = "SELECT DISTINCT RCD_DATE FROM stratdb.tb_scnd_ktb_cary;"
    dt_list = dbm.get_fetchall(q)
    dt_list = [d[0] for d in dt_list]
    dt_list = sorted(dt_list)[::-1]
    return dt_list

@st.cache_data(show_spinner=False)
def get_carry_score_df():
    dbm = dbm_s.DBExecuteManager()
    score_q = "SELECT RCD_DATE, TENR_1, TENR_2, TENR_3, DRCT, VOL_CARY_Z, PCA_Z, FUND_Z, MKT_CARY, ABS_MA_MKT_CARY, VOL_CARY, MA_VOL_CARY, PCA_CARY, FUND_CARY FROM stratdb.tb_scnd_ktb_cary"
    score_df = dbm.get_fetchall(score_q)
    score_df = pd.DataFrame(score_df, columns=['Date', 'Tenor 1', 'Tenor 2', 'Tenor 3', 'Direction', 'Vol Carry Z', 'PCA Carry Z', 'Funda Carry Z', 'Market Carry', 'MA Market Carry', 'Vol Carry', 'MA Vol Carry', 'PCA Carry', 'Funda Carry'])
    return score_df


#데이터 불러오기
with st.spinner("Querying Data, Will take about 2 minutes, Please Wait..."):
    if 'mapdp' not in st.session_state:
        mapdp = pull_strategy_data()
        st.session_state.mapdp = mapdp
    else:
        mapdp = st.session_state.mapdp
    dp = mapdp.dp
    fcdl, fcp, fcr = pull_carry_data()
    dt_list = get_distinct_date()
    score_df_whole = get_carry_score_df()
    #전략리스트
    ktb = ['1Y_KTB', '2Y_KTB','3Y_KTB','4Y_KTB','5Y_KTB','7Y_KTB','10Y_KTB','20Y_KTB','30Y_KTB', 'IL10Y_KTB', 'BE10Y_KTB', '3Y_FUT', '10Y_FUT']
    swap = ['9M_IRS', '1Y_IRS', '18M_IRS','2Y_IRS','3Y_IRS','4Y_IRS','5Y_IRS','7Y_IRS','10Y_IRS']
    foreign = ['2Y_FUT_US', '5Y_FUT_US', '10Y_FUT_US', '30Y_FUT_US','2Y_FUT_GER', '5Y_FUT_GER', '10Y_FUT_GER'] 
    outright_list = ktb+swap+foreign
    #가격데이터
    strategy, strategy_tr, strategy_outright, strategy_outright_tr = pull_strategy_data_series(dp)

 
with st.container():
    tab1, tab2, tab3 = st.tabs(['Score', 'Technical', 'Regime'])

    with open(css_dir) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

    with tab1:
        date_selected = st.selectbox('Select date below', dt_list)
        #dbm = dbm_s.DBExecuteManager()
        #score_q = "SELECT TENR_1, TENR_2, TENR_3, DRCT, VOL_CARY_Z, PCA_Z, FUND_Z, MKT_CARY, ABS_MA_MKT_CARY, VOL_CARY, MA_VOL_CARY, PCA_CARY, FUND_CARY FROM stratdb.tb_scnd_ktb_cary WHERE DATE_FORMAT(STR_TO_DATE(RCD_DATE, '%Y-%m-%d'),'%Y-%m-%d') = DATE_FORMAT(STR_TO_DATE('{}', '%Y-%m-%d'),'%Y-%m-%d')".format(date_selected)
        #dbm.get_fetchall(score_q)
        #score_df = pd.DataFrame(score_df, columns=['Tenor 1', 'Tenor 2', 'Tenor 3', 'Direction', 'Vol Carry Z', 'PCA Carry Z', 'Funda Carry Z', 'Market Carry', 'MA Market Carry', 'Vol Carry', 'MA Vol Carry', 'PCA Carry', 'Funda Carry']).sort_values(by='Vol Carry Z').set_index('Tenor 1').reset_index()
        score_df = score_df_whole[score_df_whole['Date'] == date_selected]
        score_df = score_df[['Tenor 1', 'Tenor 2', 'Tenor 3', 'Direction', 'Vol Carry Z', 'PCA Carry Z', 'Funda Carry Z', 'Market Carry', 'MA Market Carry', 'Vol Carry', 'MA Vol Carry', 'PCA Carry', 'Funda Carry']].sort_values(by='Vol Carry Z').set_index('Tenor 1').reset_index()
        score_df['Market Carry'] = score_df['Market Carry'] * score_df['Direction']
        score_df['PCA Carry'] = score_df['PCA Carry'] * score_df['Direction']
        score_df['Funda Carry'] = score_df['Funda Carry'] * score_df['Direction']
        st.dataframe(score_df, hide_index=True, height=900, column_config={"widgets": st.column_config.Column(width='large')}, use_container_width=True)
        
        st.download_button(label="Download data as CSV",data= convert_df(score_df),file_name='KTB_Carry_{}.csv'.format(date_selected), mime='text/csv')
    
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
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
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
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_['date'], y=strategy_series_tr_to_chart_df_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]))
                elif len(strategy_selected) == 2:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_['date'], y=strategy_series_tr_to_chart_df_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_['date'], y=strategy_series_tr_to_chart_df_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.update_layout(xaxis=dict(domain=[0.1, 0.9]),
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

        st.divider()

        if len(strategy_selected)>0:
            strategy_selected = list(set(strategy_selected))
            
            if len(strategy_selected)==1:
                strategy_1 = strategy_selected[0]
                strategy_carry = pd.DataFrame(fcr.carry_series_dict[strategy_1]*fcr.carry_series_direction_dict[strategy_1], columns=[str(strategy_1)]).reset_index()
                strategy_carry_adj = pd.DataFrame(fcr.carry_coverage_vol_dict[strategy_1]*fcr.carry_coverage_vol_direction_dict[strategy_1], columns=[str(strategy_1)]).reset_index().rename(columns={'index':'Date'})
                strategy_carry_pca = pd.DataFrame(fcr.pca_carry_coverage_vol_dict[strategy_1]*fcr.pca_carry_coverage_vol_direction_dict[strategy_1], columns=[str(strategy_1)]).reset_index().rename(columns={'index':'Date'})
                strategy_carry_funda = pd.DataFrame(fcr.funda_carry_coverage_vol_dict[strategy_1]*fcr.funda_carry_coverage_vol_direction_dict[strategy_1], columns=[str(strategy_1)]).reset_index().rename(columns={'index':'Date'})
                
            elif len(strategy_selected)==2:
                strategy_1 = strategy_selected[0]
                strategy_2 = strategy_selected[1]
                strategy_carry_1 = pd.DataFrame(fcr.carry_series_dict[strategy_1]*fcr.carry_series_direction_dict[strategy_1], columns=[str(strategy_1)])
                strategy_carry_adj_1 = pd.DataFrame(fcr.carry_coverage_vol_dict[strategy_1]*fcr.carry_coverage_vol_direction_dict[strategy_1], columns=[str(strategy_1)])
                strategy_carry_pca_1 = pd.DataFrame(fcr.pca_carry_coverage_vol_dict[strategy_1]*fcr.pca_carry_coverage_vol_direction_dict[strategy_1], columns=[str(strategy_1)])
                strategy_carry_funda_1 = pd.DataFrame(fcr.funda_carry_coverage_vol_dict[strategy_1]*fcr.funda_carry_coverage_vol_direction_dict[strategy_1], columns=[str(strategy_1)])
                strategy_carry_2 = pd.DataFrame(fcr.carry_series_dict[strategy_2]*fcr.carry_series_direction_dict[strategy_2], columns=[str(strategy_2)])
                strategy_carry_adj_2 = pd.DataFrame(fcr.carry_coverage_vol_dict[strategy_2]*fcr.carry_coverage_vol_direction_dict[strategy_2], columns=[str(strategy_2)])
                strategy_carry_pca_2 = pd.DataFrame(fcr.pca_carry_coverage_vol_dict[strategy_2]*fcr.pca_carry_coverage_vol_direction_dict[strategy_2], columns=[str(strategy_2)])
                strategy_carry_funda_2 = pd.DataFrame(fcr.funda_carry_coverage_vol_dict[strategy_2]*fcr.funda_carry_coverage_vol_direction_dict[strategy_2], columns=[str(strategy_2)])
                
                strategy_carry = pd.concat([strategy_carry_1,strategy_carry_2], axis=1, sort=True).fillna(method='ffill').reset_index()
                strategy_carry_adj = pd.concat([strategy_carry_adj_1,strategy_carry_adj_2], axis=1, sort=True).fillna(method='ffill').reset_index().rename(columns={'index':'Date'})
                strategy_carry_pca = pd.concat([strategy_carry_pca_1,strategy_carry_pca_2], axis=1, sort=True).fillna(method='ffill').reset_index().rename(columns={'index':'Date'})
                strategy_carry_funda = pd.concat([strategy_carry_funda_1,strategy_carry_funda_2], axis=1, sort=True).fillna(method='ffill').reset_index().rename(columns={'index':'Date'})

            elif len(strategy_selected)==3:
                strategy_1 = strategy_selected[0]
                strategy_2 = strategy_selected[1]
                strategy_3 = strategy_selected[2]
                strategy_carry_1 = pd.DataFrame(fcr.carry_series_dict[strategy_1]*fcr.carry_series_direction_dict[strategy_1], columns=[str(strategy_1)])
                strategy_carry_adj_1 = pd.DataFrame(fcr.carry_coverage_vol_dict[strategy_1]*fcr.carry_coverage_vol_direction_dict[strategy_1], columns=[str(strategy_1)])
                strategy_carry_pca_1 = pd.DataFrame(fcr.pca_carry_coverage_vol_dict[strategy_1]*fcr.pca_carry_coverage_vol_direction_dict[strategy_1], columns=[str(strategy_1)])
                strategy_carry_funda_1 = pd.DataFrame(fcr.funda_carry_coverage_vol_dict[strategy_1]*fcr.funda_carry_coverage_vol_direction_dict[strategy_1], columns=[str(strategy_1)])
                strategy_carry_2 = pd.DataFrame(fcr.carry_series_dict[strategy_2]*fcr.carry_series_direction_dict[strategy_2], columns=[str(strategy_2)])
                strategy_carry_adj_2 = pd.DataFrame(fcr.carry_coverage_vol_dict[strategy_2]*fcr.carry_coverage_vol_direction_dict[strategy_2], columns=[str(strategy_2)])
                strategy_carry_pca_2 = pd.DataFrame(fcr.pca_carry_coverage_vol_dict[strategy_2]*fcr.pca_carry_coverage_vol_direction_dict[strategy_2], columns=[str(strategy_2)])
                strategy_carry_funda_2 = pd.DataFrame(fcr.funda_carry_coverage_vol_dict[strategy_2]*fcr.funda_carry_coverage_vol_direction_dict[strategy_2], columns=[str(strategy_2)])
                strategy_carry_3 = pd.DataFrame(fcr.carry_series_dict[strategy_3]*fcr.carry_series_direction_dict[strategy_3], columns=[str(strategy_3)])
                strategy_carry_adj_3 = pd.DataFrame(fcr.carry_coverage_vol_dict[strategy_3]*fcr.carry_coverage_vol_direction_dict[strategy_3], columns=[str(strategy_3)])
                strategy_carry_pca_3 = pd.DataFrame(fcr.pca_carry_coverage_vol_dict[strategy_3]*fcr.pca_carry_coverage_vol_direction_dict[strategy_3], columns=[str(strategy_2)])
                strategy_carry_funda_3 = pd.DataFrame(fcr.funda_carry_coverage_vol_dict[strategy_3]*fcr.funda_carry_coverage_vol_direction_dict[strategy_3], columns=[str(strategy_3)])
                
                strategy_carry = pd.concat([strategy_carry_1,strategy_carry_2,strategy_carry_3], axis=1, sort=True).fillna(method='ffill').reset_index()
                strategy_carry_adj = pd.concat([strategy_carry_adj_1,strategy_carry_adj_2,strategy_carry_adj_3], axis=1, sort=True).fillna(method='ffill').reset_index().rename(columns={'index':'Date'})
                strategy_carry_pca = pd.concat([strategy_carry_pca_1,strategy_carry_pca_2,strategy_carry_pca_3], axis=1, sort=True).fillna(method='ffill').reset_index().rename(columns={'index':'Date'})
                strategy_carry_funda = pd.concat([strategy_carry_funda_1,strategy_carry_funda_2,strategy_carry_funda_3], axis=1, sort=True).fillna(method='ffill').reset_index().rename(columns={'index':'Date'})

            fig_carry = px.line(strategy_carry, x='Date', y=strategy_carry.columns,hover_data={'Date': "|%B %d, %Y"},title='Strategy Carry')    
            fig_carry.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            st.plotly_chart(fig_carry, use_container_width=True)

            fig_carry_adj = px.line(strategy_carry_adj, x='Date', y=strategy_carry_adj.columns,hover_data={'Date': "|%B %d, %Y"},title='Strategy Carry/Vol')    
            fig_carry_adj.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            st.plotly_chart(fig_carry_adj, use_container_width=True)

            fig_carry_pca = px.line(strategy_carry_pca, x='Date', y=strategy_carry_pca.columns,hover_data={'Date': "|%B %d, %Y"},title='Strategy PCA Carry')    
            fig_carry_pca.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            st.plotly_chart(fig_carry_pca, use_container_width=True)

            fig_carry_funda = px.line(strategy_carry_funda, x='Date', y=strategy_carry_funda.columns,hover_data={'Date': "|%B %d, %Y"},title='Strategy Fundamental Carry')    
            fig_carry_funda.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            st.plotly_chart(fig_carry_funda, use_container_width=True)

        st.divider()
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                strat = st.selectbox('Strategy Selected', strategy_selected)
            with col2:
                col2_1, col2_2, col2_3 = st.columns(3)
                with col2_1:
                    marketc = st.number_input('Market', 0.0, 1.0, step=0.05)
                with col2_2:
                    pcac = st.number_input('PCA', 0.0, 1.0, step=0.05)
                with col2_3:
                    fundac = st.number_input('Fundamental', 0.0, 1.0, step=0.05)
            
            if marketc+pcac+fundac>0:
                strategy_vol_trade_to_chart_df = fcr.strategy_expected_capital_vol_trading_single(strat,[marketc,pcac,fundac])
                strategy_vol_trade_to_chart_df = strategy_vol_trade_to_chart_df.ffill().dropna()
                strategy_vol_trade_to_chart_df.index.name = 'Date'
                strategy_vol_trade_to_chart_df.columns = ['Strategy']
                strategy_vol_trade_to_chart_df = strategy_vol_trade_to_chart_df.reset_index()
                #st.dataframe(strategy_vol_trade_to_chart_df, height = 900, use_container_width=True)
                
                
                fig_trade = px.line(strategy_vol_trade_to_chart_df, x='Date', y=strategy_vol_trade_to_chart_df.columns, hover_data={'Date': "|%B %d, %Y"},title='Strategy with Trading')    
                fig_trade.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                st.plotly_chart(fig_trade, use_container_width=True)

                #st.download_button(label="Download data as CSV",data= convert_df(past_data),file_name='KTB_Value_Data_{}.csv'.format(strat), mime='text/csv')

            st.divider()     
   
    with tab3:
        with st.container():
            #GMM Regime Bar Plot
            carry_gmm_df = pd.concat([fcr.carry_regime_factor, fcr.carry_regime], axis=1, sort=True).fillna(method='ffill').dropna()
            carry_gmm_df = carry_gmm_df.reset_index()
            carry_gmm_df = carry_gmm_df.rename(columns={'index':'Date', 'Regime_1':'Regime 1', 'Regime_2':'Regime 2'})
            
            fig_c = make_subplots(specs=[[{"secondary_y":True}]], subplot_titles=['GMM Regime'])
            fig_c.add_trace(go.Bar(x=carry_gmm_df['Date'], y=carry_gmm_df['Regime 1'], name='Regime 1', hovertemplate='<br>Date: %{x:|%B %d, %Y}<br> Regime 1: %{y:.3f}'), secondary_y=False)
            fig_c.add_trace(go.Bar(x=carry_gmm_df['Date'], y=carry_gmm_df['Regime 2'], name='Regime 2', hovertemplate='<br>Date: %{x:|%B %d, %Y}<br> Regime 2: %{y:.3f}'), secondary_y=False)
            fig_c.add_trace(go.Scatter(x=carry_gmm_df['Date'], y=carry_gmm_df['FRA Deviation'], name='FRA Deviation', mode='lines', hovertemplate='<br>Date: %{x:|%B %d, %Y}<br>'+ 'FRA Deviation' + ': %{y:.3f}'), secondary_y=True)
            fig_c.add_trace(go.Scatter(x=carry_gmm_df['Date'], y=carry_gmm_df['Carry Deviation'], name='Carry Deviation', mode='lines', hovertemplate='<br>Date: %{x:|%B %d, %Y}<br>'+ 'Carry Deviation' + ': %{y:.3f}'), secondary_y=True)
            fig_c.add_trace(go.Scatter(x=carry_gmm_df['Date'], y=carry_gmm_df['Top Instability'], name='Top Instability', mode='lines',  hovertemplate='<br>Date: %{x:|%B %d, %Y}<br>'+ 'Top Instability' + ': %{y:.3f}'), secondary_y=True)
            fig_c.add_trace(go.Scatter(x=carry_gmm_df['Date'], y=carry_gmm_df['Bottom Instability'], name='Bottom Instability', mode='lines',hovertemplate='<br>Date: %{x:|%B %d, %Y}<br>'+'Bottom Instability'+ ': %{y:.3f}'), secondary_y=True)
            
            fig_c.update_layout(barmode='stack')
            fig_c.update_xaxes(dtick="M3", tickformat="%Y.%m",
                        rangeselector = dict(
                        buttons=list([
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all")])))
            fig_c.update_yaxes(title_text='GMM', secondary_y=False)
            fig_c.update_yaxes(title_text='Carry Regime Factor', secondary_y=True)
            st.markdown('**Carry Regime**')
            st.plotly_chart(fig_c, use_container_width=True)
        
        #st.divider()
        
        
                
 


#with st.container():
#with open('style.css') as f:
#    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)