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
from Feature_Preprocessing import RatesData, RatesDataProcess
from Strategy_MA_Optimal_Portfolio import MultiAssetPortDataProcess
from Strategy_MA_Macro_Trend import MacroTrendSignal
from Strategy_MA_Trend_Portfolio import TrendPortGenerator
from MPTSRT_StratDB import db_execute_manager as dbm_s
#dbm = dbm_s.DBExecuteManager()

if 'note' not in st.session_state:
    st.session_state.note = ''

st.session_state.note = st.sidebar.text_area('Note', st.session_state.note, height=300)

def dict_merge(dict1, dict2):
    res = {**dict1, **dict2}
    return res

@st.cache_resource
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

@st.cache_resource(show_spinner=False)
def pull_strategy_data():
    mapdp =  MultiAssetPortDataProcess()
    return mapdp

@st.cache_resource(show_spinner=False)
def pull_trend_port():
    tpg = TrendPortGenerator(dict_pt_weight={'rates_price_trend':1, 'fx_price_trend':1, 'equity_price_trend':1, 'commodity_price_trend':1})
    #vol_skew_weight, pl_after_cost, vs_pos, indiv_ret = pg.volskewport()
    return tpg

@st.cache_resource(show_spinner=False)
def pull_macro_trend_data():
    mts = MacroTrendSignal()
    signal_df, macro_factor_delta, macro_beta = mts.macro_trend_signal(mts.macro_factor_index, regression_lookback=60, ma_lookback=60)
    signal_indi_df, macro_indi_factor_delta, macro_indi_beta = mts.macro_trend_signal(mts.macro_indi_factor_index)
    trend_on_trend = mts.macro_trend_tot('macro_trend')
    trend_on_trend_indi = mts.macro_trend_tot('macro_factor_trend')
    #strategy_position = mts.signal_position_trend_(signal_df)
    return mts, signal_df, macro_factor_delta, macro_beta, trend_on_trend, signal_indi_df, macro_indi_factor_delta, macro_indi_beta, trend_on_trend_indi

@st.cache_resource(show_spinner=False)
def pull_strategy_data_series(_mapdp):
    strategy_list_futures = list(_mapdp.fut_strategy_df.columns)
    strategy_list_rates = list(_mapdp.rates_strat_tr_cumprod_df.columns)
    strategy_list_rp = list(_mapdp.rp_strategy_df.columns)
    strategy_list_macrofactor = list(_mapdp.macro_factor_cum.columns)
    strategy_list_macroindifactor = list(_mapdp.macro_indi_factor_cum.columns)
    #strategy_macrofactor = mapdp.macro_factor_cum
    strategy_set = _mapdp.strategy_set_universe.copy()
    strategy_set.index = pd.DatetimeIndex(strategy_set.index)
    strategy_set.index.name = None
    #strategy_data = pd.concat([strategy_macrofactor, strategy_set], axis=1, sort=True).fillna(method='ffill')
    return strategy_list_futures, strategy_list_rates, strategy_list_rp, strategy_list_macrofactor, strategy_list_macroindifactor, strategy_set #, strategy_data

def get_strategy_name(options, mapdp):
    strategy_list_rates = list(mapdp.rates_strat_tr_cumprod_df.columns)
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

def strategy_return_after_inclusion(strategy_list, strategy_set, signal_date, current_price, direction):
    strategy_list_rates = list(strategy_set.columns)
    if len(strategy_list) == 1:
        strategy_selected_tr = strategy_list[0]

    elif len(strategy_list) == 2:
        t_1 = strategy_list[0]
        t_2 = strategy_list[1]
        for s in strategy_list_rates:
            if len(s) == len(strategy_list) and t_1 in s and t_2 in s:
                strategy_selected_tr = s
                break
        
    elif len(strategy_list) == 3:
        t_1 = strategy_list[0]
        t_2 = strategy_list[1]
        t_3 = strategy_list[2]
        
        for s in strategy_list_rates:
            if len(s) == len(strategy_list) and t_1 in s and t_2 in s and t_3 in s:
                strategy_selected_tr = s
                break
    
    strategy_set_selected = strategy_set[[strategy_selected_tr]]
    if direction == 1:
        return_after_inclusion = current_price/strategy_set_selected[strategy_set_selected.index>=signal_date][strategy_selected_tr].values[0]-1
    elif direction == -1:
        return_after_inclusion = strategy_set_selected[strategy_set_selected.index>=signal_date][strategy_selected_tr].values[0]/current_price-1

    return return_after_inclusion

def get_strategy(options):
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

def position_summary_single(stratgy_position):
    for j, dt in enumerate(list(stratgy_position.index)):
        elem = stratgy_position[stratgy_position.index == dt]
        elem_df = pd.DataFrame(elem.values.tolist()[0])
        elem_df = elem_df.rename(columns={0:'Ticker', 1:'Contract'})
        elem_df['Date'] = dt
        elem_df['Strategy'] = 'Macro_Trend'

        if j == 0:
            pos_summary = elem_df
        else:
            pos_summary = pd.concat([pos_summary, elem_df])

    return pos_summary

@st.cache_resource(show_spinner=False)
def get_pl_pos():
    dbm = dbm_s.DBExecuteManager()
    #price trend pl
    price_trend_q = "SELECT RCD_DATE, PNL, STRT_NAME FROM stratdb.tb_scnd_rp_pl WHERE STRT_NAME LIKE '%price_trend';"
    price_trend = dbm.get_fetchall(price_trend_q)
    price_trend_df = pd.DataFrame(price_trend, columns=['Date', 'PL', 'Strategy'])

    #price trend pos
    price_trend_pos_q = "SELECT RCD_DATE, TCKR, POS, STRT_NAME FROM stratdb.tb_scnd_rp_pos WHERE STRT_NAME LIKE '%price_trend';"
    price_trend_pos = dbm.get_fetchall(price_trend_pos_q)
    price_trend_pos_df = pd.DataFrame(price_trend_pos, columns=['Date', 'Ticker', 'Position', 'Strategy'])
    
    #macro trend pl
    macro_trend_q = "SELECT RCD_DATE, PNL, STRT_NAME FROM stratdb.tb_scnd_rp_pl WHERE STRT_NAME = 'macro_trend';"
    macro_trend = dbm.get_fetchall(macro_trend_q)
    macro_trend_df = pd.DataFrame(macro_trend, columns=['Date', 'PL', 'Strategy'])

    #macro trend pos
    macro_trend_pos_q = "SELECT RCD_DATE, TCKR, POS, STRT_NAME FROM stratdb.tb_scnd_rp_pos WHERE STRT_NAME = 'macro_trend';"
    macro_trend_pos = dbm.get_fetchall(macro_trend_pos_q)
    macro_trend_pos_df = pd.DataFrame(macro_trend_pos, columns=['Date', 'Ticker', 'Position', 'Strategy'])
    macro_trend_pos_df = macro_trend_pos_df[macro_trend_pos_df['Date']>=macro_trend_df['Date'][0]]

    #macro factor trend pl
    macro_factor_trend_q = "SELECT RCD_DATE, PNL, STRT_NAME FROM stratdb.tb_scnd_rp_pl WHERE STRT_NAME = 'macro_factor_trend';"
    macro_factor_trend = dbm.get_fetchall(macro_factor_trend_q)
    macro_factor_trend_df = pd.DataFrame(macro_factor_trend, columns=['Date', 'PL', 'Strategy'])

    #macro factor trend pos
    macro_factor_trend_pos_q = "SELECT RCD_DATE, TCKR, POS, STRT_NAME FROM stratdb.tb_scnd_rp_pos WHERE STRT_NAME = 'macro_factor_trend';"
    macro_factor_trend_pos = dbm.get_fetchall(macro_factor_trend_pos_q)
    macro_factor_trend_pos_df = pd.DataFrame(macro_factor_trend_pos, columns=['Date', 'Ticker', 'Position', 'Strategy'])
    macro_factor_trend_pos_df = macro_factor_trend_pos_df[macro_factor_trend_pos_df['Date']>=macro_factor_trend_df['Date'][0]]

    return price_trend_df, price_trend_pos_df, macro_trend_df, macro_trend_pos_df, macro_factor_trend_df, macro_factor_trend_pos_df

