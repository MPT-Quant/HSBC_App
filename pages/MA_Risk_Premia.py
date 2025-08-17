file_dir = 'C:\\Users\\kimju\\MPT-Quant\\MacroTrading'
css_dir = 'C:\\Users\\kimju\\MPT-Quant\\SystemMacro_App\\pages\\style.css'

import streamlit as st
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from datetime import datetime
import statsmodels.api as sm
import time
from datetime import date
import pandas as pd
import numpy as np
import sys
sys.path.append(file_dir)
from Strategy_MA_Optimal_Portfolio import RegimeDetection
from Strategy_MA_Risk_Premia import RiskPremiaPosition, RiskPremiaAllocation
from Strategy_Rates_Portfolio import RatesDataProcess
from Strategy_FX_Portfolio import FXDataProcess
from Strategy_Commodity_Portfolio import CommodityDataProcessLite
from Strategy_Equity_Portfolio import EquityDataProcess
from MPTSRT_StratDB import db_execute_manager as dbm_s
#dbm = dbm_s.DBExecuteManager()

if 'note' not in st.session_state:
    st.session_state.note = ''
   
st.session_state.note = st.sidebar.text_area('Note', st.session_state.note, height=300)
pd.set_option('mode.chained_assignment',  None)

@st.cache_resource
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

@st.cache_resource(show_spinner=False)
def pull_data_functions():
    rpa = RiskPremiaAllocation()
    #rpp = RiskPremiaPosition()
    #rdp = rpa.rdp #RatesDataProcess(rpp.dataprocess_parameter_rates)
    #cdp = rpa.cdp #CommodityDataProcessLite(rpp.dataprocess_parameter_commodity)
    #fdp = rpa.fdp #FXDataProcess(rpp.dataprocess_parameter_fx)
    #edp = rpa.edp #EquityDataProcess(rpp.dataprocess_parameter_equity)
    return rpa, rpa.rdp, rpa.cdp, rpa.fdp, rpa.edp #, rpp 

@st.cache_data(show_spinner=False)
def get_feature_list():
    dbm = dbm_s.DBExecuteManager()
    s_q = "SELECT Distinct STRT_NAME FROM stratdb.tb_scnd_rp_pl;"
    s_list = dbm.get_fetchall(s_q)
    s_list = [x[0] for x in s_list]
    return s_list

@st.cache_data(show_spinner=False)
def get_substrat_pl(dbm):
    pl_q = "SELECT RCD_DATE, PNL, STRT_NAME FROM stratdb.tb_scnd_rp_pl;"
    pl_list = dbm.get_fetchall(pl_q)
    pl_list = [list(x) for x in pl_list]
    pl_df = pd.DataFrame(pl_list, columns=['Date', 'PL', 'Strategy'])
    return pl_df

@st.cache_data(show_spinner=False)
def get_substrat_pos(dbm):
    pos_q = "SELECT RCD_DATE, TCKR, POS, STRT_NAME FROM stratdb.tb_scnd_rp_pos;"
    pos_list = dbm.get_fetchall(pos_q)
    pos_list = [list(x) for x in pos_list]
    pos_df = pd.DataFrame(pos_list, columns=['Date', 'Ticker', 'Position', 'Strategy'])
    return pos_df

@st.cache_resource(show_spinner=False)
def pull_strategy_data_series():
    dbm = dbm_s.DBExecuteManager()
    pos = get_substrat_pos(dbm)
    pl = get_substrat_pl(dbm)
    pl_df = pl.pivot(index='Date', columns='Strategy', values='PL')
    pl_df.columns.name = None
    pl_df.index.name = None
    
    #Position
    feature_pos = pos[pos['Strategy'].isin(feature_list)]
    substrat_pos = pos[pos['Strategy'].isin(substrat_list)]
    for i, d in enumerate(strat_sub_main_match_dict.items()):
        if i == 0:
            k = d[0]
            v = d[1]
            main_pos_ = pos[pos['Strategy'].isin(v)]   
            main_pos_ = main_pos_.groupby(['Date', 'Ticker']).sum().reset_index('Date').reset_index('Ticker')
            main_pos_['Strategy'] = k
            main_pos = main_pos_[['Date', 'Ticker', 'Position', 'Strategy']]
        else:
            k = d[0]
            v = d[1]
            main_pos_ = pos[pos['Strategy'].isin(v)]   
            main_pos_ = main_pos_.groupby(['Date', 'Ticker']).sum().reset_index('Date').reset_index('Ticker')
            main_pos_['Strategy'] = k
            main_pos_ = main_pos_[['Date', 'Ticker', 'Position', 'Strategy']]
            main_pos = pd.concat([main_pos, main_pos_], axis=0)

    #PL
    feature_pl = pl_df[feature_list]
    substrat_pl = pl_df[substrat_list]
    mainstrat_pl = pd.DataFrame([list(x) for x in dbm.get_fetchall("SELECT RCD_DATE, PL, STRT_NAME, ASET FROM stratdb.tb_scnd_rp_tr;")], columns=['Date', 'PL', 'Strategy', 'Asset'])

    #Macro
    macro_factor = rpa.macro_factor_index
    macro_indi_factor = rpa.macro_indi_factor_index

    return feature_pos, substrat_pos, main_pos, feature_pl, substrat_pl, mainstrat_pl, macro_factor, macro_indi_factor

def dict_to_df(dict):
    for i, k in enumerate(dict.items()):
        if i == 0:
            df = k[1]
        else:
            v = k[1]
            df = pd.concat([df, v], axis=1, sort=True).fillna(method='ffill')
    return df

def style_negative(v, props=''):
    try:
        x = props if v < 0 else None
    except:
        x = None
    return x