#데이터 불러오기
with st.spinner("Querying Data, Will take about 2 minutes, Please Wait..."):
    if 'mapdp' not in st.session_state:
        mapdp = pull_strategy_data()
        st.session_state.mapdp = mapdp
    else:
        mapdp = st.session_state.mapdp

    if 'tpg' not in st.session_state:
        tpg = pull_trend_port()
        st.session_state.tpg = tpg
    else:
        tpg = st.session_state.tpg

    mts, signal_df, macro_factor_delta, macro_beta, trend_on_trend, signal_indi_df, macro_indi_factor_delta, macro_indi_beta, trend_on_trend_indi  = pull_macro_trend_data()
    signal_df.index = signal_df.index.astype(str)
    macro_factor_delta.index = macro_factor_delta.index.astype(str)
    macro_beta['Date'] = macro_beta['Date'].astype(str)
    signal_indi_df.index =signal_indi_df.index.astype(str)
    macro_indi_factor_delta.index = macro_indi_factor_delta.index.astype(str)
    macro_indi_beta['Date'] = macro_indi_beta['Date'].astype(str)
    price_trend_pl_df, price_trend_pos_df, macro_trend_pl_df, macro_trend_pos_df, macro_factor_trend_pl_df, macro_factor_trend_pos_df = get_pl_pos()
    vol_skew_weight, trend_port_pl, trend_port_pos, trend_strat_ret = tpg.volskewport()
    vol_skew_weight.columns = [c.lower() for c in vol_skew_weight.columns]
    trend_strat_ret.columns = [c.lower() for c in trend_strat_ret.columns]

#전략리스트 및 가격데이터
ktb = ['1Y_KTB', '2Y_KTB','3Y_KTB','4Y_KTB','5Y_KTB','7Y_KTB','10Y_KTB','20Y_KTB','30Y_KTB', 'IL10Y_KTB', 'BE10Y_KTB', '3Y_FUT', '10Y_FUT']
swap = ['9M_IRS', '1Y_IRS', '18M_IRS','2Y_IRS','3Y_IRS','4Y_IRS','5Y_IRS','7Y_IRS','10Y_IRS']
foreign = ['2Y_FUT_US', '5Y_FUT_US', '10Y_FUT_US', '30Y_FUT_US','2Y_FUT_GER', '5Y_FUT_GER', '10Y_FUT_GER'] 
outright_list = ktb+swap+foreign
strategy_list_futures, strategy_list_rates, strategy_list_rp, strategy_list_macrofactor, strategy_list_macroindifactor, strategy_set = pull_strategy_data_series(mapdp)

with st.container():
    tab1, tab2, tab3, tab4 = st.tabs(['Score', 'Macro', 'Port', 'Charts'])

    with open(css_dir) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

    with tab1:
        q = "SELECT DISTINCT RCD_DATE FROM stratdb.tb_scnd_ma_trnd;"
        dt_list = dbm.get_fetchall(q)
        dt_list = [d[0] for d in dt_list]
        dt_list = sorted(dt_list)[::-1]
        date_selected = st.selectbox('Select date below', dt_list)
        score_q = "SELECT TENR_1, TENR_2, TENR_3, HRST, MR_FLTR, TRND_FLTR, MR_ER, MR_LB, TRND_ER, TRND_LB, CRTR, TRND_DLTA, DRCT, PRCE, DC_ANCR_PRCE,LC_ANCR_PRCE, LOCL_EXT_DATE, DC_CNFM_DATE, PREV_DC_THSD, CRNT_DSPS, CRNT_DC_THSD, CRNT_LC_THSD, DC_VOL FROM stratdb.tb_scnd_ma_trnd WHERE DATE_FORMAT(STR_TO_DATE(RCD_DATE, '%Y-%m-%d'),'%Y-%m-%d') = DATE_FORMAT(STR_TO_DATE('{}', '%Y-%m-%d'),'%Y-%m-%d')".format(date_selected)
        score_df = dbm.get_fetchall(score_q)
        score_df = pd.DataFrame(score_df, columns=['Tenor 1', 'Tenor 2', 'Tenor 3', 'Hurst Exponent', 'MR Filter', 'Trend Filter', 'MR Exp.Ret.', 'MR Lookback', 'Trend Exp.Ret.', 'Trend Lookback','Character', 'Trend Delta', 'Direction', 'Price', 'DC Anchor','LC Anchor', 'Local Extrema Date', 'Current Signal Date', 'Prev. DC Threshold', 'Current Disposition', 'Current DC Threshold','Current LC Threshold',  'DC Volatility'])
        score_df['MR Exp.Ret.'] = (score_df['MR Exp.Ret.']/100).map('{:.3%}'.format)
        score_df['Trend Exp.Ret.'] = (score_df['Trend Exp.Ret.']/100).map('{:.3%}'.format)
        score_df['Positioning Filter'] = ((score_df['Character'] > 0)&(np.sign(score_df['Trend Delta'])==np.sign(score_df['Direction'])))*1
        score_df['Current Signal Trigger'] = (score_df['Direction']*score_df['Prev. DC Threshold']).map('{:.3%}'.format)
        score_df['Current Disposition 150d'] = (score_df['Direction']*score_df['Current Disposition']).map('{:.3%}'.format)
        ret_after_inclusion = []
        for i in range(len(score_df)):
            signal_date = score_df.iloc[i]['Current Signal Date']
            if signal_date == None:
                ret_after_inclusion.append(np.nan)
            else:
                strategy_list = [score_df.iloc[i]['Tenor 1'], score_df.iloc[i]['Tenor 2'], score_df.iloc[i]['Tenor 3']]
                strategy_list = [t for t in strategy_list if t!=None]
                current_price = score_df.iloc[i]['Price']
                direction = score_df.iloc[i]['Direction']
                ret = strategy_return_after_inclusion(strategy_list, strategy_set, signal_date, current_price, direction)
                ret_after_inclusion.append(ret)
        score_df['Current Signal Ret.'] = ret_after_inclusion
        score_df['Current Signal Ret.'] = score_df['Current Signal Ret.'].map('{:.3%}'.format)
        score_df['Next Signal Trigger'] = (score_df['Direction']*score_df['Current DC Threshold']*-1).map('{:.3%}'.format)
        score_df['Current Disposition Local Ext.'] = (score_df['Price']/score_df['DC Anchor']-1).map('{:.3%}'.format)
        score_df['Next Signal Gap'] = ((score_df['Direction']*score_df['Current DC Threshold']*-1) - (score_df['Price']/score_df['DC Anchor']-1)).map('{:.2%}'.format)
        score_df = score_df[['Tenor 1', 'Tenor 2', 'Tenor 3','Direction', 'Positioning Filter','Character','Hurst Exponent', 'MR Filter', 'Trend Filter', 'MR Exp.Ret.', 'MR Lookback', 'Trend Exp.Ret.', 'Trend Lookback', 'Trend Delta', 'Price','Current Signal Date', 'Current Signal Trigger', 'Current Signal Ret.', 'Current Disposition 150d', 'Next Signal Trigger', 'Current Disposition Local Ext.', 'Next Signal Gap']]
        score_df = score_df.replace({np.nan:None})
        score_df = score_df.replace({'nan%':None})
        st.dataframe(score_df, hide_index=True, height=900, column_config={"widgets": st.column_config.Column(width='large')})

        st.download_button(label="Download data as CSV",data= convert_df(score_df),file_name='MA_Trend_Following_{}.csv'.format(date_selected), mime='text/csv')
    
    with tab2:
        ticker_name_match_dict_commodity = {'CL1 Comdty':'Crude Oil','XB1 Comdty':'Gasoline','HO1 Comdty':'Heating Oil','NG1 Comdty':'Natural Gas','GC1 Comdty':'Gold','SI1 Comdty':'Silver','HG1 Comdty':'Copper','PL1 Comdty':'Platinum','PA1 Comdty':'Palladium','C 1 Comdty':'Corn','S 1 Comdty':'Soybean','BO1 Comdty':'Soybean Oil','W 1 Comdty':'Wheat','KW1 Comdty':'Kensas Wheat','CT1 Comdty':'Cotton','KC1 Comdty':'Coffee','SB1 Comdty':'Sugar','LC1 Comdty':'Live Cattle','LH1 Comdty':'Lean Hog'} 
        ticker_name_match_dict_rates = {'KE1 Comdty':'Korea 3Y','KAA1 Comdty':'Korea 10Y','ED4 Comdty':'Eurodollar','SFR4 Comdty':'SOFR 1Y','TU1 Comdty':'US 2Y','FV1 Comdty':'US 5Y','TY1 Comdty':'US 10Y','UXY1 Comdty':'Ultra US 10Y', 'SSY4 Comdty':'Saron 1Y', 'ER4 Comdty':'Euribor 1Y', 'DU1 Comdty':'Germany 2Y','OE1 Comdty':'Germany 5Y','RX1 Comdty':'Germany 10Y','G 1 Comdty':'UK 10Y','OAT1 Comdty':'France 10Y','BTS1 Comdty':'Italy 3Y','IK1 Comdty':'Italy 10Y','JB1 Comdty':'Japan 10Y'} 
        ticker_name_match_dict_fx = {'EC1 Curncy':'EUR','JY1 Curncy':'JPY','AD1 Curncy':'AUD','BP1 Curncy':'GBP','CD1 Curncy':'CAD','SF1 Curncy':'CHF','NV1 Curncy':'NZD'} 
        ticker_name_match_dict_equity = {'ES1 Index':'S&P500','NQ1 Index':'Nasdaq100','DM1 Index':'DowJones','KM1 Index':'KOSPI200','KST1 Index':'KQ150', 'VG1 Index':'EuroStoxx50','Z 1 Index':'FTSE100','GX1 Index':'DAX','XP1 Index':'ASX200','XU1 Index':'FTSE China A50','NK1 Index':'Nikkei225','HC1 Index':'HSCEI', 'HI1 Index':'Hang Seng'} 
        commodity_ticker = dict(zip(ticker_name_match_dict_commodity.keys(), ['Commodity']*len(ticker_name_match_dict_commodity.keys())))
        rates_ticker =  dict(zip(ticker_name_match_dict_rates.keys(), ['Rates']*len(ticker_name_match_dict_rates.keys())))
        fx_ticker =  dict(zip(ticker_name_match_dict_fx.keys(), ['FX']*len(ticker_name_match_dict_fx.keys())))
        equity_ticker =  dict(zip(ticker_name_match_dict_equity.keys(), ['Equity']*len(ticker_name_match_dict_equity.keys())))

        ticker_name_match_dict = dict_merge(ticker_name_match_dict_rates, dict_merge(ticker_name_match_dict_commodity, dict_merge(ticker_name_match_dict_fx, ticker_name_match_dict_equity)))
        ticker_asset_match_dict = dict_merge(rates_ticker, dict_merge(commodity_ticker, dict_merge(fx_ticker, equity_ticker)))
        dispaly_order = dict(zip(ticker_name_match_dict.keys(), [i for i in range(len(ticker_name_match_dict.keys()))]))
        
        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                search_date_1 = datetime.strftime(st.date_input('Price Trend Position Date'), "%Y-%m-%d")
                working_date = sorted(list(set(price_trend_pos_df['Date'])))
                if search_date_1 in working_date:
                    search_date_1_ = search_date_1
                else:
                    working_date.append(search_date_1)
                    working_date = sorted(working_date)
                    search_date_1_ = working_date[working_date.index(search_date_1)-1]

            with col2:
                search_date_2 = datetime.strftime(st.date_input('Macro Trend Position Date'), "%Y-%m-%d")
                working_date = sorted(list(set(price_trend_pos_df['Date'])))
                if search_date_2 in working_date:
                    search_date_2_ = search_date_2
                else:
                    working_date.append(search_date_2)
                    working_date = sorted(working_date)
                    search_date_2_ = working_date[working_date.index(search_date_2)-1]
            
            with col3:
                search_date_3 = datetime.strftime(st.date_input('Macro Factor Trend Position Date'), "%Y-%m-%d")
                working_date = sorted(list(set(price_trend_pos_df['Date'])))
                if search_date_3 in working_date:
                    search_date_3_ = search_date_3
                else:
                    working_date.append(search_date_3)
                    working_date = sorted(working_date)
                    search_date_3_ = working_date[working_date.index(search_date_3)-1]
            

        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                price_trend_pos_display = price_trend_pos_df[price_trend_pos_df['Date']==search_date_1_]
                price_trend_pos_display['Name'] = [ticker_name_match_dict[t] for t in price_trend_pos_display['Ticker']]
                price_trend_pos_display['Asset'] = [ticker_asset_match_dict[t] for t in price_trend_pos_display['Ticker']]
                price_trend_pos_display = price_trend_pos_display.sort_values(by=['Ticker'], key=lambda x: x.map(dispaly_order))

                st.markdown("**Rates : Price Trend**")
                st.dataframe(price_trend_pos_display[price_trend_pos_display['Asset']=='Rates'][['Ticker', 'Name', 'Position']].set_index('Ticker'), use_container_width=True)
                st.markdown("**Commodity : Price Trend**")
                st.dataframe(price_trend_pos_display[price_trend_pos_display['Asset']=='Commodity'][['Ticker', 'Name', 'Position']].set_index('Ticker'), use_container_width=True)
                st.markdown("**FX : Price Trend**")
                st.dataframe(price_trend_pos_display[price_trend_pos_display['Asset']=='FX'][['Ticker', 'Name', 'Position']].set_index('Ticker'), use_container_width=True)
                st.markdown("**Equity : Price Trend**")
                st.dataframe(price_trend_pos_display[price_trend_pos_display['Asset']=='Equity'][['Ticker', 'Name', 'Position']].set_index('Ticker'), use_container_width=True)
                
            with col2:
                signal_dt = signal_df[signal_df.index==search_date_2_].T
                signal_dict = dict(zip(signal_dt.index, np.round(signal_dt.values.reshape(-1),3)))

                macro_trend_pos_display = macro_trend_pos_df[macro_trend_pos_df['Date']==search_date_2_]
                macro_trend_pos_display['Name'] = [ticker_name_match_dict[t] for t in macro_trend_pos_display['Ticker']]
                macro_trend_pos_display['Asset'] = [ticker_asset_match_dict[t] for t in macro_trend_pos_display['Ticker']]
                macro_trend_pos_display['Delta'] = [signal_dict[t] for t in macro_trend_pos_display['Ticker']]
                macro_trend_pos_display = macro_trend_pos_display.sort_values(by=['Ticker'], key=lambda x: x.map(dispaly_order))

                st.markdown("**Rates : Macro Trend**")
                st.dataframe(macro_trend_pos_display[macro_trend_pos_display['Asset']=='Rates'][['Ticker', 'Name', 'Position', 'Delta']].set_index('Ticker'), use_container_width=True)
                st.markdown("**Commodity : Macro Trend**")
                st.dataframe(macro_trend_pos_display[macro_trend_pos_display['Asset']=='Commodity'][['Ticker', 'Name', 'Position', 'Delta']].set_index('Ticker'), use_container_width=True)
                st.markdown("**FX : Macro Trend**")
                st.dataframe(macro_trend_pos_display[macro_trend_pos_display['Asset']=='FX'][['Ticker', 'Name', 'Position', 'Delta']].set_index('Ticker'), use_container_width=True)
                st.markdown("**Equity : Macro Trend**")
                st.dataframe(macro_trend_pos_display[macro_trend_pos_display['Asset']=='Equity'][['Ticker', 'Name', 'Position', 'Delta']].set_index('Ticker'), use_container_width=True)
            
            with col3:
                signal_indi_dt = signal_indi_df[signal_indi_df.index==search_date_3_].T
                signal_indi_dict = dict(zip(signal_indi_dt.index, np.round(signal_indi_dt.values.reshape(-1),3)))

                macro_factor_trend_pos_display = macro_factor_trend_pos_df[macro_factor_trend_pos_df['Date']==search_date_3_]
                macro_factor_trend_pos_display['Name'] = [ticker_name_match_dict[t] for t in macro_factor_trend_pos_display['Ticker']]
                macro_factor_trend_pos_display['Asset'] = [ticker_asset_match_dict[t] for t in macro_factor_trend_pos_display['Ticker']]
                macro_factor_trend_pos_display['Delta'] = [signal_indi_dict[t] for t in macro_factor_trend_pos_display['Ticker']]
                macro_factor_trend_pos_display = macro_factor_trend_pos_display.sort_values(by=['Ticker'], key=lambda x: x.map(dispaly_order))

                st.markdown("**Rates : Macro Factor Trend**")
                st.dataframe(macro_factor_trend_pos_display[macro_factor_trend_pos_display['Asset']=='Rates'][['Ticker', 'Name', 'Position', 'Delta']].set_index('Ticker'), use_container_width=True)
                st.markdown("**Commodity : Macro Factor Trend**")
                st.dataframe(macro_factor_trend_pos_display[macro_factor_trend_pos_display['Asset']=='Commodity'][['Ticker', 'Name', 'Position', 'Delta']].set_index('Ticker'), use_container_width=True)
                st.markdown("**FX : Macro Factor Trend**")
                st.dataframe(macro_factor_trend_pos_display[macro_factor_trend_pos_display['Asset']=='FX'][['Ticker', 'Name', 'Position', 'Delta']].set_index('Ticker'), use_container_width=True)
                st.markdown("**Equity : Macro Factor Trend**")
                st.dataframe(macro_factor_trend_pos_display[macro_factor_trend_pos_display['Asset']=='Equity'][['Ticker', 'Name', 'Position', 'Delta']].set_index('Ticker'), use_container_width=True)
                
            with col4:
                composite_pos = pd.concat([price_trend_pos_display[['Ticker', 'Position']].set_index('Ticker'), macro_trend_pos_display[['Ticker', 'Position']].set_index('Ticker'), macro_factor_trend_pos_display[['Ticker', 'Position']].set_index('Ticker')], axis=1).fillna(0)
                composite_pos_display = pd.DataFrame(composite_pos.sum(axis=1), columns=['Position']).reset_index()
                composite_pos_display['Name'] = [ticker_name_match_dict[t] for t in composite_pos_display['Ticker']]
                composite_pos_display['Asset'] =  [ticker_asset_match_dict[t] for t in composite_pos_display['Ticker']]
                composite_pos_display = composite_pos_display.sort_values(by=['Ticker'], key=lambda x: x.map(dispaly_order))

                st.markdown("**Rates : Composite**")
                st.dataframe(composite_pos_display[composite_pos_display['Asset']=='Rates'][['Ticker', 'Name', 'Position']].set_index('Ticker'), use_container_width=True)
                st.markdown("**Commodity : Composite**")
                st.dataframe(composite_pos_display[composite_pos_display['Asset']=='Commodity'][['Ticker', 'Name', 'Position']].set_index('Ticker'), use_container_width=True)
                st.markdown("**FX : Composite**")
                st.dataframe(composite_pos_display[composite_pos_display['Asset']=='FX'][['Ticker', 'Name', 'Position']].set_index('Ticker'), use_container_width=True)
                st.markdown("**Equity : Composite**")
                st.dataframe(composite_pos_display[composite_pos_display['Asset']=='Equity'][['Ticker', 'Name', 'Position']].set_index('Ticker'), use_container_width=True)
                
        st.divider()
        with st.container():
            macro_trend_pl_ = macro_trend_pl_df.groupby('Date').sum()
            macro_trend_pl_ = macro_trend_pl_.cumsum()
            macro_trend_pl_.columns = ['Macro Trend']

            macro_factor_trend_pl_ = macro_factor_trend_pl_df.groupby('Date').sum()
            macro_factor_trend_pl_ = macro_factor_trend_pl_.cumsum()/2
            macro_factor_trend_pl_.columns = ['Macro Factor Trend 1/2']

            price_trend_pl_ = price_trend_pl_df.groupby('Date').sum()
            price_trend_pl_ = price_trend_pl_[price_trend_pl_.index>=macro_trend_pl_.index[0]]
            price_trend_pl_ =  price_trend_pl_.cumsum()
            price_trend_pl_.columns = ['Price Trend']
            trend_pl = pd.concat([price_trend_pl_, macro_trend_pl_, macro_factor_trend_pl_], axis=1).sort_index().fillna(method='ffill').reset_index()

            fig = px.line(trend_pl, x='Date', y=trend_pl.columns,hover_data={'Date': "|%B %d, %Y"},title='Strategy in PL')    
            fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            
            st.plotly_chart(fig, use_container_width=True)
        
        with st.container():
            trend_on_trend_delta = trend_on_trend.reset_index()
            fig = px.line(trend_on_trend_delta, x='Date', y=trend_on_trend_delta.columns,hover_data={'Date': "|%B %d, %Y"},title='Macro Trend Strategy Delta : {}'.format(trend_on_trend_delta['Rebalance Delta'].values.tolist()[-1]))    
            fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            
            st.plotly_chart(fig, use_container_width=True)
        
        with st.container():
            trend_on_trend_indi_delta = trend_on_trend_indi.reset_index()
            fig = px.line(trend_on_trend_indi_delta, x='Date', y=trend_on_trend_indi_delta.columns,hover_data={'Date': "|%B %d, %Y"},title='Macro Factor Trend Strategy Delta : {}'.format(trend_on_trend_indi_delta['Rebalance Delta'].values.tolist()[-1]))    
            fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                search_date_4 = datetime.strftime(st.date_input('Position Date'), "%Y-%m-%d")
                working_date = sorted(list(set(macro_trend_pos_df['Date'])))
                if search_date_4 in working_date:
                    search_date_4_ = search_date_4
                else:
                    working_date.append(search_date_4)
                    working_date = sorted(working_date)
                    search_date_4_ = working_date[working_date.index(search_date_4)-1]
                #st.write(macro_factor_delta.columns)
                macro_factor_delta_dt = macro_factor_delta[macro_factor_delta.index==search_date_4_].reset_index()[list(macro_factor_delta.columns)].T #macro_factor_delta[macro_factor_delta.index==search_date_3_].reset_index()[list(macro_factor_delta.columns)[1:]].T
                macro_factor_delta_dt.columns = ['Macro Delta']
                macro_factor_delta_dt.index.name = 'Macro Factor'
                st.markdown("**Macro Factor Delta**")
                st.dataframe(macro_factor_delta_dt,  height = 595, use_container_width=True)

            with col2:
                ticker_select = st.multiselect('Futures', list(ticker_name_match_dict.keys()), default='ES1 Index', max_selections=3)
                #_, _, macro_beta = mts.macro_trend_signal(mts.macro_factor_index, regression_lookback=60, ma_lookback=60, universe_list=ticker_select)
                macro_beta_dt = macro_beta[(macro_beta['Date']==search_date_4_)&(macro_beta['Ticker'].isin(ticker_select))]
                macro_beta_dt = macro_beta_dt[['Ticker']+list(macro_beta_dt.columns)[3:]+['mu']].set_index('Ticker').T
                st.markdown("**Futures Beta**")
                st.dataframe(macro_beta_dt,  height = 630, use_container_width=True)
        
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                #st.write(macro_factor_delta.columns)
                macro_indi_factor_delta_dt = macro_indi_factor_delta[macro_indi_factor_delta.index==search_date_4_].reset_index()[list(macro_indi_factor_delta.columns)].T #macro_factor_delta[macro_factor_delta.index==search_date_3_].reset_index()[list(macro_factor_delta.columns)[1:]].T
                macro_indi_factor_delta_dt.columns = ['Macro Delta']
                macro_indi_factor_delta_dt.index.name = 'Macro Factor'
                st.markdown("**Macro Factor Delta**")
                st.dataframe(macro_indi_factor_delta_dt,  height = 315, use_container_width=True)

            with col2:
                #_, _, macro_indi_beta = mts.macro_trend_signal(mts.macro_indi_factor_index, regression_lookback=60, ma_lookback=60, universe_list=ticker_select)
                macro_indi_beta_dt = macro_indi_beta[(macro_indi_beta['Date']==search_date_4_)&(macro_indi_beta['Ticker'].isin(ticker_select))]
                macro_indi_beta_dt = macro_indi_beta_dt[['Ticker']+list(macro_indi_beta_dt.columns)[3:]+['mu']].set_index('Ticker').T
                st.markdown("**Futures Beta**")
                st.dataframe(macro_indi_beta_dt,  height = 350, use_container_width=True)

            st.download_button(label="Download trend pl data as CSV",data= convert_df(trend_pl),file_name='Trend_PL{}.csv'.format(date.today().isoformat()), mime='text/csv')
            st.download_button(label="Download price trend data as CSV",data= convert_df(price_trend_pos_display.replace({np.nan:0})),file_name='Price_Trend_{}.csv'.format(search_date_1), mime='text/csv')
            st.download_button(label="Download macro trend data as CSV",data= convert_df(macro_trend_pos_display.replace({np.nan:0})),file_name='Macro_Trend_{}.csv'.format(search_date_2), mime='text/csv')
            st.download_button(label="Download macro factor trend data as CSV",data= convert_df(macro_factor_trend_pos_display.replace({np.nan:0})),file_name='Macro_Factor_Trend_{}.csv'.format(search_date_3), mime='text/csv')
            st.download_button(label="Download composite data as CSV",data= convert_df(composite_pos_display.replace({np.nan:0})),file_name='Composite_Trend_{}.csv'.format(search_date_2), mime='text/csv')
            
    
    with tab3:
        with st.container():   

            trend_port_pl_df = pd.DataFrame(trend_port_pl, columns = ['Trend Portfolio']).cumsum()
            trend_port_pl_df.index.name = 'Date'
            trend_port_pl_df = trend_port_pl_df.reset_index()
            fig = px.line(trend_port_pl_df, x='Date', y=trend_port_pl_df.columns,hover_data={'Date': "|%B %d, %Y"}, title='Trend Portfolio PL')    
            fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
        
            st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        with st.container():   
            col1, col2 = st.columns(2)
            with col1:
                trend_strat_ret_before = tpg.df_strt.copy()
                trend_strat_ret_before.columns = [c.lower() for c in trend_strat_ret_before.columns]
                trend_strat_ret_df = trend_strat_ret_before.cumsum().fillna(method='ffill').dropna(how='all')
                trend_strat_ret_df.index.name = 'Date'
                trend_strat_ret_df = trend_strat_ret_df.reset_index()
                fig = px.line(trend_strat_ret_df, x='Date', y=trend_strat_ret_df.columns,hover_data={'Date': "|%B %d, %Y"}, title='Trend Strategy PL')    
                fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
            
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                trend_strat_ret_m_df = trend_strat_ret[['price_trend', 'macro_trend', 'macro_factor_trend', 'ma_networkmomentum', 'fx_ctotmomentum']].cumsum().fillna(method='ffill').dropna(how='all')
                trend_strat_ret_m_df.index.name = 'Date'
                trend_strat_ret_m_df = trend_strat_ret_m_df.reset_index()
                fig = px.line(trend_strat_ret_m_df, x='Date', y=trend_strat_ret_m_df.columns,hover_data={'Date': "|%B %d, %Y"}, title='Trend Strategy Vol Skew Multiple PL')    
                fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
            
                st.plotly_chart(fig, use_container_width=True)
        
        st.divider()
        with st.container():
            col1, col2 = st.columns(2)
            with col1:
                search_dt = datetime.strftime(st.date_input('Trend Port Position Date'), "%Y-%m-%d")
                working_date = sorted([datetime.strftime(d, "%Y-%m-%d") for d in list(set(trend_port_pos.index))])
                if search_dt in working_date:
                    search_dt_ = search_dt
                else:
                    working_date.append(search_dt)
                    working_date = sorted(working_date)
                    search_dt_ = working_date[working_date.index(search_dt)-1]
            with col2:
                comparison_dt = datetime.strftime(st.date_input('Comparison Date', datetime.strptime(working_date[working_date.index(search_dt)-1], "%Y-%m-%d")), "%Y-%m-%d")
                working_date = sorted([datetime.strftime(d, "%Y-%m-%d") for d in list(set(trend_port_pos.index))])
                if comparison_dt in working_date:
                    comparison_dt_ = comparison_dt
                else:
                    working_date.append(comparison_dt)
                    working_date = sorted(working_date)
                    comparison_dt_ = working_date[working_date.index(comparison_dt)-1]
                
        with st.container():
            ticker_name_match_dict_commodity = {'CL1 Comdty':'Crude Oil','CO1 Comdty':'Brent Oil','XB1 Comdty':'Gasoline','HO1 Comdty':'Heating Oil','QS1 Comdty':'Gas Oil', 'NG1 Comdty':'Natural Gas','GC1 Comdty':'Gold','SI1 Comdty':'Silver','HG1 Comdty':'Copper','PL1 Comdty':'Platinum','PA1 Comdty':'Palladium','C 1 Comdty':'Corn','S 1 Comdty':'Soybean','BO1 Comdty':'Soybean Oil','W 1 Comdty':'Wheat','KW1 Comdty':'Kensas Wheat','CT1 Comdty':'Cotton','KC1 Comdty':'Coffee','CF1 Comdty':'Robusta Coffee','CC1 Comdty':'Cocoa', 'JO1 Comdty':'Orange Juice','SB1 Comdty':'Sugar','FC1 Comdty':'Feeder Cattle','LC1 Comdty':'Live Cattle','LH1 Comdty':'Lean Hog'} 
            ticker_name_match_dict_rates = {'KE1 Comdty':'Korea 3Y','KAA1 Comdty':'Korea 10Y','ED4 Comdty':'Eurodollar','SFR4 Comdty':'SOFR 1Y','TU1 Comdty':'US 2Y','FV1 Comdty':'US 5Y','TY1 Comdty':'US 10Y','UXY1 Comdty':'Ultra US 10Y', 'SSY4 Comdty':'Saron 1Y', 'ER4 Comdty':'Euribor 1Y', 'DU1 Comdty':'Germany 2Y','OE1 Comdty':'Germany 5Y','RX1 Comdty':'Germany 10Y','G 1 Comdty':'UK 10Y','OAT1 Comdty':'France 10Y','BTS1 Comdty':'Italy 3Y','IK1 Comdty':'Italy 10Y','JB1 Comdty':'Japan 10Y'} 
            ticker_name_match_dict_fx = {'EC1 Curncy':'EUR','JY1 Curncy':'JPY','AD1 Curncy':'AUD','BP1 Curncy':'GBP','CD1 Curncy':'CAD','SF1 Curncy':'CHF','NV1 Curncy':'NZD', 'PE1 Curncy':'MXN', 'BR1 Curncy':'BRL', 'RU1 Curncy':'RUB', 'RA1 Curncy':'RUB', 'SIR1 Curncy':'INR'} 
            ticker_name_match_dict_equity = {'ES1 Index':'S&P500','NQ1 Index':'Nasdaq100','DM1 Index':'DowJones','RTY1 Index':'Russell2000', 'FA1 Index':'S&P MidCap 400','KM1 Index':'KOSPI200','KST1 Index':'KQ150', 'VG1 Index':'EuroStoxx50','Z 1 Index':'FTSE100','GX1 Index':'DAX','CF1 Index':'CAC40', 'XP1 Index':'ASX200','XU1 Index':'FTSE China A50','NK1 Index':'Nikkei225','NX1 Index':'Nikkei225 USD','HC1 Index':'HSCEI', 'HI1 Index':'Hang Seng'} 
            commodity_ticker = dict(zip(ticker_name_match_dict_commodity.keys(), ['Commodity']*len(ticker_name_match_dict_commodity.keys())))
            rates_ticker =  dict(zip(ticker_name_match_dict_rates.keys(), ['Rates']*len(ticker_name_match_dict_rates.keys())))
            fx_ticker =  dict(zip(ticker_name_match_dict_fx.keys(), ['FX']*len(ticker_name_match_dict_fx.keys())))
            equity_ticker =  dict(zip(ticker_name_match_dict_equity.keys(), ['Equity']*len(ticker_name_match_dict_equity.keys())))

            ticker_name_match_dict = dict_merge(ticker_name_match_dict_rates, dict_merge(ticker_name_match_dict_commodity, dict_merge(ticker_name_match_dict_fx, ticker_name_match_dict_equity)))
            ticker_asset_match_dict = dict_merge(rates_ticker, dict_merge(commodity_ticker, dict_merge(fx_ticker, equity_ticker)))
            dispaly_order = dict(zip(ticker_name_match_dict.keys(), [i for i in range(len(ticker_name_match_dict.keys()))]))
            
            trend_port_pos_display_s = trend_port_pos[trend_port_pos.index==search_dt_]
            trend_port_pos_display_s = trend_port_pos_display_s.T
            trend_port_pos_display_c = trend_port_pos[trend_port_pos.index==comparison_dt_]
            trend_port_pos_display_c = trend_port_pos_display_c.T
            if search_dt_!=comparison_dt_:
                trend_port_pos_display = pd.concat([trend_port_pos_display_s, trend_port_pos_display_c], axis=1).reset_index()
                trend_port_pos_display.columns = ['Ticker', search_dt_, comparison_dt_]
                trend_port_pos_display['Name'] = [ticker_name_match_dict[t] for t in trend_port_pos_display['Ticker']]
                trend_port_pos_display['Asset'] = [ticker_asset_match_dict[t] for t in trend_port_pos_display['Ticker']]
                trend_port_pos_display['Change'] = trend_port_pos_display[search_dt_] - trend_port_pos_display[comparison_dt_]
                trend_port_pos_display = trend_port_pos_display.sort_values(by=['Ticker'], key=lambda x: x.map(dispaly_order))
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown("**Rates : Trend Portfolio**")
                    st.dataframe(trend_port_pos_display[trend_port_pos_display['Asset']=='Rates'][['Ticker', 'Name', search_dt_, comparison_dt_, 'Change']].set_index('Ticker'), height=635, use_container_width=True)
                with col2:
                    st.markdown("**Commodity : Trend Portfolio**")
                    st.dataframe(trend_port_pos_display[trend_port_pos_display['Asset']=='Commodity'][['Ticker', 'Name', search_dt_, comparison_dt_, 'Change']].set_index('Ticker'), height=635, use_container_width=True)
                with col3:
                    st.markdown("**FX : Trend Portfolio**")
                    st.dataframe(trend_port_pos_display[trend_port_pos_display['Asset']=='FX'][['Ticker', 'Name', search_dt_, comparison_dt_, 'Change']].set_index('Ticker'), height=635, use_container_width=True)
                with col4:
                    st.markdown("**Equity : Trend Portfolio**")
                    st.dataframe(trend_port_pos_display[trend_port_pos_display['Asset']=='Equity'][['Ticker', 'Name', search_dt_, comparison_dt_, 'Change']].set_index('Ticker'), height=635, use_container_width=True)
                    
            else:
                trend_port_pos_display = trend_port_pos_display_s.copy().reset_index()
                trend_port_pos_display.columns = ['Ticker', search_dt_]
                trend_port_pos_display['Name'] = [ticker_name_match_dict[t] for t in trend_port_pos_display['Ticker']]
                trend_port_pos_display['Asset'] = [ticker_asset_match_dict[t] for t in trend_port_pos_display['Ticker']]
                trend_port_pos_display['Change'] = 0
                trend_port_pos_display = trend_port_pos_display.sort_values(by=['Ticker'], key=lambda x: x.map(dispaly_order))
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown("**Rates : Trend Portfolio**")
                    st.dataframe(trend_port_pos_display[trend_port_pos_display['Asset']=='Rates'][['Ticker', 'Name', search_dt_, 'Change']].set_index('Ticker'), height=635, use_container_width=True)
                with col2:
                    st.markdown("**Commodity : Trend Portfolio**")
                    st.dataframe(trend_port_pos_display[trend_port_pos_display['Asset']=='Commodity'][['Ticker', 'Name', search_dt_, 'Change']].set_index('Ticker'), height=635, use_container_width=True)
                with col3:
                    st.markdown("**FX : Trend Portfolio**")
                    st.dataframe(trend_port_pos_display[trend_port_pos_display['Asset']=='FX'][['Ticker', 'Name', search_dt_,'Change']].set_index('Ticker'), height=635, use_container_width=True)
                with col4:
                    st.markdown("**Equity : Trend Portfolio**")
                    st.dataframe(trend_port_pos_display[trend_port_pos_display['Asset']=='Equity'][['Ticker', 'Name', search_dt_,'Change']].set_index('Ticker'), height=635, use_container_width=True)
                    
            
        st.divider()
        with st.container():
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Vol Skew Strategy Multiplier**")
                st.dataframe(vol_skew_weight[['price_trend', 'macro_trend', 'macro_factor_trend', 'ma_networkmomentum', 'fx_ctotmomentum']].sort_index(ascending=False), height = 380, use_container_width=True)

            with col2:
                vol_skew_weight_fig = vol_skew_weight[['price_trend', 'macro_trend', 'macro_factor_trend', 'ma_networkmomentum', 'fx_ctotmomentum']].sort_index()
                vol_skew_weight_fig.index.name = 'Date'
                vol_skew_weight_fig = vol_skew_weight_fig.reset_index()
                fig = px.line(vol_skew_weight_fig, x='Date', y=vol_skew_weight_fig.columns,hover_data={'Date': "|%B %d, %Y"})    
                fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
            
                st.plotly_chart(fig, use_container_width=True)
        
        
        st.download_button(label="Download Trend_Port_PL data as CSV",data= convert_df(trend_port_pl_df),file_name='Trend_Port_PL_{}.csv'.format(date.today().isoformat()), mime='text/csv')
        st.download_button(label="Download Trend_Strat_PL data as CSV",data= convert_df(trend_strat_ret_df),file_name='Trend_Strat_PL_{}.csv'.format(date.today().isoformat()), mime='text/csv')
        st.download_button(label="Download Trend_Strat_Weighted_PL data as CSV",data= convert_df(trend_strat_ret_m_df),file_name='Trend_Strat_Weighted_PL_{}.csv'.format(date.today().isoformat()), mime='text/csv')
        st.download_button(label="Download Trend_Port_Position data as CSV",data= convert_df(trend_port_pos),file_name='Trend_Port_Position_{}.csv'.format(date.today().isoformat()), mime='text/csv')
        st.download_button(label="Download Trend_Port_Vol_Skew_Multiplier data as CSV",data= convert_df(vol_skew_weight_fig),file_name='Trend_Port_Vol_Skew_Multiple_{}.csv'.format(date.today().isoformat()), mime='text/csv')
        
    
    with tab4:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            option_1 = st.multiselect('Futures', strategy_list_futures, default=None, max_selections=10)
        with col2: 
            option_2 = st.multiselect('Rates', outright_list, default=None, max_selections=3)
            if len(option_2)>0:
                option_2 = [get_strategy_name(option_2, mapdp)]
            with st.expander('Additional Rates'):
                option_2_ = st.multiselect('Rates ', outright_list, default=None, max_selections=3)
                if len(option_2_)>0:
                    option_2_ = [get_strategy_name(option_2_, mapdp)]
                option_2__ = st.multiselect('Rates  ', outright_list, default=None, max_selections=3)
                if len(option_2__)>0:
                    option_2__ = [get_strategy_name(option_2__, mapdp)]
                option_2___ = st.multiselect('Rates   ', outright_list, default=None, max_selections=3)
                if len(option_2___)>0:
                    option_2___ = [get_strategy_name(option_2___, mapdp)]
        with col3:
            option_3 = st.multiselect('Risk Premia', strategy_list_rp, default=None, max_selections=10)
        with col4:
            option_4 = st.multiselect('Macro Factor', strategy_list_macrofactor+strategy_list_macroindifactor, default=None, max_selections=10)
        
        strategy_selected = []
        strategy_series_tr_to_chart = {}
        strategy_series_tr_to_chart_adj = {}
        strategy_series_tr_to_chart_z = {}
        if len(option_1) > 0:
            strategy_selected_1, strategy_selected_series_tr_1 = get_strategy(option_1)
            strategy_selected_series_tr_1_adj = strategy_selected_series_tr_1/strategy_selected_series_tr_1.dropna().values[0]
            strategy_selected += strategy_selected_1
            strategy_series_tr_to_chart['futures'] = strategy_selected_series_tr_1
            strategy_series_tr_to_chart_adj['futures'] = strategy_selected_series_tr_1_adj
            
        if len(option_2) > 0:
            strategy_selected_2, strategy_selected_series_tr_2 = get_strategy(option_2)
            strategy_selected_series_tr_2_adj = strategy_selected_series_tr_2/strategy_selected_series_tr_2.dropna().values[0]
            strategy_selected += strategy_selected_2
            strategy_series_tr_to_chart['rates'] = strategy_selected_series_tr_2
            strategy_series_tr_to_chart_adj['rates'] = strategy_selected_series_tr_2_adj
            
            if len(option_2_) > 0:
                strategy_selected_2_, strategy_selected_series_tr_2_ = get_strategy(option_2_)
                strategy_selected_series_tr_2__adj = strategy_selected_series_tr_2_/strategy_selected_series_tr_2_.dropna().values[0]
                strategy_selected += strategy_selected_2_
                strategy_series_tr_to_chart['rates_'] = strategy_selected_series_tr_2_
                strategy_series_tr_to_chart_adj['rates_'] = strategy_selected_series_tr_2__adj
                
            if len(option_2__) > 0:
                strategy_selected_2__, strategy_selected_series_tr_2__ = get_strategy(option_2__)
                strategy_selected_series_tr_2___adj = strategy_selected_series_tr_2__/strategy_selected_series_tr_2__.dropna().values[0]
                strategy_selected += strategy_selected_2__
                strategy_series_tr_to_chart['rates__'] = strategy_selected_series_tr_2__
                strategy_series_tr_to_chart_adj['rates__'] = strategy_selected_series_tr_2___adj
                
            if len(option_2___) > 0:
                strategy_selected_2___, strategy_selected_series_tr_2___ = get_strategy(option_2___)
                strategy_selected_series_tr_2____adj = strategy_selected_series_tr_2___/strategy_selected_series_tr_2___.dropna().values[0]
                strategy_selected += strategy_selected_2___
                strategy_series_tr_to_chart['rates___'] = strategy_selected_series_tr_2___
                strategy_series_tr_to_chart_adj['rates___'] = strategy_selected_series_tr_2____adj
                
        if len(option_3) > 0:
            strategy_selected_3, strategy_selected_series_tr_3 = get_strategy(option_3)
            strategy_selected_series_tr_3_adj = strategy_selected_series_tr_3/strategy_selected_series_tr_3.dropna().values[0]
            strategy_selected += strategy_selected_3
            strategy_series_tr_to_chart['riskpremia'] = strategy_selected_series_tr_3
            strategy_series_tr_to_chart_adj['riskpremia'] = strategy_selected_series_tr_3_adj
            
        if len(option_4) > 0:
            strategy_selected_4, strategy_selected_series_tr_4 = get_strategy(option_4)
            strategy_selected_series_tr_4_adj = strategy_selected_series_tr_4/strategy_selected_series_tr_4.dropna().values[0]
            strategy_selected += strategy_selected_4
            strategy_series_tr_to_chart['macrofactor'] = strategy_selected_series_tr_4
            strategy_series_tr_to_chart_adj['macrofactor'] = strategy_selected_series_tr_4_adj

        if len(strategy_selected)>0:
            strategy_series_tr_to_chart_df = dict_to_df(strategy_series_tr_to_chart)
            strategy_series_tr_to_chart_df_adj = dict_to_df(strategy_series_tr_to_chart_adj)
            strategy_series_tr_to_chart_df.columns = [str(c) for c in strategy_selected]
            strategy_series_tr_to_chart_df_adj.columns = [str(c) for c in strategy_selected]
            
            with st.container():
                strategy_series_to_chart_df_ = strategy_series_tr_to_chart_df.reset_index()
                strategy_series_to_chart_df_ = strategy_series_to_chart_df_.rename(columns={'index':'date'})

                fig = px.line(strategy_series_to_chart_df_, x='date', y=strategy_series_to_chart_df_.columns,hover_data={'date': "|%B %d, %Y"},title='Strategy in price')    
                fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                st.plotly_chart(fig, use_container_width=True)
                
            with st.container():
                strategy_series_tr_to_chart_df_adj_ = strategy_series_tr_to_chart_df_adj.reset_index()
                strategy_series_tr_to_chart_df_adj_ = strategy_series_tr_to_chart_df_adj_.rename(columns={'index':'date'})

                fig = px.line(strategy_series_tr_to_chart_df_adj_, x='date', y=strategy_series_tr_to_chart_df_adj_.columns,hover_data={'date': "|%B %d, %Y"},title='Strategy in %')    
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
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]))
                
                elif len(strategy_selected) == 2:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                       yaxis2=dict(anchor="x",overlaying="y",side="right"))
                
                elif len(strategy_selected) == 3:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                       yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                       yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 4:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.92]),
                                       yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                       yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                       yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 5:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.92]),
                                       yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.015),
                                       yaxis3=dict(anchor="x",overlaying="y",side="right"),
                                       yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                       yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 6:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.90]),
                                       yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.015),
                                       yaxis3=dict(anchor="x",overlaying="y",side="right"),
                                       yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.93),
                                       yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.955), 
                                       yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.98))
                
                elif len(strategy_selected) == 7:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.065, 0.90]),
                                       yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                       yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                       yaxis4=dict(anchor="x",overlaying="y",side="right"),
                                       yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.93), 
                                       yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                       yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.98))
                    
                elif len(strategy_selected) == 8:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][7]], name=[str(c) for c in strategy_selected][7], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y8"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.065, 0.865]),
                                       yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                       yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                       yaxis4=dict(anchor="x",overlaying="y",side="right"),
                                       yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.90), 
                                       yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.93),
                                       yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.96), 
                                       yaxis8=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 9:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][7]], name=[str(c) for c in strategy_selected][7], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y8"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][8]], name=[str(c) for c in strategy_selected][8], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y9"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.095, 0.865]),
                                       yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.06),
                                       yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                       yaxis4=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                       yaxis5=dict(anchor="x",overlaying="y",side="right"), 
                                       yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.90),
                                       yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.93), 
                                       yaxis8=dict(anchor="free",overlaying="y",side="right", position=0.96),
                                       yaxis9=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 10:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][7]], name=[str(c) for c in strategy_selected][7], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y8"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][8]], name=[str(c) for c in strategy_selected][8], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y9"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][9]], name=[str(c) for c in strategy_selected][9], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y10"))
                    
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
                
                