#데이터 불러오기
with st.spinner("Querying Data, Will take about 2 minutes, Please Wait..."):
    rpa, rdp, cdp, fdp, edp = pull_data_functions()
    strat_sub_main_match_dict = {'Rates_Value':['rates_value_slope_fra', 'rates_value_curve_fra'],
                            'Rates_Trend':['rates_price_trend'],
                            'Rates_Momentum':['rates_momentum_momhtp_momadj_mommr', 'rates_momentum_momhtp_mommr2_fra'],
                            'Rates_MeanReversion':['rates_meanreversion'],
                            #'Rates_Coskew':['rates_coskew'],
                            'Rates_Carry':['rates_carry_carry_volatility_fra'],
                            'Rates_Volatility':['rates_volatility_relativevol'],
                            'FX_Value':['fx_value_slope', 'fx_value_pricerange_cftcrange_skew'],
                            'FX_Momentum':['fx_momentum_momhtp_momadj_mommr', 'fx_momentum_momhtp_momadj2_slope'],
                            'FX_CFTC':['fx_cftc_cftc'],
                            'FX_Carry':['fx_carry_carry_curvature_volatility'],
                            'FX_BasisMomentum' : ['fx_basismomentum_bmom'],
                            'FX_Skew':['fx_skew_regular_residual_fractile'],
                            'FX_Hedgeflow':['fx_hedgeflow_bond_equity'],
                            'FX_Trend' : ['fx_price_trend'],
                            'Equity_Momentum':['equity_momentum_momhtp_momadj'],
                            'Equity_Coskew':['equity_coskew'],
                            'Equity_Volatility':['equity_volatility_relativevol'],
                            'Equity_Carry':['equity_carry_implieddividend'], #'equity_carry_implieddividend_reverse'],
                            'Equity_Value':['equity_value_pricerange_skew_short', 'equity_value_pricerange_skew_long'],
                            'Equity_Factor':['equity_factor_riskfactor_macrofactor_riskcovar'],
                            'Equity_Momvol':['equity_momvol_high52_malt_volume_momvolcovar'],
                            'Equity_Trend' : ['equity_price_trend'],
                            'Commodity_Value':['commodity_value_pricerange_cftcrange_skew'],
                            'Commodity_Momentum':['commodity_momentum_momhtp_momadj_mommr_slopelevel_slopeacceleration', 'commodity_momentum_momhtp2_momadj_mommr_convexitylevel_convexityacceleration'],
                            'Commodity_CFTC':['commodity_cftc_cftc'],
                            'Commodity_Carry':['commodity_carry_carry_convexitylevel_convexityacceleration', 'commodity_carry_carry_slopelevel_slopeacceleration'],
                            'Commodity_BasisMomentum':['commodity_basismomentum_bmom'],
                            'Commodity_Macrocycle':['commodity_macrocycle_macrocycle_macrocycle2'],
                            'Commodity_Trend' : ['commodity_price_trend']
                            }
    
    mainstrat_list = ['Commodity_Value', 
                    'Commodity_Carry',
                    'Commodity_Momentum', 
                    'Commodity_BasisMomentum', 
                    'Commodity_CFTC', 
                    'Commodity_Macrocycle',
                    'Commodity_Trend',
                    'Equity_Value', 
                    'Equity_Carry', 
                    'Equity_Momentum', 
                    'Equity_Coskew', 
                    'Equity_Volatility', 
                    'Equity_Factor', 
                    'Equity_Momvol',
                    'Equity_Trend',
                    'FX_Value', 
                    'FX_Skew', 
                    'FX_Hedgeflow',
                    'FX_Carry', 
                    'FX_Momentum', 
                    'FX_BasisMomentum',
                    'FX_CFTC',
                    'FX_Trend',
                    'Rates_Value',
                    'Rates_Carry',
                    'Rates_Momentum', 
                    'Rates_Volatility', 
                    'Rates_MeanReversion', 
                    #'Rates_Coskew',
                    'Rates_Trend'
                    ]
    
    substrat_list = ['rates_value_slope_fra', 
                    'rates_value_curve_fra', 
                    'rates_momentum_momhtp_momadj_mommr', 
                    'rates_momentum_momhtp_mommr2_fra',
                    'rates_meanreversion',
                    #'rates_coskew',
                    'rates_carry_carry_volatility_fra',
                    'rates_volatility_relativevol',
                    'rates_price_trend', 
                    'fx_value_slope',
                    'fx_value_pricerange_cftcrange_skew',
                    'fx_momentum_momhtp_momadj_mommr',
                    'fx_momentum_momhtp_momadj2_slope',
                    'fx_cftc_cftc',
                    'fx_carry_carry_curvature_volatility',
                    'fx_basismomentum_bmom',
                    'fx_skew_regular_residual_fractile',
                    'fx_hedgeflow_bond_equity',
                    'fx_price_trend',
                    'equity_momentum_momhtp_momadj',
                    'equity_coskew',
                    'equity_volatility_relativevol',
                    'equity_carry_implieddividend',
                    'equity_carry_implieddividend_reverse',
                    'equity_value_pricerange_skew_short',
                    'equity_value_pricerange_skew_long',
                    'equity_factor_riskfactor_macrofactor_riskcovar',
                    'equity_momvol_high52_malt_volume_momvolcovar',
                    'equity_price_trend',
                    'commodity_value_pricerange_cftcrange_skew',
                    'commodity_momentum_momhtp_momadj_mommr_slopelevel_slopeacceleration',
                    'commodity_momentum_momhtp2_momadj_mommr_convexitylevel_convexityacceleration',
                    'commodity_cftc_cftc',
                    'commodity_carry_carry_convexitylevel_convexityacceleration', 
                    'commodity_carry_carry_slopelevel_slopeacceleration',
                    'commodity_basismomentum_bmom',
                    'commodity_macrocycle_macrocycle_macrocycle2',
                    'commodity_price_trend'
                    ]
    
    display_order = ['Rates_Value','Rates_Carry','Rates_Momentum', 'Rates_Volatility', 'Rates_Trend', 'Rates_MeanReversion', 'Commodity_Value', 'Commodity_Carry','Commodity_Momentum', 'Commodity_CFTC', 'Commodity_BasisMomentum', 'Commodity_Macrocycle','Commodity_Trend', 'FX_Value', 'FX_Carry', 'FX_Momentum', 'FX_CFTC', 'FX_Skew', 'FX_BasisMomentum', 'FX_Hedgeflow', 'FX_Trend', 'Equity_Value', 'Equity_Carry',  'Equity_Momentum','Equity_Coskew', 'Equity_Volatility', 'Equity_Factor','Equity_Momvol','Equity_Trend']#['Rates_Value','Rates_Carry','Rates_Momentum', 'Rates_Coskew','Rates_Volatility', 'Rates_Trend', 'Rates_MeanReversion', 'Commodity_Value', 'Commodity_Carry','Commodity_Momentum', 'Commodity_CFTC', 'Commodity_BasisMomentum', 'Commodity_Trend', 'FX_Value', 'FX_Carry', 'FX_Momentum', 'FX_CFTC', 'FX_BasisMomentum', 'FX_Trend', 'Equity_Value', 'Equity_Carry',  'Equity_Momentum','Equity_Coskew', 'Equity_Volatility', 'Equity_Trend']
    ticker_name_match_dict_commodity = {'CL1 Comdty':'Crude Oil','XB1 Comdty':'Gasoline','HO1 Comdty':'Heating Oil','NG1 Comdty':'Natural Gas','GC1 Comdty':'Gold','SI1 Comdty':'Silver','HG1 Comdty':'Copper','PL1 Comdty':'Platinum','PA1 Comdty':'Palladium','C 1 Comdty':'Corn','S 1 Comdty':'Soybean','BO1 Comdty':'Soybean Oil','W 1 Comdty':'Wheat','KW1 Comdty':'Kensas Wheat','CT1 Comdty':'Cotton','KC1 Comdty':'Coffee','SB1 Comdty':'Sugar','LC1 Comdty':'Liver Cattle','LH1 Comdty':'Lean Hog'} 
    ticker_name_match_dict_rates = {'KE1 Comdty':'Korea 3Y','KAA1 Comdty':'Korea 10Y','SFR4 Comdty':'SOFR 1Y','TU1 Comdty':'US 2Y','FV1 Comdty':'US 5Y','TY1 Comdty':'US 10Y','UXY1 Comdty':'Ultra US 10Y', 'SSY4 Comdty':'Saron 1Y', 'ER4 Comdty':'Euribor 1Y', 'DU1 Comdty':'Germany 2Y','OE1 Comdty':'Germany 5Y','RX1 Comdty':'Germany 10Y','G 1 Comdty':'UK 10Y','OAT1 Comdty':'France 10Y','BTS1 Comdty':'Italy 3Y','IK1 Comdty':'Italy 10Y','JB1 Comdty':'Japan 10Y'} 
    ticker_name_match_dict_fx = {'EC1 Curncy':'EUR','JY1 Curncy':'JPY','AD1 Curncy':'AUD','BP1 Curncy':'GBP','CD1 Curncy':'CAD','SF1 Curncy':'CHF','NV1 Curncy':'NZD'} 
    ticker_name_match_dict_equity = {'ES1 Index':'S&P500','NQ1 Index':'Nasdaq100','DM1 Index':'DowJones','KM1 Index':'KOSPI200','VG1 Index':'EuroStoxx50','Z 1 Index':'FTSE100','GX1 Index':'DAX','XP1 Index':'ASX200','XU1 Index':'FTSE China A50','NK1 Index':'Nikkei225','HC1 Index':'HSCEI'} 
    feature_list = get_feature_list()
    feature_list = [s for s in feature_list if s not in substrat_list]+['fx_cftc_cftc', 'commodity_cftc_cftc']
    feature_pos, substrat_pos, main_pos, feature_pl, substrat_pl, mainstrat_pl, macro_factor, macro_indi_factor = pull_strategy_data_series()

with st.container():
    tab1, tab2, tab3, tab4, tab5 = st.tabs(['Position', 'Performance', 'Chart', 'Factor', 'Substrategy'])

    with open(css_dir) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

    with tab1:
        position_ticker = list(ticker_name_match_dict_rates.keys())+list(ticker_name_match_dict_commodity.keys())+list(ticker_name_match_dict_fx.keys())+list(ticker_name_match_dict_equity.keys())
        
        with st.expander('Strategy Weight'):
            rates_value = st.number_input('Rates Value', value=1.0, step=0.25)
            rates_carry = st.number_input('Rates Carry', value=1.0, step=0.25)
            rates_mom = st.number_input('Rates Momentum', value=1.0, step=0.25)
            #rates_coskew = st.number_input('Rates Coskew', value=0.5, step=0.25)
            rates_vol = st.number_input('Rates Volatility', value=1.0, step=0.25)
            rates_trend = st.number_input('Rates Trend', value=0.5, step=0.25)
            rates_mr = st.number_input('Rates MeanReversion', value=1.0, step=0.25)
            comm_value = st.number_input('Commodity Value', value=2.0, step=0.25)
            comm_carry = st.number_input('Commodity Carry', value=1.0, step=0.25)
            comm_mom = st.number_input('Commodity Momentum', value=1.0, step=0.25)
            comm_cftc = st.number_input('Commodity CFTC',  value=1.0, step=0.25)
            comm_bmom = st.number_input('Commodity BasisMomentum', value=2.0, step=0.25)
            comm_mcycle = st.number_input('Commodity Macrocycle', value=1.0, step=0.25)
            comm_trend = st.number_input('Commodity Trend', value=1.0, step=0.25)
            fx_value = st.number_input('FX Value', value=7.0, step=0.25)
            fx_carry = st.number_input('FX Carry', value=8.0, step=0.25)
            fx_mom = st.number_input('FX Momentum', value=7.0, step=0.25)
            fx_cftc = st.number_input('FX CFTC', value=10.0, step=0.25)
            fx_skew = st.number_input('FX Skew', value=5.0, step=0.25)
            fx_bmom = st.number_input('FX BasisMomentum', value=10.0, step=0.25)
            fx_hflow = st.number_input('FX Hedgeflow', value=1.0, step=0.25)
            fx_trend = st.number_input('FX Trend', value=1.0, step=0.25)
            equity_value = st.number_input('Equity Value', value=1.0, step=0.25)
            equity_carry = st.number_input('Equity Carry', value=2.0, step=0.25)
            equity_mom = st.number_input('Equity Momentum', value=0.5, step=0.25)
            equity_coskew = st.number_input('Equity Coskew', value=0.5, step=0.25)
            equity_momvol = st.number_input('Equity Momvol', value=1.0, step=0.25)
            equity_vol = st.number_input('Equity Volatility', value=2.0, step=0.25)
            equity_factor = st.number_input('Equity Factor', value=2.0, step=0.25)
            equity_trend = st.number_input('Equity Trend', value=0.5, step=0.25)
            main_strategy_weight = {'Commodity_Value':comm_value, 
                                    'Commodity_Carry':comm_carry,
                                    'Commodity_Momentum':comm_mom, 
                                    'Commodity_CFTC':comm_cftc, 
                                    'Commodity_BasisMomentum':comm_bmom, 
                                    'Commodity_Macrocycle':comm_mcycle,
                                    'Commodity_Trend':comm_trend,
                                    'Equity_Value':equity_value, 
                                    'Equity_Carry':equity_carry,  
                                    'Equity_Momentum':equity_mom,
                                    'Equity_Coskew':equity_coskew, 
                                    'Equity_Momvol':equity_momvol, 
                                    'Equity_Volatility':equity_vol, 
                                    'Equity_Factor':equity_factor, 
                                    'Equity_Trend':equity_trend,
                                    'FX_Value':fx_value, 
                                    'FX_Carry':fx_carry, 
                                    'FX_Momentum':fx_mom, 
                                    'FX_CFTC':fx_cftc,
                                    'FX_Skew':fx_skew,
                                    'FX_BasisMomentum':fx_bmom,
                                    'FX_Hedgeflow' : fx_hflow,
                                    'FX_Trend':fx_trend,
                                    'Rates_Value':rates_value,
                                    'Rates_Carry':rates_carry,
                                    'Rates_Momentum':rates_mom, 
                                    #'Rates_Coskew':rates_coskew,
                                    'Rates_Volatility':rates_vol, 
                                    'Rates_Trend':rates_trend, 
                                    'Rates_MeanReversion':rates_mr
                                    }
            
            #if 'main_strategy_weight' not in st.session_state:
            st.session_state.strategy_weight_dict = main_strategy_weight
        
        def get_position_df(search_date):

            main_pos_1 = main_pos[main_pos['Date']<=search_date]
            for i, w in enumerate(main_strategy_weight.items()):
                k = w[0]
                v = w[1]
                if i == 0:
                    strat_main_pos = main_pos_1[main_pos_1['Strategy']==k].pivot(index='Date', columns='Ticker', values='Position').iloc[-1,:]
                    strat_main_pos.name = k
                else:
                    strat_main_pos_ = main_pos_1[main_pos_1['Strategy']==k].pivot(index='Date', columns='Ticker', values='Position').iloc[-1,:]
                    strat_main_pos_.name = k
                    strat_main_pos = pd.concat([strat_main_pos, strat_main_pos_], axis=1)
    
            strat_main_pos = strat_main_pos*list(main_strategy_weight.values())
            strat_main_pos['Aggregate'] = strat_main_pos.sum(axis=1)
            
            usdkrw = rdp.currency_df['KE1 Comdty'][-1]
            
            #commodity
            commodity_1 = strat_main_pos.copy().T[list(ticker_name_match_dict_commodity.keys())]
            commodity_1 = commodity_1[commodity_1.index.isin([k for k in main_strategy_weight.keys() if 'Commodity' in k]+['Aggregate'])]
            commodity_1 = commodity_1.T
            commodity_1['Name'] = list(ticker_name_match_dict_commodity.values())
            commodity_1 = commodity_1.replace({np.nan:0})
            commodity_1.columns = [c.replace("Commodity_", "") for c in commodity_1.columns]
            
            commodity_price = cdp.clpr_signal_df[list(ticker_name_match_dict_commodity.keys())]
            commodity_price_series = cdp.clpr_df[list(ticker_name_match_dict_commodity.keys())].iloc[-60:, :] - cdp.clpr_df[list(ticker_name_match_dict_commodity.keys())].iloc[-60:, :].shift(1)
            commodity_price = commodity_price[commodity_price.index<=date.today().isoformat()].iloc[-1,:]
            
            commodity_value = pd.DataFrame(cdp.contract_value.items(), columns=['Ticker', 'Contract Value'])
            commodity_value = commodity_value[commodity_value['Ticker'].isin(list(ticker_name_match_dict_commodity.keys()))].set_index('Ticker').T[list(ticker_name_match_dict_commodity.keys())].iloc[-1,:]

            commodity_1['Notional'] = np.round(commodity_1['Aggregate']*commodity_price*commodity_value*usdkrw/100000000, 2)
            commodity_position = commodity_1[ ['Name', 'Notional', 'Aggregate'] + [c.replace("Commodity_", "") for c in main_strategy_weight.keys() if "Commodity" in c]]            

            vol_c = ['Volatility',  np.round(commodity_1['Notional'].sum(),2)]
            for s in ['Aggregate']+[c.replace("Commodity_", "") for c in main_strategy_weight.keys() if "Commodity" in c]:
                vol_c.append(np.round((commodity_price_series*commodity_1[s]*commodity_value).sum(axis=1).std(),2))

            commodity_position = pd.concat([commodity_position, pd.DataFrame(vol_c, columns=['Commodity'], index=commodity_position.columns).T], axis=0)
            
            #rates
            rates_1 = strat_main_pos.copy().T[list(ticker_name_match_dict_rates.keys())]
            rates_1 = rates_1[rates_1.index.isin([k for k in main_strategy_weight.keys() if 'Rates' in k]+['Aggregate'])]
            rates_1 = rates_1.T
            rates_1['Name'] = list(ticker_name_match_dict_rates.values())
            rates_1 = rates_1.replace({np.nan:0})
            rates_1.columns = [c.replace("Rates_", "") for c in rates_1.columns]

            rates_price = rdp.clpr_signal_df[list(ticker_name_match_dict_rates.keys())]
            rates_price_series = rdp.clpr_df[list(ticker_name_match_dict_rates.keys())].iloc[-60:, :] - rdp.clpr_df[list(ticker_name_match_dict_rates.keys())].iloc[-60:, :].shift(1)
            rates_price = rates_price[rates_price.index<=date.today().isoformat()].iloc[-1,:]
            
            rates_value = pd.DataFrame(rdp.contract_value.items(), columns=['Ticker', 'Contract Value'])
            rates_value = rates_value[rates_value['Ticker'].isin(list(ticker_name_match_dict_rates.keys()))].set_index('Ticker').T[list(ticker_name_match_dict_rates.keys())].iloc[-1,:]

            rates_currency =  rdp.currency_df[list(ticker_name_match_dict_rates.keys())].iloc[-1, :]
            rates_currency_series =  rdp.currency_df[list(ticker_name_match_dict_rates.keys())].iloc[-60:, :]

            rates_1['Notional'] = np.round(rates_1['Aggregate']*rates_price*rates_value/rates_currency*usdkrw/100000000, 2)
            rates_position = rates_1[ ['Name', 'Notional', 'Aggregate'] + [c.replace("Rates_", "") for c in main_strategy_weight.keys() if "Rates" in c]]
            
            vol_r = ['Volatility',  np.round(rates_1['Notional'].sum(),2)]
            for s in ['Aggregate']+[c.replace("Rates_", "") for c in main_strategy_weight.keys() if "Rates" in c]:
                vol_r.append(np.round((rates_price_series*rates_1[s]*rates_value/rates_currency_series).sum(axis=1).std(),2))

            rates_position = pd.concat([rates_position, pd.DataFrame(vol_r, columns=['Rates'], index=rates_position.columns).T], axis=0)
            
            #fx
            fx_1 = strat_main_pos.copy().T[list(ticker_name_match_dict_fx.keys())]
            fx_1 = fx_1[fx_1.index.isin([k for k in main_strategy_weight.keys() if 'FX' in k]+['Aggregate'])]
            fx_1 = fx_1.T
            fx_1['Name'] = list(ticker_name_match_dict_fx.values())
            fx_1 = fx_1.replace({np.nan:0})
            fx_1.columns = [c.replace("FX_", "") for c in fx_1.columns]

            fx_price = fdp.clpr_signal_df[list(ticker_name_match_dict_fx.keys())]
            fx_price_series = fdp.clpr_df[list(ticker_name_match_dict_fx.keys())].iloc[-60:, :] - fdp.clpr_df[list(ticker_name_match_dict_fx.keys())].iloc[-60:, :].shift(1)
            fx_price = fx_price[fx_price.index<=date.today().isoformat()].iloc[-1,:]
            
            fx_value = pd.DataFrame(fdp.contract_value.items(), columns=['Ticker', 'Contract Value'])
            fx_value = fx_value[fx_value['Ticker'].isin(list(ticker_name_match_dict_fx.keys()))].set_index('Ticker').T[list(ticker_name_match_dict_fx.keys())].iloc[-1,:]

            fx_1['Notional'] = np.round(fx_1['Aggregate']*fx_price*fx_value*usdkrw/100000000, 2)
            fx_position = fx_1[ ['Name', 'Notional', 'Aggregate'] + [c.replace("FX_", "") for c in main_strategy_weight.keys() if "FX" in c]]

            vol_f = ['Volatility',  np.round(fx_1['Notional'].sum(),2)]
            for s in ['Aggregate']+[c.replace("FX_", "") for c in main_strategy_weight.keys() if "FX" in c]:
                vol_f.append(np.round((fx_price_series*fx_1[s]*fx_value).sum(axis=1).std(),2))

            fx_position = pd.concat([fx_position, pd.DataFrame(vol_f, columns=['FX'], index=fx_position.columns).T], axis=0)
            
            #equity
            equity_1 = strat_main_pos.copy().T[list(ticker_name_match_dict_equity.keys())]
            equity_1 = equity_1[equity_1.index.isin([k for k in main_strategy_weight.keys() if 'Equity' in k]+['Aggregate'])]
            equity_1 = equity_1.T
            equity_1['Name'] = list(ticker_name_match_dict_equity.values())
            equity_1 = equity_1.replace({np.nan:0})
            equity_1.columns = [c.replace("Equity_", "") for c in equity_1.columns]

            equity_price = edp.clpr_signal_df[list(ticker_name_match_dict_equity.keys())]
            equity_price_series = edp.clpr_df[list(ticker_name_match_dict_equity.keys())].iloc[-60:, :] - edp.clpr_df[list(ticker_name_match_dict_equity.keys())].iloc[-60:, :].shift(1)
            equity_price = equity_price[equity_price.index<=date.today().isoformat()].iloc[-1,:]
            
            equity_value = pd.DataFrame(edp.contract_value.items(), columns=['Ticker', 'Contract Value'])
            equity_value = equity_value[equity_value['Ticker'].isin(list(ticker_name_match_dict_equity.keys()))].set_index('Ticker').T[list(ticker_name_match_dict_equity.keys())].iloc[-1,:]

            equity_currency =  edp.currency_df[list(ticker_name_match_dict_equity.keys())].iloc[-1, :]
            equity_currency_series =  edp.currency_df[list(ticker_name_match_dict_equity.keys())].iloc[-60:, :]

            equity_1['Notional'] = np.round(equity_1['Aggregate']*equity_price*equity_value/equity_currency*usdkrw/100000000, 2)
            equity_position = equity_1[ ['Name', 'Notional', 'Aggregate'] + [c.replace("Equity_", "") for c in main_strategy_weight.keys() if "Equity" in c]]
            
            vol_e = ['Volatility',  np.round(equity_1['Notional'].sum(),2)]
            for s in ['Aggregate']+[c.replace("Equity_", "") for c in main_strategy_weight.keys() if "Equity" in c]:
                vol_e.append(np.round((equity_price_series*equity_1[s]*equity_value/equity_currency_series).sum(axis=1).std(),2))

            equity_position = pd.concat([equity_position, pd.DataFrame(vol_e, columns=['Equity'], index=equity_position.columns).T], axis=0)
            
            return strat_main_pos, commodity_position.style.applymap(style_negative, props='color:red;').format(precision=2, thousands=",", decimal="."), rates_position.style.applymap(style_negative, props='color:red;').format(precision=2, thousands=",", decimal="."), fx_position.style.applymap(style_negative, props='color:red;').format(precision=2, thousands=",", decimal="."),  equity_position.style.applymap(style_negative, props='color:red;').format(precision=2, thousands=",", decimal=".")

        col1, col2 = st.columns(2)
        with col1:
            search_date_1 = datetime.strftime(st.date_input('Position Date'), "%Y-%m-%d")
            main_position, commodity_position, rates_position, fx_position,  equity_position = get_position_df(search_date_1)
            st.markdown("**Rates**")
            st.dataframe(rates_position, use_container_width=True)
            st.markdown("**Commodity**")
            st.dataframe(commodity_position, use_container_width=True)
            st.markdown("**FX**")
            st.dataframe(fx_position, use_container_width=True)
            st.markdown("**Equity**")
            st.dataframe(equity_position, use_container_width=True)
            st.download_button(label="Download data as CSV",data= convert_df(main_position.replace({np.nan:0})),file_name='MA_RP_{}.csv'.format(search_date_1), mime='text/csv')
        
        with col2:
            search_date_2 = datetime.strftime(st.date_input('Position Date '), "%Y-%m-%d")
            main_position, commodity_position_, rates_position_, fx_position_,  equity_position_ = get_position_df(search_date_2)
            st.markdown("**Rates**")
            st.dataframe(rates_position_, use_container_width=True)
            st.markdown("**Commodity**")
            st.dataframe(commodity_position_, use_container_width=True)
            st.markdown("**FX**")
            st.dataframe(fx_position_, use_container_width=True)
            st.markdown("**Equity**")
            st.dataframe(equity_position_, use_container_width=True)  
                 
    with tab2:
        daily = mainstrat_pl.pivot(index='Date', columns='Strategy', values='PL')
        daily = daily[list(main_strategy_weight.keys())]
        daily_pl = daily*np.array(main_strategy_weight.values())
        daily_pl.index = pd.DatetimeIndex(daily_pl.index)
        st.session_state.mainstratpl = daily_pl
        weekly_pl = daily_pl.resample('W-Mon').sum()
        monthly_pl = daily_pl.resample('M').sum()
        yearly_pl = daily_pl.resample('Y').sum()
        
        col1, col2 = st.columns(2)
        with col1:
            ref_date = datetime.strftime(st.date_input('Reference Date'), "%Y-%m-%d")
            daily_pl_ref = daily_pl[daily_pl.index<=ref_date]
            pl_1 = daily_pl_ref[display_order].tail(12).sort_index(ascending=False).T.replace({np.nan:0})
            pl_1.columns.name = None
            pl_1.columns = pl_1.columns.astype(str)
            pl_1.loc['Rates'] = pl_1[pl_1.index.isin([s for s in mainstrat_list if 'Rates' in s])].sum()
            pl_1.loc['Commodity'] = pl_1[pl_1.index.isin([s for s in mainstrat_list if 'Commodity' in s])].sum()
            pl_1.loc['FX'] = pl_1[pl_1.index.isin([s for s in mainstrat_list if 'FX' in s])].sum()
            pl_1.loc['Equity'] = pl_1[pl_1.index.isin([s for s in mainstrat_list if 'Equity' in s])].sum()
            pl_1.loc['Portfolio'] = pl_1[pl_1.index.isin(mainstrat_list)].sum()
            pl_1 = pl_1.style.applymap(style_negative, props='color:red;').format(precision=2, thousands=",", decimal=".")
            st.write(pl_1)

        with col2:
            freq = st.selectbox('Frequency', ('Weekly', 'Monthly', 'Yearly'))
            if freq == 'Weekly':
                pl = daily_pl_ref.resample('W-Mon').sum()[display_order].tail(12).sort_index(ascending=False).T.replace({np.nan:0})
                pl.columns.name = None
                pl.columns = pl.columns.astype(str)
                pl_ = pl.copy()
                pl.loc['Rates'] = pl[pl.index.isin([s for s in mainstrat_list if 'Rates' in s])].sum()
                pl.loc['Commodity'] = pl[pl.index.isin([s for s in mainstrat_list if 'Commodity' in s])].sum()
                pl.loc['FX'] = pl[pl.index.isin([s for s in mainstrat_list if 'FX' in s])].sum()
                pl.loc['Equity'] = pl[pl.index.isin([s for s in mainstrat_list if 'Equity' in s])].sum()
                pl.loc['Portfolio'] = pl[pl.index.isin(mainstrat_list)].sum()
                pl_s = pl.style.applymap(style_negative, props='color:red;').format(precision=2, thousands=",", decimal=".")
                
                pl__ = pl_.T
                fig = px.bar(pl__, x=pl__.index, y=pl__.columns, title='P&L Contribution')
                fig.update_xaxes(tickformat="%Y.%m.%d", title=freq)
                fig.update_yaxes(title="P&L")
                st.write(pl_s)
            elif freq == 'Monthly':
                pl = daily_pl_ref.resample('M').sum()[display_order].tail(12).sort_index(ascending=False).T.replace({np.nan:0})
                pl.columns.name = None
                pl.columns = pl.columns.astype(str)
                pl_ = pl.copy()
                pl.loc['Rates'] = pl[pl.index.isin([s for s in mainstrat_list if 'Rates' in s])].sum()
                pl.loc['Commodity'] = pl[pl.index.isin([s for s in mainstrat_list if 'Commodity' in s])].sum()
                pl.loc['FX'] = pl[pl.index.isin([s for s in mainstrat_list if 'FX' in s])].sum()
                pl.loc['Equity'] = pl[pl.index.isin([s for s in mainstrat_list if 'Equity' in s])].sum()
                pl.loc['Portfolio'] = pl[pl.index.isin(mainstrat_list)].sum()
                pl_s = pl.style.applymap(style_negative, props='color:red;').format(precision=2, thousands=",", decimal=".")
                
                pl__ = pl_.T
                fig = px.bar(pl__, x=pl__.index, y=pl__.columns, title='P&L Contribution')
                fig.update_xaxes(tickformat="%Y.%m.%d", title=freq)
                fig.update_yaxes(title="P&L")
                
                st.write(pl_s)
            elif freq == 'Yearly':
                pl = daily_pl_ref.resample('Y').sum()[display_order].tail(12).sort_index(ascending=False).T.replace({np.nan:0})
                pl.columns.name = None
                pl.columns = pl.columns.astype(str)
                pl_ = pl.copy()
                pl.loc['Rates'] = pl[pl.index.isin([s for s in mainstrat_list if 'Rates' in s])].sum()
                pl.loc['Commodity'] = pl[pl.index.isin([s for s in mainstrat_list if 'Commodity' in s])].sum()
                pl.loc['FX'] = pl[pl.index.isin([s for s in mainstrat_list if 'FX' in s])].sum()
                pl.loc['Equity'] = pl[pl.index.isin([s for s in mainstrat_list if 'Equity' in s])].sum()
                pl.loc['Portfolio'] = pl[pl.index.isin(mainstrat_list)].sum()
                pl_s = pl.style.applymap(style_negative, props='color:red;').format(precision=2, thousands=",", decimal=".")
                
                pl__ = pl_.T
                fig = px.bar(pl__, x=pl__.index, y=pl__.columns, title='P&L Contribution', height=600)
                fig.update_xaxes(tickformat="%Y.%m.%d", title=freq)
                fig.update_yaxes(title="P&L")

                st.write(pl_s)

        st.plotly_chart(fig, use_container_width=True)
        
        #yearly performance
        yearly_pl_present = st.session_state.mainstratpl.copy()
        yearly_pl_present = yearly_pl_present[yearly_pl_present.index>'2012-12-31']
        yearly_pl_present['Portfolio'] = yearly_pl_present.sum(axis=1)
        yearly_pl_present['Year'] = yearly_pl_present.index.year
        yearly_pl_present = yearly_pl_present[['Portfolio', 'Year']]

        yearly_pl_list = []
        yearly_pl_len = []
        for i in range(2013, yearly_pl_present['Year'][-1]+1):
            p = list(yearly_pl_present[yearly_pl_present['Year'] == i]['Portfolio'].cumsum().values)
            yearly_pl_len.append(len(p))
            yearly_pl_list.append(p)
        
        yearly_pl_list_pad = []
        max_length = np.max(yearly_pl_len)
        for pl_i in yearly_pl_list:
            pad = max_length - len(pl_i)
            yearly_pl_list_pad.append(pl_i + [pl_i[-1] for i in range(pad)])

        yearly_pl_pad_df = pd.DataFrame(yearly_pl_list_pad).T
        yearly_pl_pad_df.columns = [str(y) for y in sorted(list(set(yearly_pl_present['Year'])))]
        yearly_pl_pad_df = yearly_pl_pad_df.reset_index().rename(columns={'index':'Date'})

        fig_y = px.line(yearly_pl_pad_df, x='Date', y=yearly_pl_pad_df.columns,title='Yearly Performance', height=600)    
        fig_y.update_yaxes(title='P&L')
        st.plotly_chart(fig_y, use_container_width=True)

        #whole sample
        pl_whole = pd.DataFrame(yearly_pl_present['Portfolio'].cumsum())

        #trend line
        X = np.array(range(len(pl_whole)))
        y = pl_whole.values
        model = sm.OLS(y, X).fit()
        regression_line_ols = model.predict(X)
        pl_whole['Trend Line'] = regression_line_ols            
        fig_y_whole = px.line(pl_whole.reset_index(), x='Date', y=pl_whole.columns,title='Whole Period Performance', height=600)    
        fig_y_whole.update_yaxes(title='P&L')
        st.plotly_chart(fig_y_whole, use_container_width=True)

        col1_, col2_ = st.columns(2)
        with col1_:
            rolling_s = st.session_state.mainstratpl.sum(axis=1)
            rolling_s = rolling_s.rolling(20).sum()
            rolling_s_df = pd.DataFrame(rolling_s, columns=['20D Rolling P&L'])
            rolling_s_df = rolling_s_df.reset_index()
            
            fig_pl = px.line(rolling_s_df, x='Date', y='20D Rolling P&L' ,hover_data={'Date': "|%B %d, %Y"}, title='20d Rolling PL')    
            fig_pl.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            st.plotly_chart(fig_pl, use_container_width=True)

        with col2_:
            mdd = st.session_state.mainstratpl.copy()
            mdd['Portfolio'] = mdd.sum(axis=1)
            mdd = mdd[['Portfolio']].cumsum()

            mdd = (mdd - mdd.cummax())
            mdd.columns = ['MDD']
            mdd = mdd.reset_index()

            fig_m = px.line(mdd, x='Date', y='MDD',hover_data={'Date': "|%B %d, %Y"},title='MDD')    
            fig_m.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            #fig_m.update_yaxes(tickformat=":.2f")
            st.plotly_chart(fig_m, use_container_width=True)
        
        #Sharpe
        sharpe_pl = st.session_state.mainstratpl.copy()
        sharpe_pl['Portfolio'] = sharpe_pl.sum(axis=1)
        
        col1__, col2__, col3__, col4__ = st.columns(4)
        with col1__:
            start_dt = st.date_input('Calculation Start', date(2022,9,1))
        with col2__:
            end_dt = st.date_input('Calculation End')
        
        sharpe_pl = sharpe_pl[(sharpe_pl.index>=datetime.strftime(start_dt, "%Y-%m-%d"))&(sharpe_pl.index<=datetime.strftime(end_dt, "%Y-%m-%d"))]
        sharpe_pl = sharpe_pl.replace({np.nan:0})
        strat_sharpe = sharpe_pl.sum()*(365/((end_dt-start_dt).days)) / (sharpe_pl.std()*np.sqrt(252))
        
        yearly_sharpe = {}
        for y_s, y in zip(yearly_pl_list,[str(y) for y in sorted(list(set(yearly_pl_present['Year'])))]):
            if len(y_s) >= 250:
                y_s_ =  [x[0]-x[1]  for x in zip(y_s[1:], y_s[:-1])]
                yearly_sharpe[y] = np.sum(y_s_)/(np.std(y_s_)*np.sqrt(252))
            elif y == str(date.today().year):
                y_s_ =  [x[0]-x[1]  for x in zip(y_s[1:], y_s[:-1])]
                if len(y_s_)>0:
                    yearly_sharpe[y] = np.sum(y_s_)*(365/((sharpe_pl.index[-1]-datetime.strptime(str(date.today().year)+"-01-01", "%Y-%m-%d")).days))/(np.std(y_s_)*np.sqrt(252))
                else:
                    yearly_sharpe[y] = 0
                    
        strat_sharpe_df = pd.DataFrame(strat_sharpe, columns=['SR'])
        sharpe_ratio_df = np.round(pd.concat([strat_sharpe_df, pd.DataFrame(yearly_sharpe.items(), columns=['Strategy', 'SR']).set_index('Strategy')] ,axis=0),4)
        #sharpe_ratio_df.columns = [c.replace('_', '\n') for c in sharpe_ratio_df.columns]
        #st.table(sharpe_ratio_df.style.background_gradient(cmap='RdBu', axis=1).format("{:.3f}"))
        
        #Consistency
        cwr_pl = sharpe_pl.cumsum().copy()
        _, strat_cwr_df = rpa.cwr(cwr_pl)
        #st.write(pd.DataFrame(yearly_pl_list))
        yearly_pl_df = pd.DataFrame(yearly_pl_list).T
        yearly_pl_df.columns = [str(c) for c in sorted(list(set(yearly_pl_present['Year'])))]     
        _, yearly_cwr_df = rpa.cwr(yearly_pl_df)   
        cwr_df = np.round(pd.concat([strat_cwr_df, yearly_cwr_df],axis=0),4)
        
        comb_df = pd.concat([sharpe_ratio_df, cwr_df], axis=1).T
        comb_df.columns = [c.replace('_', '\n') for c in comb_df.columns]

        st.dataframe(comb_df.style.background_gradient(cmap='RdBu', axis=1).format("{:.3f}"))
        st.download_button(label="Download data as CSV",data= convert_df(daily_pl),file_name='MA_RP_PL_{}.csv'.format(date.today().isoformat()), mime='text/csv')
        
    with tab3:
        strategy_selected_ = st.multiselect("Select Strategy", mainstrat_list, max_selections=9)
        if len(strategy_selected_)>0:
            strategy_series_tr_to_chart_df_adj =  st.session_state.mainstratpl[strategy_selected_]
            strategy_series_tr_to_chart_df_adj['Port'] = strategy_series_tr_to_chart_df_adj.sum(axis=1)
            strategy_selected = strategy_selected_ + ['Port']
            strategy_series_tr_to_chart_df_adj_ = strategy_series_tr_to_chart_df_adj.cumsum().fillna(method='ffill')
            strategy_series_tr_to_chart_df_adj_ =  strategy_series_tr_to_chart_df_adj_.reset_index()

            mdd_selected = st.session_state.mainstratpl[strategy_selected_]
            mdd_selected['Port'] = mdd_selected.sum(axis=1)
            mdd_selected = mdd_selected.cumsum()
            mdd_selected = (mdd_selected - mdd_selected.cummax())
            mdd_selected = mdd_selected.reset_index()

        col1_c, col2_c = st.columns(2)
        with col1_c:
            if len(strategy_selected_) > 0:
                if len(strategy_selected) == 1:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]))
                
                elif len(strategy_selected) == 2:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"))
                
                elif len(strategy_selected) == 3:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 4:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.92]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 5:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.92]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.015),
                                        yaxis3=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 6:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.90]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.015),
                                        yaxis3=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.93),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.955), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.98))
                
                elif len(strategy_selected) == 7:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.065, 0.90]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                        yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                        yaxis4=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.93), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.98))
                    
                elif len(strategy_selected) == 8:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][7]], name=[str(c) for c in strategy_selected][7], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y8"))
                    
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
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][7]], name=[str(c) for c in strategy_selected][7], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y8"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][8]], name=[str(c) for c in strategy_selected][8], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y9"))
                    
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
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][7]], name=[str(c) for c in strategy_selected][7], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y8"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][8]], name=[str(c) for c in strategy_selected][8], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y9"))
                    fig_.add_trace(go.Scatter(x=strategy_series_tr_to_chart_df_adj_['Date'], y=strategy_series_tr_to_chart_df_adj_[[str(c) for c in strategy_selected][9]], name=[str(c) for c in strategy_selected][9], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y10"))
                    
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
        
        with col2_c:
            if len(strategy_selected_) > 0:
                if len(strategy_selected) == 1:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_m.update_layout(xaxis=dict(domain=[0.05, 0.95]))
                
                elif len(strategy_selected) == 2:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_m.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"))
                
                elif len(strategy_selected) == 3:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_m.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 4:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    
                    fig_m.update_layout(xaxis=dict(domain=[0.05, 0.92]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 5:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    
                    fig_m.update_layout(xaxis=dict(domain=[0.05, 0.92]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.015),
                                        yaxis3=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 6:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    
                    fig_m.update_layout(xaxis=dict(domain=[0.05, 0.90]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.015),
                                        yaxis3=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.93),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.955), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.98))
                
                elif len(strategy_selected) == 7:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    
                    fig_m.update_layout(xaxis=dict(domain=[0.065, 0.90]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                        yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                        yaxis4=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.93), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.98))
                    
                elif len(strategy_selected) == 8:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][7]], name=[str(c) for c in strategy_selected][7], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y8"))
                    
                    fig_m.update_layout(xaxis=dict(domain=[0.065, 0.865]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                        yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                        yaxis4=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.90), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.93),
                                        yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.96), 
                                        yaxis8=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 9:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][7]], name=[str(c) for c in strategy_selected][7], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y8"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][8]], name=[str(c) for c in strategy_selected][8], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y9"))
                    
                    fig_m.update_layout(xaxis=dict(domain=[0.095, 0.865]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.06),
                                        yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                        yaxis4=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                        yaxis5=dict(anchor="x",overlaying="y",side="right"), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.90),
                                        yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.93), 
                                        yaxis8=dict(anchor="free",overlaying="y",side="right", position=0.96),
                                        yaxis9=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(strategy_selected) == 10:
                    fig_m = go.Figure()
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][0]], name=[str(c) for c in strategy_selected][0], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][1]], name=[str(c) for c in strategy_selected][1], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][2]], name=[str(c) for c in strategy_selected][2], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][3]], name=[str(c) for c in strategy_selected][3], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][4]], name=[str(c) for c in strategy_selected][4], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][5]], name=[str(c) for c in strategy_selected][5], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][6]], name=[str(c) for c in strategy_selected][6], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y7"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][7]], name=[str(c) for c in strategy_selected][7], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y8"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][8]], name=[str(c) for c in strategy_selected][8], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y9"))
                    fig_m.add_trace(go.Scatter(x=mdd_selected['Date'], y=mdd_selected[[str(c) for c in strategy_selected][9]], name=[str(c) for c in strategy_selected][9], mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y10"))
                    
                    fig_m.update_layout(xaxis=dict(domain=[0.095, 0.835]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.06),
                                        yaxis3=dict(anchor="free",overlaying="y",side="left", position=0.03),
                                        yaxis4=dict(anchor="free",overlaying="y",side="left", position=0.0),
                                        yaxis5=dict(anchor="x",overlaying="y",side="right"), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.87),
                                        yaxis7=dict(anchor="free",overlaying="y",side="right", position=0.90), 
                                        yaxis8=dict(anchor="free",overlaying="y",side="right", position=0.93),
                                        yaxis9=dict(anchor="free",overlaying="y",side="right", position=0.96),
                                        yaxis10=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                fig_m.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")]))) 
                
                st.plotly_chart(fig_m, use_container_width=True)
            
        rates_strat_list = [s for s in mainstrat_list if "Rates_" in s]
        commodity_strat_list = [s for s in mainstrat_list if "Commodity_" in s]
        fx_strat_list = [s for s in mainstrat_list if "FX_" in s]
        equity_strat_list = [s for s in mainstrat_list if "Equity_" in s]

        col1_s, col2_s = st.columns(2)
        with col1_s:
            rates_strat_pl = st.session_state.mainstratpl[rates_strat_list].copy()
            rates_strat_pl['Rates Port'] = rates_strat_pl.mean(axis=1).values
            rates_strat_pl = rates_strat_pl[rates_strat_pl.index>='2012-08-01']
            rates_strat_pl_cum = rates_strat_pl.cumsum().fillna(method='ffill')
            rates_strat_pl_cum =  rates_strat_pl_cum.reset_index()
            
            fig_rates = px.line(rates_strat_pl_cum, x='Date', y=rates_strat_pl_cum.columns,hover_data={'Date': "|%B %d, %Y"},title='Rates Strategy')    
            fig_rates.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            st.plotly_chart(fig_rates, use_container_width=True)
            
            fx_strat_pl = st.session_state.mainstratpl[fx_strat_list].copy()
            fx_strat_pl['FX Port'] = fx_strat_pl.mean(axis=1).values
            fx_strat_pl = fx_strat_pl[fx_strat_pl.index>='2012-08-01']
            fx_strat_pl_cum = fx_strat_pl.cumsum().fillna(method='ffill')
            fx_strat_pl_cum =  fx_strat_pl_cum.reset_index()
     
            fig_fx = px.line(fx_strat_pl_cum, x='Date', y=fx_strat_pl_cum.columns,hover_data={'Date': "|%B %d, %Y"},title='FX Strategy')    
            fig_fx.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            st.plotly_chart(fig_fx, use_container_width=True)
            
        with col2_s:
            commodity_strat_pl = st.session_state.mainstratpl[commodity_strat_list].copy()
            commodity_strat_pl['Commodity Port'] = commodity_strat_pl.mean(axis=1).values
            commodity_strat_pl = commodity_strat_pl[commodity_strat_pl.index>='2012-08-01']
            commodity_strat_pl_cum = commodity_strat_pl.cumsum().fillna(method='ffill')
            commodity_strat_pl_cum =  commodity_strat_pl_cum.reset_index()
            
            fig_commodity = px.line(commodity_strat_pl_cum, x='Date', y=commodity_strat_pl_cum.columns,hover_data={'Date': "|%B %d, %Y"},title='Commodity Strategy')    
            fig_commodity.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            st.plotly_chart(fig_commodity, use_container_width=True)
            
            equity_strat_pl = st.session_state.mainstratpl[equity_strat_list].copy()
            equity_strat_pl['Equity Port'] = equity_strat_pl.mean(axis=1).values
            equity_strat_pl = equity_strat_pl[equity_strat_pl.index>='2012-08-01']
            equity_strat_pl_cum = equity_strat_pl.cumsum().fillna(method='ffill')
            equity_strat_pl_cum =  equity_strat_pl_cum.reset_index()
     
            fig_equity = px.line(equity_strat_pl_cum, x='Date', y=equity_strat_pl_cum.columns,hover_data={'Date': "|%B %d, %Y"},title='Equity Strategy')    
            fig_equity.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                rangeselector = dict(
                                buttons=list([
                                dict(count=1, label="1m", step="month", stepmode="backward"),
                                dict(count=6, label="6m", step="month", stepmode="backward"),
                                dict(count=1, label="YTD", step="year", stepmode="todate"),
                                dict(count=1, label="1y", step="year", stepmode="backward"),
                                dict(step="all")])))
            st.plotly_chart(fig_equity, use_container_width=True)

    with tab4:   
        def dict_merge(dict1, dict2):
            res = {**dict1, **dict2}
            return res       
          
        with st.expander('Strategy Weight '):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                rates_import_weight = st.radio('Rates Import Weight', ['True', 'False'])
            
            with col2:
                comm_import_weight = st.radio('Commodity Import Weight', ['True', 'False'])

            with col3:
                fx_import_weight = st.radio('FX Import Weight', ['True', 'False'])

            with col4:
                equity_import_weight = st.radio('Equity Import Weight', ['True', 'False'])
            
            rates_value_ = st.number_input('Rates Value ', value=0.0, step=0.25)
            rates_carry_ = st.number_input('Rates Carry ', value=0.0, step=0.25)
            rates_mom_ = st.number_input('Rates Momentum ', value=0.0, step=0.25)
            #rates_coskew_ = st.number_input('Rates Coskew ', value=0.0, step=0.25)
            rates_vol_ = st.number_input('Rates Volatility ', value=0.0, step=0.25)
            rates_trend_ = st.number_input('Rates Trend ', value=0.0, step=0.25)
            rates_mr_ = st.number_input('Rates MeanReversion ', value=0.0, step=0.25)
            comm_value_ = st.number_input('Commodity Value ', value=0.0, step=0.25)
            comm_carry_ = st.number_input('Commodity Carry ', value=0.0, step=0.25)
            comm_mom_ = st.number_input('Commodity Momentum ', value=0.0, step=0.25)
            comm_cftc_ = st.number_input('Commodity CFTC ',  value=0.0, step=0.25)
            comm_bmom_ = st.number_input('Commodity BasisMomentum ', value=0.0, step=0.25)
            comm_trend_ = st.number_input('Commodity Trend ', value=0.0, step=0.25)
            fx_value_ = st.number_input('FX Value ', value=0.0, step=0.25)
            fx_carry_ = st.number_input('FX Carry ', value=0.0, step=0.25)
            fx_mom_ = st.number_input('FX Momentum ', value=0.0, step=0.25)
            fx_cftc_ = st.number_input('FX CFTC ', value=0.0, step=0.25)
            fx_skew_ = st.number_input('FX Skew ', value=0.0, step=0.25)
            fx_bmom_ = st.number_input('FX BasisMomentum ', value=0.0, step=0.25)
            fx_trend_ = st.number_input('FX Trend ', value=0.0, step=0.25)
            equity_value_ = st.number_input('Equity Value ', value=0.0, step=0.25)
            equity_carry_ = st.number_input('Equity Carry ', value=0.0, step=0.25)
            equity_mom_ = st.number_input('Equity Momentum ', value=0.0, step=0.25)
            equity_coskew_ = st.number_input('Equity Coskew ', value=0.0, step=0.25)
            equity_momvol_ = st.number_input('Equity Momvol ', value=0.0, step=0.25)
            equity_vol_ = st.number_input('Equity Volatility ', value=0.0, step=0.25)
            equity_factor_ = st.number_input('Equity Factor ', value=0.0, step=0.25)
            equity_trend_ = st.number_input('Equity Trend ', value=0.0, step=0.25)

            if rates_import_weight == 'True':
                rates_strategy_name_dict = {'rates_value':st.session_state.strategy_weight_dict['Rates_Value'],
                                            'rates_carry':st.session_state.strategy_weight_dict['Rates_Carry'],
                                            'rates_momentum':st.session_state.strategy_weight_dict['Rates_Momentum'], 
                                            #'rates_coskew':st.session_state.strategy_weight_dict['Rates_Coskew'],
                                            'rates_volatility':st.session_state.strategy_weight_dict['Rates_Volatility'], 
                                            'rates_trend':st.session_state.strategy_weight_dict['Rates_Trend'], 
                                            'rates_meanreversion':st.session_state.strategy_weight_dict['Rates_MeanReversion']
                                            }
            
            else:
                rates_strategy_name_dict = {'rates_value':rates_value_,
                                            'rates_carry':rates_carry_,
                                            'rates_momentum':rates_mom_, 
                                            #'rates_coskew':rates_coskew_,
                                            'rates_volatility':rates_vol_, 
                                            'rates_trend':rates_trend_, 
                                            'rates_meanreversion':rates_mr_
                                            }
            
            if comm_import_weight == 'True':
                comm_strategy_name_dict = {'commodity_value':st.session_state.strategy_weight_dict['Commodity_Value'], 
                                            'commodity_carry':st.session_state.strategy_weight_dict['Commodity_Carry'],
                                            'commodity_momentum':st.session_state.strategy_weight_dict['Commodity_Momentum'], 
                                            'commodity_cftc':st.session_state.strategy_weight_dict['Commodity_CFTC'], 
                                            'commodity_bmom':st.session_state.strategy_weight_dict['Commodity_BasisMomentum'], 
                                            'commodity_mcycle':st.session_state.strategy_weight_dict['Commodity_Macrocycle'], 
                                            'commodity_trend':st.session_state.strategy_weight_dict['Commodity_Trend'], 
                                            }
                
            else:
                comm_strategy_name_dict = {'commodity_value':comm_value_, 
                                            'commodity_carry':comm_carry_,
                                            'commodity_momentum':comm_mom_, 
                                            'commodity_cftc':comm_cftc_, 
                                            'commodity_bmom':comm_bmom_, 
                                            'commodity_trend':comm_trend_, 
                                            }
            
            if fx_import_weight == 'True':
                fx_strategy_name_dict = {'fx_value':st.session_state.strategy_weight_dict['FX_Value'], 
                                        'fx_carry':st.session_state.strategy_weight_dict['FX_Carry'], 
                                        'fx_momentum':st.session_state.strategy_weight_dict['FX_Momentum'], 
                                        'fx_cftc':st.session_state.strategy_weight_dict['FX_CFTC'],
                                        'fx_skew':st.session_state.strategy_weight_dict['FX_Skew'],
                                        'fx_bmom':st.session_state.strategy_weight_dict['FX_BasisMomentum'],
                                        'fx_hflow':st.session_state.strategy_weight_dict['FX_Hedgeflow'],
                                        'fx_trend':st.session_state.strategy_weight_dict['FX_Trend'], 
                                        }
            
            else:
                fx_strategy_name_dict = {'fx_value':fx_value_, 
                                    'fx_carry':fx_carry_, 
                                    'fx_momentum':fx_mom_, 
                                    'fx_cftc':fx_cftc_,
                                    'fx_skew':fx_skew_,
                                    'fx_bmom':fx_bmom_,
                                    'fx_hflow':fx_hflow_,
                                    'fx_trend':fx_trend_, 
                                    }
        
            if equity_import_weight == 'True':
                equity_strategy_name_dict = {'equity_value':st.session_state.strategy_weight_dict['Equity_Value'], 
                                            'equity_carry':st.session_state.strategy_weight_dict['Equity_Carry'],  
                                            'equity_momentum':st.session_state.strategy_weight_dict['Equity_Momentum'],
                                            'equity_coskew':st.session_state.strategy_weight_dict['Equity_Coskew'], 
                                            'equity_momvol':st.session_state.strategy_weight_dict['Equity_Momvol'], 
                                            'equity_volatility':st.session_state.strategy_weight_dict['Equity_Volatility'], 
                                            'equity_factor':st.session_state.strategy_weight_dict['Equity_Factor'], 
                                            'equity_trend':st.session_state.strategy_weight_dict['Equity_Trend'], 
                                            }
            
            else:
                equity_strategy_name_dict = {'equity_value':equity_value_, 
                                            'equity_carry':equity_carry_,  
                                            'equity_momentum':equity_mom_,
                                            'equity_coskew':equity_coskew_, 
                                            'equity_momvol':equity_momvol_, 
                                            'equity_volatility':equity_vol_, 
                                            'equity_factor':equity_factor_, 
                                            'equity_trend':equity_trend_, 
                                            }

        strategy_name_dict = dict_merge(rates_strategy_name_dict, dict_merge(comm_strategy_name_dict, dict_merge(fx_strategy_name_dict, equity_strategy_name_dict)))

        col1, col2, col3 = st.columns(3)
        with col1:
            rf_lookback = st.slider('Random Forest Lookback', 0, 500, step=10)
        with col2:
            reg_lookback = st.slider('Regression Lookback', 0, 1250, step=10)
        with col3:
            col3_1, col3_2 = st.columns(2)
            with col3_1:
                strategy_port_date = datetime.strftime(st.date_input('Portfolio Date'), "%Y-%m-%d")
            with col3_2:
                st.markdown('')
                st.markdown('')
                start_button = st.button('Analyze', use_container_width=True)

        new_strategy_name_dict = {}
        for k, v in strategy_name_dict.items():
            if v > 0:
                new_strategy_name_dict[k] = v
        
        if start_button:
            portfolio_correlation, factor_sensitivity, current_position, portfolio_series, delta_df = rpa.macro_factor_analysis_port(new_strategy_name_dict, rf_lookback, reg_lookback, strategy_port_date)
            
            with st.container():
                portfolio_series = portfolio_series.reset_index()
                fig_strat = px.line(portfolio_series, x='Date', y=portfolio_series.columns,hover_data={'Date': "|%B %d, %Y"})    
                fig_strat.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                st.plotly_chart(fig_strat, use_container_width=True)

            with st.container():
                col1, col2, col3 = st.columns(3)
                with col1:
                    ticker_name_match_dict = rpa.dict_merge(rpa.dict_merge(rpa.dict_merge(ticker_name_match_dict_commodity,ticker_name_match_dict_rates), ticker_name_match_dict_fx),ticker_name_match_dict_equity)
                    ticker_name_match_dict['ED4 Comdty'] = 'Eurodollar' #보정
                    current_position['Name'] = [ticker_name_match_dict[k] for k in current_position['Ticker'].values.tolist()]
                    current_position = current_position[['Ticker', 'Name', 'Position']]
                    st.dataframe(current_position, height = 630, use_container_width=True)
                with col2:
                    st.dataframe(factor_sensitivity.set_index('Factor'), width = 630, height = 630)
                with col3:
                    st.dataframe(portfolio_correlation.style.background_gradient(cmap='RdBu'), height=630, use_container_width=True)
                
            st.divider()
            with st.container():
                delta_df = delta_df.reset_index()
                fig_delta = px.line(delta_df, x='Date', y=delta_df.columns,hover_data={'Date': "|%B %d, %Y"})    
                fig_delta.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                st.plotly_chart(fig_delta, use_container_width=True)
                st.dataframe(delta_df.set_index('Date').dropna().T)
            
    with tab5:
        palceholder = st.empty()
        pw = palceholder.text_input("Enter Password : ")
        if pw == 'macroquant7777':
            palceholder.empty()
        
            col1_ss, col2_ss = st.columns(2)
            with col1_ss:
                selected_asset = st.selectbox('Select Asset Type', ['Rates', 'Commodity', 'FX', 'Equity'])
                selected_asset = selected_asset.lower()
            with col2_ss:
                pos_date = datetime.strftime(st.date_input('Position Date  '), "%Y-%m-%d")

            feature_position = feature_pos
            feature_list = list(set(feature_position['Strategy'].values))
            feature_position = feature_position.groupby(['Date', 'Ticker', 'Strategy']).sum().reset_index()
            feature_pnl = feature_pl.copy()
            
            if selected_asset == 'rates':
                feature_list_selected = [s for s in feature_list if 'rates_' in s]
                ticker_order = ticker_name_match_dict_rates
            
            elif selected_asset == 'commodity':
                feature_list_selected = [s for s in feature_list if 'commodity_' in s]
                ticker_order = ticker_name_match_dict_commodity
            
            elif selected_asset == 'fx':
                feature_list_selected = [s for s in feature_list if 'fx_' in s]
                ticker_order = ticker_name_match_dict_fx
            
            elif selected_asset == 'equity':
                feature_list_selected = [s for s in feature_list if 'equity_' in s]
                ticker_order = ticker_name_match_dict_equity

            pnl = feature_pnl[feature_list_selected]
            pos = feature_position[feature_position['Date']<= pos_date]
            
            for i, k in enumerate(feature_list_selected):
                if i == 0:
                    strat_feature_pos = pos[pos['Strategy']==k].pivot(index='Date', columns='Ticker', values='Position').iloc[-1,:]
                    strat_feature_pos.name = k
                else:
                    strat_feature_pos_ = pos[pos['Strategy']==k].pivot(index='Date', columns='Ticker', values='Position').iloc[-1,:]
                    strat_feature_pos_.name = k
                    strat_feature_pos = pd.concat([strat_feature_pos, strat_feature_pos_], axis=1)
            
            strat_feature_pos = strat_feature_pos .T[list(ticker_order.keys())].T
            strat_feature_pos_columns = list(strat_feature_pos.columns)
            strat_feature_pos['Name'] = list(ticker_order.values())
            strat_feature_pos = strat_feature_pos[['Name']+strat_feature_pos_columns].replace({np.nan:0}).style.applymap(style_negative, props='color:red;').format(precision=1, thousands=",", decimal=".")
            st.dataframe(strat_feature_pos, use_container_width=True)

            st.text_area('전략별 비중', '', height=100)

            feature_select = st.multiselect("Select Features", feature_list_selected, max_selections=6)
            col1_f, col2_f = st.columns(2)
            with col1_f:
                if len(feature_select)==1 or len(feature_select)==2:
                    pl1 = pnl[[feature_select[0]]]
                    pl1 = pl1.cumsum().fillna(method='ffill')
                    pl1 = pl1.reset_index().rename(columns={'index':'Date'})
                    fig = px.line(pl1 , x='Date', y=pl1.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[0])    
                    fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig, use_container_width=True)

                elif len(feature_select)==3 or len(feature_select)==4:
                    pl1 = pnl[[feature_select[0]]]
                    pl1 = pl1.cumsum().fillna(method='ffill')
                    pl1 = pl1.reset_index().rename(columns={'index':'Date'})
                    fig1 = px.line(pl1 , x='Date', y=pl1.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[0])    
                    fig1.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig1, use_container_width=True)

                    pl3 = pnl[[feature_select[2]]]
                    pl3 = pl3.cumsum().fillna(method='ffill')
                    pl3 = pl3.reset_index().rename(columns={'index':'Date'})
                    fig3 = px.line(pl3 , x='Date', y=pl3.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[2])    
                    fig3.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig3, use_container_width=True)

                elif len(feature_select)==5 or len(feature_select)==6:
                    pl1 = pnl[[feature_select[0]]]
                    pl1 = pl1.cumsum().fillna(method='ffill')
                    pl1 = pl1.reset_index().rename(columns={'index':'Date'})
                    fig1 = px.line(pl1 , x='Date', y=pl1.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[0])    
                    fig1.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig1, use_container_width=True)

                    pl3 = pnl[[feature_select[2]]]
                    pl3 = pl3.cumsum().fillna(method='ffill')
                    pl3 = pl3.reset_index().rename(columns={'index':'Date'})
                    fig3 = px.line(pl3 , x='Date', y=pl3.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[2])    
                    fig3.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig3, use_container_width=True)

                    pl5 = pnl[[feature_select[4]]]
                    pl5 = pl5.cumsum().fillna(method='ffill')
                    pl5 = pl5.reset_index().rename(columns={'index':'Date'})
                    fig5 = px.line(pl5 , x='Date', y=pl5.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[4])    
                    fig5.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig5, use_container_width=True)

            with col2_f:
                if len(feature_select)==2 or len(feature_select)==3:
                    pl2 = pnl[[feature_select[1]]]
                    pl2 = pl2.cumsum().fillna(method='ffill')
                    pl2 = pl2.reset_index().rename(columns={'index':'Date'})
                    fig2 = px.line(pl2 , x='Date', y=pl2.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[1])    
                    fig2.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig2, use_container_width=True)

                elif len(feature_select)==4 or len(feature_select)==5:
                    pl2 = pnl[[feature_select[1]]]
                    pl2 = pl2.cumsum().fillna(method='ffill')
                    pl2 = pl2.reset_index().rename(columns={'index':'Date'})
                    fig2 = px.line(pl2 , x='Date', y=pl2.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[1])    
                    fig2.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig2, use_container_width=True)

                    pl4 = pnl[[feature_select[3]]]
                    pl4 = pl4.cumsum().fillna(method='ffill')
                    pl4 = pl4.reset_index().rename(columns={'index':'Date'})
                    fig4 = px.line(pl4 , x='Date', y=pl4.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[3])    
                    fig4.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig4, use_container_width=True)

                elif len(feature_select)==6:
                    pl2 = pnl[[feature_select[1]]]
                    pl2 = pl2.cumsum().fillna(method='ffill')
                    pl2 = pl2.reset_index().rename(columns={'index':'Date'})
                    fig2 = px.line(pl2 , x='Date', y=pl2.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[1])    
                    fig2.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig2, use_container_width=True)

                    pl4 = pnl[[feature_select[3]]]
                    pl4 = pl4.cumsum().fillna(method='ffill')
                    pl4 = pl4.reset_index().rename(columns={'index':'Date'})
                    fig4 = px.line(pl4 , x='Date', y=pl4.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[3])    
                    fig4.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig4, use_container_width=True)

                    pl6 = pnl[[feature_select[5]]]
                    pl6 = pl6.cumsum().fillna(method='ffill')
                    pl6 = pl6.reset_index().rename(columns={'index':'Date'})
                    fig6 = px.line(pl6 , x='Date', y=pl6.columns,hover_data={'Date': "|%B %d, %Y"},title=feature_select[5])    
                    fig6.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig6, use_container_width=True)



main_strategy_weight = {'Commodity_Value':2, 
                        'Commodity_Carry':1,
                        'Commodity_Momentum':1, 
                        'Commodity_CFTC':2, 
                        'Commodity_BasisMomentum':2, 
                        'Commodity_BasisMomentum':1, 
                        'Equity_Value':2, 
                        'Equity_Carry':2,  
                        'Equity_Momentum':0.5,
                        'Equity_Coskew':0.5, 
                        'Equity_Volatility':1, 
                        'FX_Value':9, 
                        'FX_Skew':5,
                        'FX_Carry':5, 
                        'FX_Momentum':6, 
                        'FX_CFTC':11,
                        'FX_BasisMomentum':12,
                        'FX_Hedgeflow':1,
                        'Rates_Value':1,
                        'Rates_Carry':1,
                        'Rates_Momentum':0.5, 
                        'Rates_Coskew':0.5,
                        'Rates_Volatility':1, 
                        'Rates_Trend':0.25, 
                        'Rates_MeanReversion':1
                        }