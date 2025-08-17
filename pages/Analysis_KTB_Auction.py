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
import QuantLib as ql
from scipy.stats import norm
import sys
sys.path.append(file_dir)
#from Strategy_MA_Optimal_Portfolio import MultiAssetPortDataProcess
from Feature_MacroFundamental import MacroFactor
from Feature_Preprocessing import RatesDataProcess
from Strategy_KTB_Auction import KTBAuction
from MPTSRT_PositionDB import db_execute_manager as dbm_p
dbm = dbm_p.DBExecuteManager()

if 'note' not in st.session_state:
    st.session_state.note = ''

st.session_state.note = st.sidebar.text_area('Note', st.session_state.note, height=300)

@st.cache_resource
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('EUC-KR')

@st.cache_resource(show_spinner=False)
def pull_strategy_data():
    dp = RatesDataProcess('2012-10-01', date.today().isoformat())
    return dp

@st.cache_data(show_spinner=False)
def pull_price_data():
    query = "SELECT CLPR_FRMT_DATE, STND_ISCD, CLPR_ERT FROM positiondb.tb_clpr;"
    price = pd.DataFrame([[x[0], x[1], float(x[2])] for x in dbm.get_fetchall(query)], columns=['Date', 'STND_ISCD', 'CLPR']).set_index('Date')
    return price

@st.cache_data(show_spinner=False)
def pull_bok_price_data():
    query = "SELECT CLPR_DATE, CLPR FROM macrodb.tb_mcro_clpr WHERE TCKR = 'KORP7DR Index';"
    price = pd.DataFrame([[x[0],float(x[1])] for x in dbm.get_fetchall(query)], columns=['Date','BOK']).set_index('Date')
    return price

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
def get_auction_data():
    #dbm = dbm_p.DBExecuteManager()
    auct_q = "SELECT AUCT_DATE, STND_ISCD, MIN_BID_ERT, MAX_BID_ERT, PLMT_ERT, PLMT_AMT, BID_RATE FROM positiondb.tb_comp_ofer;"
    auct_data = pd.DataFrame([list(x) for x in dbm.get_fetchall(auct_q)], columns=['Auction Date', 'Code', 'Min Bid Price', 'Max Bid Price', 'Offer Price', 'Amount', 'Bid Rate'])

    ktb_info_q = "SELECT STND_ISCD, KOR_ISNM, PBLC_DATE, RDMP_DATE FROM positiondb.tb_ktb;"
    ktb_info_data = pd.DataFrame([list(x) for x in dbm.get_fetchall(ktb_info_q)], columns=['Code', 'Name', 'Public Date', 'Redemption Date'])
    ktb_info_data = ktb_info_data[['Code', 'Name']]
    
    dur_q = "SELECT RCD_DATE, STND_ISCD, MATU_CLAS FROM positiondb.tb_dur;"
    dur_data = pd.DataFrame([list(x) for x in dbm.get_fetchall(dur_q)], columns=['Date', 'Code', 'Maturity'])
    dur_data = dur_data[dur_data['Code'].isin(list(set(auct_data['Code'])))].set_index('Date').reset_index()
    dur_data['ix'] = dur_data['Date']+dur_data['Code']
    dur_data = dur_data[['ix','Maturity']]

    noncomp_q = "SELECT AUCT_DATE_STRT, STND_ISCD, PLMT_AMT_ORD, PLMT_AMT_OPT, PLMT_AMT_STRP FROM positiondb.tb_noncomp_ofer;"
    noncomp_data = pd.DataFrame([list(x) for x in dbm.get_fetchall(noncomp_q)], columns=['Date', 'Code', 'Option_Ord', 'Option_Opt', 'Option_Strp'])
    noncomp_data['Noncomp'] = noncomp_data[['Option_Ord', 'Option_Opt', 'Option_Strp']].sum(axis=1)
    noncomp_data['ix'] = noncomp_data['Date']+noncomp_data['Code']
    noncomp_data = noncomp_data[['ix', 'Noncomp']]
    
    auct_data = pd.merge(auct_data, ktb_info_data, how='left', on='Code')
    auct_data['ix'] = auct_data['Auction Date']+auct_data['Code']
    auct_data = pd.merge(auct_data, dur_data, how='left', on='ix')
    auct_data = pd.merge(auct_data, noncomp_data, how='left', on='ix')

    auct_data = auct_data[['Auction Date', 'Code', 'Name', 'Maturity','Min Bid Price', 'Max Bid Price', 'Offer Price', 'Bid Rate', 'Amount', 'Noncomp']]
    auct_data = auct_data.replace('18M', '2Y').replace(np.nan, 0)
    auct_data = auct_data[auct_data['Auction Date']>='2007-07-01']

    def ktbi_exclusion(x):
        if '물가' in x:
            b = 0
        else:
            b = 1
        return b
    
    auct_data['KTBi Bool'] = auct_data['Name'].apply(lambda x:ktbi_exclusion(x))
    auct_data = auct_data[auct_data['KTBi Bool']==1]
    auct_data = auct_data[['Auction Date', 'Code', 'Name', 'Maturity','Min Bid Price', 'Max Bid Price', 'Offer Price', 'Bid Rate', 'Amount', 'Noncomp']]

    return auct_data  

@st.cache_resource(show_spinner=False)
def get_strategy_score(strategy, strategy_date_list, horizon_before, horizon_after):
    strategy_event = {}
    strategy_score = {}
    strategy_score_before = {}
    strategy_score_after = {}
    strategy_win = []
    for k, v in strategy.items():
        strategy_event_list = []
        if type(k) == str:
            if 'KTB' in k and 'IL' not in k and 'BE' not in k:
                for dt in strategy_date_list:
                    strat_value = list(v.values[list(v.index).index(dt)-horizon_before:list(v.index).index(dt)+horizon_after+1])
                    strat_value = np.round(strat_value + [np.nan for x in range(len(strat_value)) if x < (horizon_before+horizon_after)+1-len(strat_value)],3)
                    strategy_event_list.append(strat_value)
                strategy_event[k] = strategy_event_list
                strategy_event_df = pd.DataFrame(strategy_event_list)
                strategy_event_df = strategy_event_df.sub(strategy_event_df[horizon_before], axis='index').T
                strategy_event_df_ = strategy_event_df.fillna(method='ffill').T
                strategy_win.append([str(k), sum((np.sign(strategy_event_df_[horizon_after+horizon_before] - strategy_event_df_[0])==1)), sum((np.sign(strategy_event_df_[horizon_after+horizon_before] - strategy_event_df_[0])==-1))])
                score = strategy_event_df.mean(axis=1)[horizon_after+horizon_before] - strategy_event_df.mean(axis=1)[0]
                score_before = strategy_event_df.mean(axis=1)[horizon_before] - strategy_event_df.mean(axis=1)[0]
                score_after = strategy_event_df.mean(axis=1)[horizon_after+horizon_before] - strategy_event_df.mean(axis=1)[+horizon_before]
                strategy_score[k] = score
                strategy_score_before[k] = score_before
                strategy_score_after[k] = score_after

        elif len(k) == 2:
            if 'KTB' in k[0] and 'KTB' in k[1] and 'IL' not in k[0] and 'IL' not in k[1] and 'BE' not in k[0] and 'BE' not in k[1]:
                for dt in strategy_date_list:
                    strat_value = list(v.values[list(v.index).index(dt)-horizon_before:list(v.index).index(dt)+horizon_after+1])
                    strat_value = np.round(strat_value + [np.nan for x in range(len(strat_value)) if x < (horizon_before+horizon_after)+1-len(strat_value)],3)
                    strategy_event_list.append(strat_value)
                strategy_event[k] = strategy_event_list
                strategy_event_df = pd.DataFrame(strategy_event_list)
                strategy_event_df = strategy_event_df.sub(strategy_event_df[horizon_before], axis='index').T
                strategy_event_df_ = strategy_event_df.fillna(method='ffill').T
                strategy_win.append([str(k), sum((np.sign(strategy_event_df_[horizon_after+horizon_before] - strategy_event_df_[0])==1)), sum((np.sign(strategy_event_df_[horizon_after+horizon_before] - strategy_event_df_[0])==-1))])
                score = strategy_event_df.mean(axis=1)[horizon_after+horizon_before] - strategy_event_df.mean(axis=1)[0]
                score_before = strategy_event_df.mean(axis=1)[horizon_before] - strategy_event_df.mean(axis=1)[0]
                score_after = strategy_event_df.mean(axis=1)[horizon_after+horizon_before] - strategy_event_df.mean(axis=1)[+horizon_before]
                strategy_score[k] = score
                strategy_score_before[k] = score_before
                strategy_score_after[k] = score_after

        elif len(k) == 3:
            if 'KTB' in k[0] and 'KTB' in k[1] and 'KTB' in k[2] and 'IL' not in k[0] and 'IL' not in k[1] and 'IL' not in k[2] and 'BE' not in k[0] and 'BE' not in k[1] and 'BE' not in k[2]:
                for dt in strategy_date_list:
                    strat_value = list(v.values[list(v.index).index(dt)-horizon_before:list(v.index).index(dt)+horizon_after+1])
                    strat_value = np.round(strat_value + [np.nan for x in range(len(strat_value)) if x < (horizon_before+horizon_after)+1-len(strat_value)], 3)
                    strategy_event_list.append(strat_value)
                strategy_event[k] = strategy_event_list
                strategy_event_df = pd.DataFrame(strategy_event_list)
                strategy_event_df = strategy_event_df.sub(strategy_event_df[horizon_before], axis='index').T
                strategy_event_df_ = strategy_event_df.fillna(method='ffill').T
                strategy_win.append([str(k), sum((np.sign(strategy_event_df_[horizon_after+horizon_before] - strategy_event_df_[0])==1)), sum((np.sign(strategy_event_df_[horizon_after+horizon_before] - strategy_event_df_[0])==-1))])
                score = strategy_event_df.mean(axis=1)[horizon_after+horizon_before] - strategy_event_df.mean(axis=1)[0]
                score_before = strategy_event_df.mean(axis=1)[horizon_before] - strategy_event_df.mean(axis=1)[0]
                score_after = strategy_event_df.mean(axis=1)[horizon_after+horizon_before] - strategy_event_df.mean(axis=1)[+horizon_before]
                strategy_score[k] = score
                strategy_score_before[k] = score_before
                strategy_score_after[k] = score_after
    
    strategy_score_df = pd.DataFrame(strategy_score.items(), columns=['Strategy', 'Score'])
    strategy_score_df['Strategy'] = [str(s) for s in strategy_score_df['Strategy']]
    strategy_score_df = strategy_score_df.set_index('Strategy')
    strategy_score_before_df = pd.DataFrame(strategy_score_before.items(), columns=['Strategy', 'Score Before'])
    strategy_score_before_df['Strategy'] = [str(s) for s in strategy_score_before_df['Strategy']]
    strategy_score_before_df = strategy_score_before_df.set_index('Strategy')
    strategy_score_after_df = pd.DataFrame(strategy_score_after.items(), columns=['Strategy', 'Score After'])
    strategy_score_after_df['Strategy'] = [str(s) for s in strategy_score_after_df['Strategy']]
    strategy_score_after_df = strategy_score_after_df.set_index('Strategy')
    strategy_win_df = pd.DataFrame(strategy_win, columns=['Strategy', 'Up', 'Down']).set_index('Strategy')
    strategy_score_win_df = pd.concat([strategy_score_df,strategy_score_before_df,strategy_score_after_df,strategy_win_df], axis=1)
    strategy_score_win_df['Up/Down'] = strategy_score_win_df['Up']/(strategy_score_win_df['Down']+strategy_score_win_df['Up'])
    return strategy_score_win_df, strategy_event

@st.cache_resource(show_spinner=False)
def get_strategy_event_date_pair(strategy_event, strategy_date_list):
    strategy_event_date_pair = []
    strategy_clpr_date_pair = []
    for k,v in strategy_event.items():
        strategy_event_date_pair += [[str(k)]+ list(np.round((pd.DataFrame(v).iloc[:, -1] - pd.DataFrame(v).iloc[:, 0]).values, 4))]
        strat = strategy[k] 
        strategy_clpr_date_pair += [[str(k)]+list(np.round(strat[strat.index.isin(strategy_date_list)].values,4))]

    strategy_event_date_pair_df = pd.DataFrame(strategy_event_date_pair)
    strategy_event_date_pair_df.columns = ['Strategy']+strategy_date_list
    strategy_clpr_date_pair_df = pd.DataFrame(strategy_clpr_date_pair)
    strategy_clpr_date_pair_df.columns = ['Strategy']+strategy_date_list
    
    return strategy_event_date_pair_df.set_index('Strategy'), strategy_clpr_date_pair_df.set_index('Strategy')


@st.cache_resource(show_spinner=False)
def get_strategy_event_date_vs_bok(strat_select, strategy_date_list, strategy_outright, bok_outright):

    outright_rate = pd.concat([strategy_outright, bok_outright], axis=1, sort=True).fillna(method='ffill')
    result = []
    for s in strat_select:
        sub_result = []
        for d in strategy_date_list:
            sub_result.append(outright_rate[outright_rate.index==d][s].values[0] - outright_rate[outright_rate.index==d]['BOK'].values[0])
        result.append(sub_result)

    return pd.DataFrame(result, columns=strategy_date_list, index=strat_select)

@st.cache_data(show_spinner=False)
def get_auction_sort(auction_data_df, clpr, us_rate_change, noncomp, dday_month):
    auction_data_df_ = auction_data_df.copy().sort_index()
    original_columns = auction_data_df.columns
    us_rate = dp.ustf
    auction_data_df_['Date'] = auction_data_df_.index
    us_rate_diff = (us_rate[['10Y_FUT_US']]-us_rate[['10Y_FUT_US']].shift(1)).shift(1)*100
    auction_data_df_['US Rate'] = auction_data_df_['Date'].apply(lambda x: np.round(us_rate_diff[us_rate_diff.index<=x]['10Y_FUT_US'][-1],2)) 
    auction_data_df_['US Rate Bool'] = [1 if abs(x) >= abs(us_rate_change) and np.sign(x) == np.sign(us_rate_change) else 1 if us_rate_change == 0 else 0 for x in list(auction_data_df_['US Rate'].values)]
    auction_data_df_['Month Bool'] = [1 if x in dday_month else 0 for x in list(pd.DatetimeIndex(auction_data_df_['Date']).month)]
    auction_data_df_['Noncomp Bool'] = [1 if x>0 and noncomp==True else 1 if noncomp==False else 0 for x in list(auction_data_df_['Noncomp'].values)]
    auction_data_df_ = auction_data_df_[(auction_data_df_['US Rate Bool']==1)&(auction_data_df_['Month Bool']==1)&(auction_data_df_['Noncomp Bool']==1)]
    
    def get_previous_rate(stnd_iscd, date):
        clpr_ = clpr[clpr['STND_ISCD']==stnd_iscd]['CLPR'].shift(1)
        return clpr_[clpr_.index<=date][-1]
    
    auction_data_df_['Previous Date Price'] = auction_data_df_[['Code','Date']].apply(lambda x:get_previous_rate(x.Code, x.Date), axis=1).fillna(auction_data_df_['Offer Price'])
    auction_data_df_['vs Previous Date'] = (auction_data_df_['Offer Price'].astype(float) - auction_data_df_['Previous Date Price'].astype(float))*100
    auction_data_df_ = auction_data_df_[list(original_columns)+['US Rate']+['vs Previous Date']]
    
    return auction_data_df_.sort_index()

@st.cache_data(show_spinner=False)
def real_money_trade(trade_borrow_data, end_date):
    trade_borrow_data = trade_borrow_data[trade_borrow_data['DATE']<=end_date]
    stnd_iscd_list = list(set(trade_borrow_data['CODE'].values))
    result = {}
    for i, stnd_iscd in enumerate(stnd_iscd_list):
        #print(stnd_iscd_list.index(stnd_iscd)/len(stnd_iscd_list))

        istu = {'외국인':1, '금융투자':2, '보험':3, '자산운용':4, '은행':5, '종합금융':6, '기타금융':7, '기금/공제':8, '국가지자체 등':9, '기타법인':10, '개인':11}

        sq_df = trade_borrow_data[trade_borrow_data['CODE']==stnd_iscd]
        sq_df_trd = sq_df.pivot_table(values='AMT', index='DATE', columns='ISTU')
        sq_df_trd = sq_df_trd.where(pd.notnull(sq_df_trd), 0)
        sq_df_trd = pd.merge(sq_df_trd.reset_index(), sq_df[['DATE', 'NAME', 'MATU_CLAS', 'DUR','RDMP', 'PRE_STRP_AMT', 'BROW_AMT', 'YIELD', 'MKT_YIELD']].groupby('DATE').last(), how='left', on='DATE')
        sq_df_trd = sq_df_trd.fillna(method='ffill')

        for ist in ['01','02', '03', '04','05','08']:
            if ist not in sq_df_trd.columns:
                sq_df_trd[ist] = 0
        
        sq_df_trd['Spread'] = (sq_df_trd['YIELD'] - sq_df_trd['MKT_YIELD'])
        sq_df_trd['Real Money'] = sq_df_trd[['01', '03', '04', '08']].sum(axis=1)
        sq_df_trd['Trading'] = sq_df_trd[['02', '05']].sum(axis=1)
        sq_df_trd['Real Money Cum'] = sq_df_trd['Real Money'].cumsum()
        sq_df_trd['Trading Cum'] = sq_df_trd['Trading'].cumsum() + sq_df_trd['PRE_STRP_AMT']
        sq_df_trd['Real Money Ratio'] = sq_df_trd['Real Money Cum']/sq_df_trd['PRE_STRP_AMT']
        sq_df_trd['Trading Ratio'] = sq_df_trd['Trading Cum']/sq_df_trd['PRE_STRP_AMT']
        sq_df_trd['Borrow Ratio'] = sq_df_trd['BROW_AMT']/ sq_df_trd['Real Money Cum']
        sq_df_trd['Outperformance'] = 100*((sq_df_trd['YIELD']-sq_df_trd['YIELD'].shift(1))-(sq_df_trd['MKT_YIELD']-sq_df_trd['MKT_YIELD'].shift(1)))
        sq_df_trd['Outperformance Cum'] = sq_df_trd['Outperformance'].cumsum()
        sq_df_trd['CODE'] = stnd_iscd
        sq_df_trd_ = sq_df_trd[['CODE', 'NAME', 'MATU_CLAS', 'DUR','RDMP', 'DATE', 'YIELD', 'MKT_YIELD', 'Spread', 'PRE_STRP_AMT', 'BROW_AMT', 'Real Money Cum', 'Trading Cum', 'Real Money Ratio', 'Trading Ratio', 'Borrow Ratio', 'Outperformance', 'Outperformance Cum']]
        sq_df_trd_.columns = ['Code', 'Name', 'Maturity Class' ,'Duration','Maturity Date', 'Date', 'Yield', 'Market Yield', 'Spread', 'Pre Strip Listed', 'Borrow', 'Real Money Cum', 'Trading Cum', 'Real Money Ratio', 'Trading Ratio', 'Borrow Ratio', 'Outperformance', 'Outperformance Cum']
        sq_df_trd_ = sq_df_trd_.set_index('Date')
        
        ret = sq_df_trd[['Real Money Cum']] - sq_df_trd[['Real Money Cum']].shift(1)
        for j, lb in enumerate([20,60,120,250]):
            #trend following 델타 계산
            avg_ret = ret.rolling(lb).mean()
            vol_ret = ret.rolling(lb).std()
            d1 = np.sqrt(lb)*avg_ret/vol_ret
            call_delta = pd.DataFrame(norm.cdf(d1), index=d1.index, columns=d1.columns)
            put_delta = call_delta - 1
            straddle_delta = (call_delta + put_delta) #*-1의 경우 mean reversion
            ewma_delta = straddle_delta.ewm(alpha=3/11).mean()
            
            if j == 0:
                delta_df = ewma_delta
                delta_df.columns = [lb]
            else:
                delta_df_ = ewma_delta
                delta_df_.columns = [lb]
                delta_df = pd.concat([delta_df, delta_df_], axis=1, sort=True)
        delta_df.index = sq_df_trd_.index
        sq_df_trd_ = pd.concat([sq_df_trd_, delta_df], axis=1, sort=True)
        
        result[stnd_iscd] = sq_df_trd_

        if i == 0:
            comparison = sq_df_trd_.reset_index().iloc[-1]
        else:
            comparison = pd.concat([comparison, sq_df_trd_.reset_index().iloc[-1]], axis=1)
    
    return result, comparison

@st.cache_data(show_spinner=False)
def get_position_data():
    #dbm = dbm_p.DBExecuteManager()
    #istu match dict
    istu_q = "SELECT * FROM positiondb.tb_istu;"
    istu_dict = dict(dbm.get_fetchall(istu_q))
    istu_dict['02'] = '금투/은행'
    
    #tb_brow
    brow_q = "SELECT STND_ISCD, RCD_DATE, BROW_AMT_TDAY FROM positiondb.tb_brow;"
    brow_data = pd.DataFrame([list(x) for x in dbm.get_fetchall(brow_q)], columns=['Code', 'Date', 'Borrow'])

    #otr
    otr_q = "SELECT DATE, MATU_CLAS, STND_ISCD FROM positiondb.tb_ktb_otr ;"
    otr_data = pd.DataFrame([list(x) for x in dbm.get_fetchall(otr_q)], columns=['Date', 'Tenor', 'Code'])

    #supply
    sply_q = "SELECT RCD_DATE, MATU_CLAS, SPLY_DUR FROM positiondb.tb_scnd_dur_sply;"
    sply_data = pd.DataFrame([list(x) for x in dbm.get_fetchall(sply_q)], columns=['Date', 'Tenor', 'Net Supply'])

    #demand
    demand_q = "SELECT RCD_DATE, ISTU, MATU_CLAS, TRD_DUR FROM positiondb.tb_scnd_dur_trd WHERE MATU_CLAS != '3M';"
    demand_data = pd.DataFrame([list(x) for x in dbm.get_fetchall(demand_q)], columns=['Date', 'Institution', 'Tenor', 'Net Demand'])

    #ktbf
    ktbf_q = "SELECT FUT_CODE, TRD_DATE, ISTU_CODE, TRD_VOL FROM positiondb.tb_ktb_fut;"
    ktbf_data = pd.DataFrame([list(x) for x in dbm.get_fetchall(ktbf_q)], columns=['Future', 'Date', 'Institution', 'Trade Volume'])

    #duration
    dur_q = "SELECT STND_ISCD, RCD_DATE, MATU_CLAS, DUR FROM positiondb.tb_dur;"
    dur_data = pd.DataFrame([list(x) for x in dbm.get_fetchall(dur_q)], columns = ['Code', 'Date', 'Maturity Class', 'DUR'])
    
    return istu_dict, brow_data, otr_data, sply_data, demand_data, ktbf_data, dur_data

@st.cache_data(show_spinner=False)
def get_borrowing_data():
    #dbm = dbm_p.DBExecuteManager()
    #istu match dict

    #PRICE
    query_price = "SELECT STND_ISCD, CLPR_FRMT_DATE, CLPR_ERT FROM positiondb.tb_clpr;"
    price = dbm.get_fetchall(query_price)
    price = [[x[0],x[1],float(x[2])] for x in price]
    price_df = pd.DataFrame(price, columns=['CODE', 'DATE','YIELD'])
    price_df['IX'] = price_df['CODE']+"_"+ price_df['DATE']
    
    #TRADE DATA
    query_trd = "SELECT STND_ISCD, TRD_DATE, TRD_AMT, ISTU_CODE, TRD_DRCT FROM positiondb.tb_mkt_trd;"
    trd = dbm.get_fetchall(query_trd)
    trd = [list(x) for x in trd]
    trd_df = pd.DataFrame(trd, columns=['CODE', 'DATE', 'AMT', 'ISTU', 'DIRECTION'])
    trd_df['DIRECTION'] = [1 if d==1 else -1 for d in trd_df['DIRECTION'].values]
    trd_df['AMT'] = trd_df['AMT'] * trd_df['DIRECTION']
    trd_df_g = trd_df.groupby(['CODE', 'DATE', 'ISTU']).sum().reset_index()
    trd_df_g = trd_df_g[['CODE', 'DATE', 'ISTU', 'AMT']]
    trd_df_g['IX'] = trd_df_g['CODE']+"_"+ trd_df_g['DATE']

    m_df = pd.merge(price_df, trd_df_g[['IX', 'ISTU', 'AMT']], how='left', on='IX')
    m_df = m_df.where(pd.notnull(m_df), 0)
    
    #DURATION
    query_dur = "SELECT STND_ISCD, RCD_DATE, REMN_MATU, MATU_CLAS, DUR FROM positiondb.tb_dur;"
    dur = dbm.get_fetchall(query_dur)
    dur = [list(x) for x in dur]
    dur_df = pd.DataFrame(dur, columns = ['CODE', 'DATE', 'REMN_MATU', 'MATU_CLAS', 'DUR'])
    dur_df['IX'] = dur_df['CODE']+"_"+ dur_df['DATE']
    dur_df = dur_df[['IX', 'REMN_MATU', 'MATU_CLAS', 'DUR']]

    m_df = pd.merge(m_df, dur_df, how='left', on='IX')
   
    #NAME
    query_ktb = "SELECT * FROM positiondb.tb_ktb;"
    ktb = dbm.get_fetchall(query_ktb)
    ktb = [list(x) for x in ktb]
    ktb_long_duration = [[k[0], k[1], k[2], k[3]] for k in ktb if '원금' not in k[1] and '이자' not in k[1]]
    ktb_long_duration_df = pd.DataFrame(ktb_long_duration, columns=['CODE', 'NAME', 'PBLC', 'RDMP'])

    m_df = pd.merge(m_df, ktb_long_duration_df, how='left', on='CODE')
    m_df = m_df[~m_df['NAME'].isna()]

    #LISTED
    query_lstd_strip = "SELECT STND_ISCD_KTB, RCD_DATE, PRE_STRP_AMT FROM positiondb.tb_lstd_strp;"
    lstd_strip = dbm.get_fetchall(query_lstd_strip)
    lstd_strip_df = pd.DataFrame(lstd_strip, columns=['CODE', 'DATE', 'PRE_STRP_AMT'])
    lstd_strip_df['IX'] = lstd_strip_df['CODE']+"_"+ lstd_strip_df['DATE']

    query_lstd = "SELECT STND_ISCD, RCD_DATE, LSTD_AMT FROM positiondb.tb_lstd;"
    lstd = dbm.get_fetchall(query_lstd)
    lstd_df = pd.DataFrame(lstd, columns=['CODE', 'DATE', 'PRE_STRP_AMT'])
    lstd_df = lstd_df[~lstd_df['CODE'].isin(list(set(lstd_strip_df['CODE'])))]
    lstd_df['IX'] = lstd_df['CODE']+"_"+ lstd_df['DATE']
    lstd_df = pd.concat([lstd_strip_df, lstd_df], axis=0)

    m_df = pd.merge(m_df, lstd_df[['IX','PRE_STRP_AMT']], how='left', on='IX')

    #BORROWING
    query_brow = "SELECT STND_ISCD, RCD_DATE, BROW_AMT_TDAY, BROW_RATE, LSTD_AMT FROM positiondb.tb_brow;"
    brow = dbm.get_fetchall(query_brow)
    brow_df = pd.DataFrame(brow, columns=['CODE', 'DATE','BROW_AMT','RATE','LSTD'])
    brow_df['IX'] = brow_df['CODE']+"_"+ brow_df['DATE']
    
    m_df = pd.merge(m_df, brow_df[['IX','BROW_AMT','RATE','LSTD']], how='left', on='IX')

    #MARKET YIELD
    query_mkt = "SELECT TCKR, CLPR_DATE, CLPR FROM macrodb.tb_mcro_clpr WHERE tckr='KBGBG03Y Index' OR  tckr='KBGBG10Y Index';"
    mkt = dbm.get_fetchall(query_mkt)
    mkt_df = pd.DataFrame(mkt, columns=['TCKR', 'DATE', 'MKT_YIELD'])
    mkt_df = mkt_df.groupby('DATE').mean().reset_index()
    
    m_df = pd.merge(m_df, mkt_df[['DATE','MKT_YIELD']], how='left', on='DATE')

    return m_df

@st.cache_data(show_spinner=False)
def get_auct_option_data():
    #dbm = dbm_p.DBExecuteManager()
    ktb_q = "SELECT STND_ISCD, KOR_ISNM FROM positiondb.tb_ktb;"
    ktb_name = pd.DataFrame(dbm.get_fetchall(ktb_q), columns=['Code','Name'])
    ktb_name_dict = dict(zip(ktb_name.Code, ktb_name.Name))
    #del ktb_name_dict['KRC0353P2761']
    #del ktb_name_dict['KRC0353P2068']
    #del ktb_name_dict['KRC0355P2736']
    #del ktb_name_dict['KRC035AP29C7']

    auction_comp_q = "SELECT STND_ISCD, AUCT_DATE, PLMT_ERT, AUCT_AMT, BID_AMT, PLMT_AMT FROM positiondb.tb_comp_ofer;"
    auction_comp = pd.DataFrame(dbm.get_fetchall(auction_comp_q), columns=['Code', 'Date', 'Offer_Price','Offer_Amount', 'Bid_Amount', 'Auction_Amount'])
    
    auction_noncomp_q = "SELECT STND_ISCD, AUCT_DATE_STRT, AUCT_DATE_END, PLMT_AMT_OPT, PLMT_AMT_STRP FROM positiondb.tb_noncomp_ofer;"
    auction_noncomp = pd.DataFrame(dbm.get_fetchall(auction_noncomp_q), columns=['Code', 'Date', 'Expire_Date', 'Option_Amount', 'Strip_Option_Amount'])
    
    auction_otr_q = "SELECT STND_ISCD, DATE, MATU_CLAS FROM positiondb.tb_ktb_otr;"
    auction_otr = pd.DataFrame(dbm.get_fetchall(auction_otr_q), columns=['Code', 'Date', 'Maturity_Class'])
    
    duration_q = "SELECT STND_ISCD, RCD_DATE, CLPR, CLPR_ERT, DUR, MATU_CLAS FROM positiondb.tb_dur WHERE DATE_FORMAT(STR_TO_DATE(RCD_DATE, '%Y-%m-%d'),'%Y-%m-%d') >= DATE_FORMAT(STR_TO_DATE('{}', '%Y-%m-%d'),'%Y-%m-%d');".format('2012-01-01')
    duration = pd.DataFrame([[x[0], x[1], x[2], float(x[3]), x[4], x[5]] for x in dbm.get_fetchall(duration_q)], columns=['Code', 'Date', 'Price', 'Yield', 'Duration', 'Maturity_Class'])
    duration['PV01'] = duration['Price']*duration['Duration']/10
    
    return ktb_name_dict, auction_comp, auction_noncomp, auction_otr, duration

def auct_option_data(dp, ktb_name_dict, auction_comp, auction_noncomp, auction_otr, duration, vol_lookback, tenor):
    otr_bp = dp.ktb[['2Y_KTB', '3Y_KTB', '5Y_KTB', '10Y_KTB', '20Y_KTB', '30Y_KTB']]
    otr_bp.columns = ['2Y', '3Y', '5Y', '10Y', '20Y', '30Y']
    otr_bp_diff = otr_bp - otr_bp.shift(1)
    otr_volatility = otr_bp_diff.rolling(vol_lookback).std()*np.sqrt(252)
    
    tenor_otr = auction_otr[auction_otr['Maturity_Class']==tenor]
    tenor_auction_comp = auction_comp[auction_comp['Code'].isin(tenor_otr['Code'])].sort_values(by='Date').set_index('Code').reset_index()
    tenor_auction_data = pd.merge(tenor_auction_comp, auction_noncomp, on=['Code', 'Date'])
    tenor_auction_data = tenor_auction_data.sort_values(by='Date').set_index('Code').reset_index()
    tenor_auction_data = tenor_auction_data.dropna()
    
    tenor_duration = duration[duration['Code'].isin(tenor_otr.Code.values.tolist())]

    last_auction_date = tenor_auction_comp['Date'].values[-1]
    last_option_date = tenor_auction_data['Date'].values[-1]
    if last_auction_date>=last_option_date:
        today = date.today().isoformat()
        a_Date = ql.Date(int(last_auction_date.split('-')[2]) , int(last_auction_date.split('-')[1]),int(last_auction_date.split('-')[0]))
        t_Date = ql.Date(int(today.split('-')[2]) , int(today.split('-')[1]),int(today.split('-')[0]))
        b_days = ql.SouthKorea().businessDaysBetween(a_Date, t_Date)
        if b_days<=3:
            #def ql_to_datetime(d):
            #    return datetime(d.year(), d.month(), d.dayOfMonth())
            #tenor_auction_data = tenor_auction_data.append(dict(zip(tenor_auction_data.columns, tenor_auction_comp.iloc[-1].values.tolist() + [datetime.strftime(ql_to_datetime(ql.SouthKorea().advance(t_Date, ql.Period('3D'))), "%Y-%m-%d"),0,0])), ignore_index=True, sort=False)
            tenor_auction_data = tenor_auction_data.append(dict(zip(tenor_auction_data.columns, tenor_auction_comp.iloc[-1].values.tolist() + [today,0,0])), ignore_index=True, sort=False)
    
    ktb_name = []
    trading_vol = []
    trading_yield = []
    trading_delta = []
    for i, code in enumerate(tenor_auction_data.Code):
        ktb_name.append(ktb_name_dict[code])
        strt_dt = tenor_auction_data.Date[i]
        end_dt = tenor_auction_data.Expire_Date[i]
        trading_data = tenor_duration[(tenor_duration.Code==code)&(tenor_duration.Date>=strt_dt)&(tenor_duration.Date<=end_dt)]
        if strt_dt == date.today().isoformat():
            trading_delta.append([tenor_duration[tenor_duration.Code==code].sort_values(by='Date').set_index('Code').reset_index().PV01.values.tolist()[-1]])
        else:
            trading_delta.append(trading_data.PV01.values.tolist())
        volatility_data = otr_volatility[tenor][(otr_volatility.index>=strt_dt)&(otr_volatility.index<=end_dt)]
        trading_yield.append(trading_data.Yield.values.tolist())
        trading_vol.append(volatility_data.values.tolist())

    tenor_auction_data['Name'] = ktb_name
    
    return tenor_auction_data, trading_yield, trading_delta, trading_vol

@st.cache_data(show_spinner=False)
def sim_dates(data):
    def z_scores(data):
        '''helper function'''
        avg = data.mean()
        std = data.std()
        z = (data - avg) / std
        return z

    def rolling_z_scores(data, window):
        '''helper function'''
        r = data.rolling(window)
        m = r.mean().shift(1)
        s = r.std(ddof=0).shift(1)
        z = (data-m)/s
        return z

    def mahalanobis(x, y):
        '''helper function'''
        #Compute the Mahalanobis Distance between each row of x and the data  
        #x    : ndarray of reference date
        #y    : ndarray of historical date
        dist = np.subtract(x, y)
        cov = np.cov(x.T) 
        if len(np.shape(cov))==0:
            cov = cov.reshape(1,1)
        else:
            pass
        inv_covmat = np.linalg.inv(cov)
        left_term = np.dot(dist, inv_covmat)
        mahal = np.dot(left_term, dist.T)
        return mahal.diagonal()

    def mahalanobis_distance(data):
        '''helper function'''
        #1y z-score
        data_roll = data.copy() #data.copy() #rolling_z_scores(data, 250).dropna()

        #calculate distance
        lookback = [20, 60] #[20, 60, 120, 250]
        mahal_dist_list = {}
        mahal_dist_date = {}
        for lb in lookback:
            #print(lb)
            ref = data_roll[-lb:]
            hist = data_roll[:-lb-60] #trim last 3 months
            for i in range(lb, len(hist), 10):
                #if i % 500 ==0:
                #    print("{}/{}".format(i, len(hist)))
                hist_ = hist[i-lb:i]
                mahal_dist = mahalanobis(ref, hist_)
                hist_dist_ = pd.DataFrame({'Date' : hist_.index, 'Mahalanobis Distance' : mahal_dist})
                hist_dist_ = hist_dist_.set_index('Date')
                if i == lb:
                    hist_dist = hist_dist_.copy()
                else:
                    hist_dist = pd.concat([hist_dist, hist_dist_], axis=1, sort=True)
                
                #calculate z score of distance
                hist_dist['Mahal Dist Avg'] = hist_dist.mean(axis=1)
                z = z_scores(hist_dist['Mahal Dist Avg']).dropna()
                mahal_dist_list[lb] = z
                mahal_dist_date[lb] = z.index[z<-1]

        return mahal_dist_date

    def historical_date_filter(data):
        '''helper function'''
        pd.set_option('mode.chained_assignment',  None)
        historical_date = list(data.index)
        m_date = mahalanobis_distance(data)
        historical_date_df = pd.DataFrame(historical_date, columns=['Date'])
        
        lookback = [20, 60] # [20, 60, 120, 250]
        for lb in lookback:
            historical_date_df[lb] = 0
            m_date_ = m_date[lb]
            for d in list(m_date_):
                #print(lb, d)
                ix = historical_date.index(d)
                historical_date_df.loc[ix-10:ix+10+1, lb] = 1
        pd.set_option('mode.chained_assignment',  'warn')
        return historical_date_df
    
    sim_dt = historical_date_filter(data)
    sim_dt['Regime'] = 1.5*(sim_dt[20]+sim_dt[60]>0)
    
    return sim_dt[['Date', 'Regime']].set_index('Date')

@st.cache_data(show_spinner=False)
def get_ktb_name():
    #dbm = dbm_p.DBExecuteManager()
    name_q = "SELECT KOR_ISNM, STND_ISCD FROM positiondb.tb_ktb WHERE KOR_ISNM LIKE '%국고%' OR KOR_ISNM LIKE '%물가%';"
    ktb_name = dbm.get_fetchall(name_q)
    ktb_name = [x for x in ktb_name if x[1] not in ktb_remove_list] #없는 종목 보정
    return ktb_name

@st.cache_data(show_spinner=False)
def get_bok_policy_rate():
    #dbm = dbm_p.DBExecuteManager()
    bok_q = "SELECT CLPR_DATE, CLPR FROM macrodb.tb_mcro_clpr WHERE TCKR = 'KORP7DR Index';"
    bok = pd.DataFrame(dbm.get_fetchall(bok_q), columns=['Date', 'BOK']).set_index('Date')
    return bok

@st.cache_data(show_spinner=False)
def get_ktbf_price():
    #dbm = dbm_p.DBExecuteManager()
    ktbf_price_q = "SELECT TCKR, CLPR_DATE, CLPR FROM macrodb.tb_mcro_clpr WHERE (TCKR='KE1 Comdty' OR TCKR='KAA1 Comdty') AND FLDS='PX_LAST';"
    ktbf_price = pd.DataFrame([list(x) for x in dbm.get_fetchall(ktbf_price_q)], columns=['Ticker', 'Date', 'Price'])
    return ktbf_price            

def style_negative(v, props=''):
    try:
        x = props if v < 0 else None
    except:
        x = None
    return x

def mean_highlighter(x):
    style_lt = "background-color: maroon; color:white;"
    style_gt = "background-color: midnightblue; color:white;"
    gt_mean = x > 0
    return [style_gt if i else style_lt for i in gt_mean]

#데이터 불러오기
with st.spinner("Querying Data, Will take about 2 minutes, Please Wait..."):
    dp = pull_strategy_data()
    auction_data = get_auction_data()
    clpr = pull_price_data()
    bok = pull_bok_price_data()
    kauc = KTBAuction(dp)

    #전략리스트
    ktb = ['1Y_KTB', '2Y_KTB','3Y_KTB','4Y_KTB','5Y_KTB','7Y_KTB','10Y_KTB','20Y_KTB','30Y_KTB', 'IL10Y_KTB', 'BE10Y_KTB', '3Y_FUT', '10Y_FUT']
    swap = ['9M_IRS', '1Y_IRS', '18M_IRS','2Y_IRS','3Y_IRS','4Y_IRS','5Y_IRS','7Y_IRS','10Y_IRS']
    foreign = ['2Y_FUT_US', '5Y_FUT_US', '10Y_FUT_US', '30Y_FUT_US','2Y_FUT_GER', '5Y_FUT_GER', '10Y_FUT_GER'] 
    outright_list = ktb+swap+foreign
    #가격데이터
    strategy, strategy_tr, strategy_outright, strategy_outright_tr = pull_strategy_data_series(dp)
    
    for c in [t for t in strategy_outright.columns.tolist() if 'KTB' in t]:
        strategy[c] = strategy_outright[c]
    
    ktbf_price = get_ktbf_price()
    #수급데이터
    istu_dict, brow_data, otr_data, sply_data, demand_data, ktbf_data, dur_data = get_position_data()
    #매매데이터
    trade_borrow_data = get_borrowing_data()
    #옵션관련 데이터
    ktb_dur_list = list(set(dur_data.Code))
    ktb_remove_list = ['KRC0353P2068','KRC0353P2761','KRC0355P2736','KRC0355P2736','KRC035AP29C7', 'KRC0353P27C4']
    ktb_remove_list = [ktb for ktb in ktb_remove_list if ktb not in ktb_dur_list]
    ktb_name_dict, auction_comp, auction_noncomp, auction_otr, duration = get_auct_option_data()
    ktb_name = get_ktb_name() #없는 종목 보정
    #Auction 차트
    bok = get_bok_policy_rate()
    features = dp.strategy_feature[['FRA Deviation', 'Local Liquidity Risk']]
    features = features.fillna(method='ffill')
    features.index.name = 'Date'
    strategy_yield = strategy_outright[['3Y_KTB', '10Y_KTB']]
    strategy_yield['YC3Y10Y'] = strategy_outright['10Y_KTB'] - strategy_outright['3Y_KTB']
    strategy_yield.index.name = 'Date'
    features = pd.concat([features, strategy_yield], axis=1, sort=True).fillna(method='ffill')
    regime = sim_dates(features[['FRA Deviation', 'Local Liquidity Risk', 'YC3Y10Y']].dropna())
    features = pd.concat([features, regime], axis=1, sort=True).fillna(method='ffill')
    features = pd.merge(features, bok, how='left', left_index=True, right_index=True).fillna(method='ffill')
    features = features.reset_index()

with st.container():
    tab1, tab2, tab3, tab4, tab5 = st.tabs(['Auction', 'Option', 'Delta Demand', 'Cum. Trade', 'Real Money'])

    with open(css_dir) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

    with tab1:
        with st.container():
            fig_f = make_subplots(specs=[[{"secondary_y":True}]])
            fig_f.add_trace(go.Bar(x=features['Date'], y=features['Regime'], name='Regime', hovertemplate='<br>Date: %{x:|%B %d, %Y}<br> Regime : %{y:.3f}'), secondary_y=False)            
            fig_f.add_trace(go.Scatter(x=features['Date'], y=features['BOK'], name='BOK(L)', mode='lines', hovertemplate='<br>Date: %{x:|%B %d, %Y}<br>'+ '3Y_KTB' + ': %{y:.3f}'), secondary_y=True)
            #fig_f.add_trace(go.Scatter(x=features['Date'], y=features['3Y_KTB'], name='3Y_KTB(L)', mode='lines', hovertemplate='<br>Date: %{x:|%B %d, %Y}<br>'+ '10Y_KTB' + ': %{y:.3f}'), secondary_y=True)
            fig_f.add_trace(go.Scatter(x=features['Date'], y=features['10Y_KTB'], name='10Y_KTB(L)', mode='lines', hovertemplate='<br>Date: %{x:|%B %d, %Y}<br>'+ '10Y_KTB' + ': %{y:.3f}'), secondary_y=True)
            fig_f.add_trace(go.Scatter(x=features['Date'], y=features['Local Liquidity Risk'], name='Local Liquidity Risk(L)', mode='lines',hovertemplate='<br>Date: %{x:|%B %d, %Y}<br>'+'Local Liquidity Risk'+ ': %{y:.3f}'), secondary_y=True)
            fig_f.add_trace(go.Scatter(x=features['Date'], y=features['YC3Y10Y'], name='YC3Y10Y(R)', mode='lines',  hovertemplate='<br>Date: %{x:|%B %d, %Y}<br>'+ 'YC3Y10Y' + ': %{y:.3f}'), secondary_y=False)
            fig_f.add_trace(go.Scatter(x=features['Date'], y=features['FRA Deviation'], name='FRA Deviation(R)', mode='lines',hovertemplate='<br>Date: %{x:|%B %d, %Y}<br>'+'FRA Deivation'+ ': %{y:.3f}'), secondary_y=False)
            
            fig_f.update_xaxes(dtick="M3", tickformat="%Y.%m",
                        rangeselector = dict(
                        buttons=list([
                        dict(count=1, label="1m", step="month", stepmode="backward"),
                        dict(count=6, label="6m", step="month", stepmode="backward"),
                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                        dict(count=1, label="1y", step="year", stepmode="backward"),
                        dict(step="all")])))
            #fig_f.update_yaxes(title_text='Yield', secondary_y=False)
            #fig_f.update_yaxes(title_text='KTB Regime', secondary_y=True)
            #st.markdown('**KTB Regime**')
            st.plotly_chart(fig_f, use_container_width=True)
        
        with st.container():
            col1_a, col2_a = st.columns(2)
            with col1_a:
                manual = st.selectbox('Manual Date Input', ['Auto', 'Manual'])
            with col2_a:
                if manual == 'Manual':
                    text_input = st.text_input("Enter dates", placeholder='2016-10-26~2016-11-12, 2019-04-05~2020-03-24, 2022-06-29~2024-04-24')
                    if len(text_input):
                        text_input_ = [t.replace(' ', '') for t in text_input.split(',')]
                        start_date_string_list = [t.split('~')[0] for t in text_input_]
                        end_date_string_list = [t.split('~')[1] for t in text_input_]
                    else:
                        start_date_string_list = []
                        end_date_string_list = []

        st.divider()
        maturity_list = ['2Y', '3Y', '5Y','10Y', '20Y', '30Y', '50Y']
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                col1_, col2_ = st.columns(2)
                with col1_:
                    st.markdown("")
                    st.markdown("")
                    start_button = st.button('Calculate Score')
                
                with col2_:
                    tenor = st.selectbox('Choose a Tenor', maturity_list)
                    auction_data_t = auction_data[auction_data['Maturity']==tenor]
            
            with col2:
                col1_, col2_ = st.columns(2)
                with col1_:
                    horizon_before = int(st.number_input('Before Auction', min_value=0, max_value=20))
                with col2_:
                    horizon_after = int(st.number_input('After Auction', min_value=0, max_value=20))
                
            with col3:
                col1_, col2_ = st.columns(2)
                with col1_:
                    if manual == 'Auto':
                        start_dt = datetime.strftime(st.date_input('Auction Start', date(2018,1,1)), '%Y-%m-%d')
                with col2_:
                    if manual == 'Auto':
                        end_dt = datetime.strftime(st.date_input('Auction End'), '%Y-%m-%d')

        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                col1_1, col1_2 = st.columns(2)
                with col1_1:
                    us_rate_change = st.number_input('US Rate Change in bp', -10, 10, value=0)
                with col1_2:
                    noncomp = st.selectbox('Noncomp Offer', [False, True])

            with col2:
                eliminate_tenor = st.multiselect('Eliminate Tenor', ['1Y', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y', '20Y', '30Y'], default =[], max_selections=6)
            
            with col3:
                dday_month = st.multiselect('Select Auction Month', [1,2,3,4,5,6,7,8,9,10,11,12], default =[1,2,3,4,5,6,7,8,9,10,11,12], max_selections=12)
               
        with st.container():
            col1, col2 = st.columns(2)
            #st.write(auction_data_t)
            with col1:
                if manual == 'Auto':
                    auction_data_t_s = auction_data_t[(auction_data_t['Auction Date']>=start_dt)&(auction_data_t['Auction Date']<=end_dt)].set_index('Auction Date')
                elif manual == 'Manual' and len(start_date_string_list)>0:
                    #st.write(end_date_string_list)
                    for i, dt in enumerate(zip(start_date_string_list, end_date_string_list)):
                        start_dt, end_dt = dt[0], dt[1]
                        if i ==0:
                            auction_data_t_s = auction_data_t[(auction_data_t['Auction Date']>=start_dt)&(auction_data_t['Auction Date']<=end_dt)].set_index('Auction Date')
                        else:
                            auction_data_t_s_ = auction_data_t[(auction_data_t['Auction Date']>=start_dt)&(auction_data_t['Auction Date']<=end_dt)].set_index('Auction Date')
                            auction_data_t_s = pd.concat([auction_data_t_s, auction_data_t_s_], axis=0)
                else:
                    auction_data_t_s = auction_data_t[(auction_data_t['Auction Date']>='2018-01-01')&(auction_data_t['Auction Date']<=date.today().isoformat())].set_index('Auction Date')
                auction_data_t_s = get_auction_sort(auction_data_t_s, clpr, us_rate_change, noncomp, dday_month)
                strategy_date_list = sorted(list(set(auction_data_t_s.index.values)))
                st.dataframe(auction_data_t_s, use_container_width=True)
                
            with col2:
                if start_button:
                    sorted_strategy = {}
                    for k,v in zip(strategy.keys(), strategy.values()):
                        inclusiion_bool = True
                        if type(k)==str:
                            if k.split('_')[0] not in eliminate_tenor:
                                sorted_strategy[k] = v
                        else:
                            for t in k:
                                if t.split('_')[0] in eliminate_tenor:
                                    inclusiion_bool = False
                            if inclusiion_bool:
                                sorted_strategy[k] = v
                    strategy_score_win_df, strategy_event = get_strategy_score(sorted_strategy, strategy_date_list, horizon_before, horizon_after)
                    strategy_event_date_pair, strategy_clpr_date_pair = get_strategy_event_date_pair(strategy_event, strategy_date_list) 
                    
                    st.session_state.st_score = strategy_score_win_df
                    st.session_state.st_event = strategy_event
                    st.session_state.st_event_date = strategy_event_date_pair
                    st.session_state.st_clpr_date = strategy_clpr_date_pair
                if 'st_score' in st.session_state:
                    st.dataframe(st.session_state.st_score, use_container_width=True)
                
        with st.container():  
            col1, col2 = st.columns(2)
            with col1: 
                strat_select = st.multiselect('Strategy', ['1Y_KTB', '2Y_KTB','3Y_KTB','4Y_KTB','5Y_KTB','7Y_KTB','10Y_KTB','20Y_KTB','30Y_KTB'], default=None, max_selections=3)
                event_date_rate_bok = get_strategy_event_date_vs_bok(strat_select, strategy_date_list, strategy_outright, bok)

            if len(strat_select)>0:
                try:
                    strat_key = get_strategy_name(strat_select)[0]
                    strategy_past = pd.DataFrame(st.session_state.st_event[strat_key])
                    strategy_past = strategy_past.sub(strategy_past[horizon_before], axis='index').T
                    strategy_past.columns = strategy_date_list
                    strategy_past.index.name = 'horizon'
                    strategy_past = strategy_past.reset_index()
                    strategy_past['horizon'] = strategy_past['horizon']-horizon_before
                    
                    fig = px.line(strategy_past, x='horizon', y=strategy_past.columns,title="{} Movement Around {} Auction".format(str(strat_key), tenor), height=500)    
                    fig.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                        rangeselector = dict(
                                        buttons=list([
                                        dict(count=1, label="1m", step="month", stepmode="backward"),
                                        dict(count=6, label="6m", step="month", stepmode="backward"),
                                        dict(count=1, label="YTD", step="year", stepmode="todate"),
                                        dict(count=1, label="1y", step="year", stepmode="backward"),
                                        dict(step="all")])))
                    st.plotly_chart(fig, use_container_width=True)
                except:
                    st.write('Choose more than one tenor!')

            if len(strat_select)>0:
                if 'st_event_date' in st.session_state:
                    st.markdown('**Event Score**')
                    st.dataframe(st.session_state.st_event_date[st.session_state.st_event_date.index==str(get_strategy_name(strat_select)[0])], use_container_width=True)

                if 'st_clpr_date' in st.session_state:
                    st.markdown('**Event Level**')
                    st.dataframe(st.session_state.st_clpr_date[st.session_state.st_clpr_date.index==str(get_strategy_name(strat_select)[0])], use_container_width=True)

                st.markdown('**Level vs BOK**')
                st.dataframe(event_date_rate_bok,  use_container_width=True)

            else:
                if 'st_event_date' in st.session_state:
                    st.markdown('**Event Score**')
                    st.dataframe(st.session_state.st_event_date, height=500, use_container_width=True)
                
                if 'st_clpr_date' in st.session_state:
                    st.markdown('**Event Level**')
                    st.dataframe(st.session_state.st_clpr_date, height=500, use_container_width=True)
            

        st.download_button(label="Download auction data as CSV", data=convert_df(auction_data_t),file_name='Auction_{}.csv'.format(date.today().isoformat()), mime='text/csv')
        if 'st_score' in st.session_state:
            st.download_button(label="Download score data as CSV", data=convert_df(st.session_state.st_score),file_name='Auction_Score_{}.csv'.format(date.today().isoformat()), mime='text/csv')
        if 'st_event_date' in st.session_state:
            st.download_button(label="Download event score data as CSV", data=convert_df(st.session_state.st_event_date),file_name='Auction_Event_Score_{}.csv'.format(date.today().isoformat()), mime='text/csv')
            st.download_button(label="Download event level data as CSV", data=convert_df(st.session_state.st_clpr_date),file_name='Auction_Event_Level_{}.csv'.format(date.today().isoformat()), mime='text/csv')
            st.download_button(label="Download event bok data as CSV", data=convert_df(event_date_rate_bok),file_name='Auction_Event_BOK_{}.csv'.format(date.today().isoformat()), mime='text/csv')
    
    with tab2:
        with st.container():
            col1_o, col2_o = st.columns(2)
            with col1_o:
                col1_1, col1_2, col1_3, col1_4 = st.columns(4)
                with col1_1:
                    option_tenor = st.selectbox('Choose a Tenor  ', maturity_list)
                with col1_2:
                    option_vol_lookback = int(st.number_input('Volatility Lookback', value=20, min_value=0, max_value=500))
                with col1_3:
                    display_columns = st.selectbox('Choose Information', ['All', 'd1', 'Delta', 'Option Value'])
                with col1_4:
                    display_cases = st.number_input('Choose Recet # Events', value=50, min_value=1)
            
            with col2_o:
                current_yield_ = st.text_input("Current Yield", "0")
                current_yield = float(current_yield_)
        
        st.divider()        
        tenor_auction_data, trading_yield, trading_delta, trading_vol = auct_option_data(dp, ktb_name_dict, auction_comp, auction_noncomp, auction_otr, duration, option_vol_lookback, option_tenor)
        tenor_auction_data_option = kauc.auction_option_value(tenor_auction_data, trading_yield, trading_delta, trading_vol, option_tenor, option_vol_lookback, current_yield)
        display_data = tenor_auction_data_option.iloc[-display_cases:, :]
        
        if display_columns == 'All':
            display_data_final = display_data[['Date','Code','Name', 'Auction_Amount','Expire_Date','Option_Amount', 'T0', 'T1', 'T2', 'T3', 'T0_dur', 'T1_dur', 'T2_dur', 'T3_dur', 'T0_vol', 'T1_vol', 'T2_vol', 'T3_vol', 'd1_T0', 'd2_T0', 'N_d1_T0', 'N_d2_T0', 'Option_Value_T0', 'd1_T1', 'd2_T1', 'N_d1_T1', 'N_d2_T1', 'Option_Value_T1', 'd1_T2', 'd2_T2', 'N_d1_T2', 'N_d2_T2', 'Option_Value_T2', 'd1_T3', 'd2_T3', 'N_d1_T3', 'N_d2_T3', 'Option_Value_T3']]
        elif display_columns == 'd1':
            display_data_final = display_data[['Date','Code','Name', 'Auction_Amount','Expire_Date','Option_Amount', 'd1_T0', 'd1_T1','d1_T2', 'd1_T3']]
        elif display_columns == 'Delta':
            display_data_final = display_data[['Date','Code','Name', 'Auction_Amount','Expire_Date','Option_Amount', 'N_d1_T0', 'N_d1_T1','N_d1_T2', 'N_d1_T3']]
        elif display_columns == 'Option Value':
            display_data_final = display_data[['Date','Code','Name', 'Auction_Amount','Expire_Date','Option_Amount', 'Option_Value_T0', 'Option_Value_T1','Option_Value_T2', 'Option_Value_T3']]
        else:
            display_data_final = None
        
        if display_data_final is not None:
            st.dataframe(display_data_final.set_index('Date'), height=528, use_container_width=True)
       
    with tab3:
        istu_dict_inv = dict(zip(istu_dict.values(), istu_dict.keys()))
        
        with st.container():
            col1_p, col2_p = st.columns(2)
            with col1_p:
                start_dt = datetime.strftime(st.date_input('Start Date', date(2025,1,2)), '%Y-%m-%d')
            with col2_p:
                end_dt = datetime.strftime(st.date_input('End Date'), '%Y-%m-%d')

        with st.container():
            tenor_order = {'3M':0, '6M':1, '9M':2, '1Y':3, '18M':4, '2Y':5, '3Y':6, '4Y':7, '5Y':8, '7Y':9, '10Y':10, '15Y':11, '20Y':12, '30Y':13, '50Y':14}
            istu_order = ['01','02','03','04','05','06','07','08','09','10','11']
            fut_istu_order = {'01':0,'02':1,'03':2,'04':3,'05':4,'06':5,'07':6,'08':7,'09':8,'10':9,'11':10,'13':11,'00':12}

            #듀레이션 공급
            sply_data_dt = sply_data[(sply_data['Date']>=start_dt)&(sply_data['Date']<=end_dt)]
            sply_data_process =  sply_data_dt.groupby('Tenor').sum().astype(int).reset_index()

            sply_data_list = []
            for t in tenor_order:
                if t != '3M':
                    if t in sply_data_process['Tenor'].values:
                        sply_data_list.append(sply_data_process[sply_data_process['Tenor']==t].values.tolist()[0])
                    else:
                        sply_data_list.append([t, 0])

            sply_data_process = pd.DataFrame(sply_data_list, columns=['Tenor', 'Supply']).sort_values(by='Tenor', key=lambda x:x.map(tenor_order))
            sply_data_process['Supply'] = sply_data_process['Supply']*-1

            #듀레이션 수요
            demand_data_dt = demand_data[(demand_data['Date']>=start_dt)&(demand_data['Date']<=end_dt)]
            demand_data_process = demand_data_dt.groupby(['Tenor', 'Institution']).sum().astype(int).reset_index()
                
            for i, ist in enumerate(istu_order):
                if i == 0:
                    demand_data_istu = demand_data_process[demand_data_process['Institution']==ist][['Tenor', 'Net Demand']].set_index('Tenor').sort_index(key=lambda x:x.map(tenor_order))
                    demand_data_istu.columns = [istu_dict[ist]]
                else:
                    demand_data_istu_ = demand_data_process[demand_data_process['Institution']==ist][['Tenor', 'Net Demand']].set_index('Tenor').sort_index(key=lambda x:x.map(tenor_order))
                    demand_data_istu_.columns = [istu_dict[ist]]
                    demand_data_istu = pd.concat([demand_data_istu, demand_data_istu_], axis=1)
            
            demand_data_istu = demand_data_istu.where(pd.notnull(demand_data_istu), 0)
            demand_data_istu = demand_data_istu[[x for x in list(demand_data_istu.columns) if x!='은행']].reset_index()

            #선물
            ktbf_data_dt = ktbf_data[(ktbf_data['Date']>=start_dt)&(ktbf_data['Date']<=end_dt)]
            ktbf_data_process = ktbf_data_dt.groupby(['Future', 'Institution']).sum().reset_index()
            ktbf_data_process.loc[((ktbf_data_process['Institution']=='00')&(ktbf_data_process['Future']=='KTB')), ['Trade Volume']] = ktbf_data[(ktbf_data['Institution']=='00')&(ktbf_data['Future']=='KTB')]['Trade Volume'].values[-1]
            ktbf_data_process.loc[((ktbf_data_process['Institution']=='00')&(ktbf_data_process['Future']=='LKTB')), ['Trade Volume']]= ktbf_data[(ktbf_data['Institution']=='00')&(ktbf_data['Future']=='LKTB')]['Trade Volume'].values[-1]

            ktbf_price = ktbf_price[ktbf_price['Date']<=end_dt]

            ktbf_3y_price = ktbf_price[ktbf_price['Ticker']=='KE1 Comdty']['Price'].values[-1]
            ktbf_10y_price = ktbf_price[ktbf_price['Ticker']=='KAA1 Comdty']['Price'].values[-1]

            ktbf_data_list = []
            ktb_istu_match_dict = {'00':'미결제약정', '01':'외국인', '02':'금융투자', '03':'보험', '04':'자산운용', '05':'은행','07':'기타금융', '08':'기금/공제', '10':'기타법인', '11':'개인', '13':'기관합계'}
            for ktbf in ktbf_data_process.values:
                ktbf = list(ktbf)
                ktbf[1] = ktb_istu_match_dict[ktbf[1]]
                if 'KTB' in ktbf:
                    ktbf.append(np.round(ktbf[2]*2.9*ktbf_3y_price/10*-1))
                else:
                    ktbf.append(np.round(ktbf[2]*8.9*ktbf_10y_price/10*-1))
                ktbf_data_list.append(ktbf)
            
            #대차증감
            brow_date = list(set(brow_data['Date']))
            if end_dt in brow_date:
                brow_end_dt = end_dt
            else:
                brow_date.append(end_dt)
                brow_date = sorted(brow_date)
                brow_end_dt = brow_date[brow_date.index(end_dt)-1]

            brow_date = list(set(brow_data['Date']))
            if brow_end_dt == start_dt:
                brow_date = sorted(brow_date)
                brow_start_dt = brow_date[brow_date.index(brow_end_dt)-1]
            else:
                if start_dt in brow_date:
                    brow_start_dt = start_dt
                else:
                    brow_date.append(start_dt)
                    brow_date = sorted(brow_date)
                    brow_start_dt = brow_date[brow_date.index(start_dt)-1]

            #지표물 선택
            #시작일 당시 지표물을 확인해야함
            otr_data_list = []
            for odt in list(set(otr_data['Date'])):
                for t in list(tenor_order.keys())[1:]:
                    otr_data_ = otr_data[(otr_data['Date']<=odt)&(otr_data['Tenor']==t)]['Code'].values
                    if len(otr_data_)>0:
                        otr_data_list.append([odt, t, otr_data_[-1]])

            otr_date = list(set(otr_data['Date']))
            otr_date.append(start_dt)
            otr_date = sorted(otr_date)
            start_dt_ = otr_date[otr_date.index(start_dt)-1]
                
            otr_data_cont = pd.DataFrame(otr_data_list, columns=['Date', 'Tenor', 'Code'])
            otr_data_dt = otr_data_cont[(otr_data_cont['Date']>=start_dt_)&(otr_data_cont['Date']<=end_dt)]
            otr_tenor_match_dict = dict(zip(otr_data_dt['Code'].values,otr_data_dt['Tenor'].values))

            #대차 데이터 process : 기간 내 모든 지표물 기준 종료일 - 시작일
            brow_data_cd = brow_data[brow_data['Code'].isin(list(otr_data_dt['Code'].values))]
            brow_data_cd_at_start = brow_data_cd[brow_data_cd['Date']==brow_start_dt]
            brow_data_cd_at_end = brow_data_cd[brow_data_cd['Date']==brow_end_dt]

            clpr_dur_q = "SELECT RCD_DATE, STND_ISCD, CLPR, DUR FROM positiondb.tb_dur WHERE DATE_FORMAT(STR_TO_DATE(RCD_DATE, '%Y-%m-%d'),'%Y-%m-%d') = DATE_FORMAT(STR_TO_DATE('{}', '%Y-%m-%d'),'%Y-%m-%d');".format(brow_start_dt)
            clpr_dur_data_start = pd.DataFrame([list(x) for x in dbm.get_fetchall(clpr_dur_q)], columns=['Date', 'Code', 'Price', 'Duration'])
            clpr_dur_q = "SELECT RCD_DATE, STND_ISCD, CLPR, DUR FROM positiondb.tb_dur WHERE DATE_FORMAT(STR_TO_DATE(RCD_DATE, '%Y-%m-%d'),'%Y-%m-%d') = DATE_FORMAT(STR_TO_DATE('{}', '%Y-%m-%d'),'%Y-%m-%d');".format(brow_end_dt)
            clpr_dur_data_end = pd.DataFrame([list(x) for x in dbm.get_fetchall(clpr_dur_q)], columns=['Date', 'Code', 'Price', 'Duration'])
            
            dur_at_start = clpr_dur_data_start[clpr_dur_data_start['Code'].isin(brow_data_cd_at_start['Code'].values)]
            dur_at_end = clpr_dur_data_end[clpr_dur_data_end['Code'].isin(brow_data_cd_at_end['Code'].values)]

            brow_data_cd_at_start['Duration_Start'] = np.round(brow_data_cd_at_start['Borrow'].values*dur_at_start['Price'].values*dur_at_start['Duration'].values/1000,2)
            brow_data_cd_at_end['Borrowing'] = np.round(brow_data_cd_at_end['Borrow'].values*dur_at_end['Price'].values*dur_at_end['Duration'].values/1000,2)
            
            brow_data_process = pd.concat([brow_data_cd_at_end.set_index('Code'), brow_data_cd_at_start.set_index('Code')], axis=1)
            brow_data_process = brow_data_process.where(pd.notnull(brow_data_process), 0)
            brow_data_process['Borrowing Change'] = brow_data_process['Borrowing'] - brow_data_process['Duration_Start'] 
            brow_data_process = brow_data_process.reset_index()[['Code', 'Borrowing', 'Borrowing Change']]
            brow_data_process['Tenor'] = [otr_tenor_match_dict[x] for x in brow_data_process['Code'].values]
            brow_data_process = brow_data_process[brow_data_process['Tenor'].isin(tenor_order.keys())]
            brow_data_process = np.round(brow_data_process.groupby('Tenor').sum().sort_index(key=lambda x:x.map(tenor_order)).reset_index())

            brow_data_list = []
            for t in tenor_order:
                if t != '3M':
                    if t in brow_data_process['Tenor'].values:
                        brow_data_list.append(brow_data_process[brow_data_process['Tenor']==t].values.tolist()[0])
                    else:
                        brow_data_list.append([t, 0,0])
            brow_data_df = pd.DataFrame(brow_data_list, columns=['Tenor', 'Borrowing', 'Borrowing Change'])

        with st.container():
            col1_d, col2_d = st.columns(2)

            with col1_d:
                st.markdown('Delta Demand')
                st.dataframe(demand_data_istu.set_index('Tenor').style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), height=525, use_container_width=True)
                
            with col2_d:
                col2_d_1, col2_d_2 = st.columns(2)
                with col2_d_1:
                    st.markdown('Delta Supply')
                    st.dataframe(sply_data_process.set_index('Tenor').style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), height=525, use_container_width=True)
                with col2_d_2:
                    st.markdown('Delta Borrowing')
                    st.dataframe(brow_data_df.set_index('Tenor').style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), height=525, use_container_width=True)

        with st.container():
            st.markdown('Futures Traded')
            col1_f, col2_f = st.columns(2)
            
            fut_istu_order = ['외국인', '금융투자', '보험', '자산운용','은행','기타금융', '기금/공제','기타법인','개인', '기관합계','미결제약정']
            fut_vol = pd.DataFrame(ktbf_data_list, columns=['Future', 'Institution', 'Volume', 'Delta']).pivot_table(index=['Future'], columns=['Institution'], values = ['Volume'])
            fut_vol.columns = fut_vol.columns.droplevel()
            fut_vol.columns.name = None
            fut_vol.index.name = 'Volume'
            fut_vol = fut_vol[fut_istu_order]
            fut_del = pd.DataFrame(ktbf_data_list, columns=['Future', 'Institution', 'Volume', 'Delta']).pivot_table(index=['Future'], columns=['Institution'], values = ['Delta'])
            fut_del.columns = fut_del.columns.droplevel()
            fut_del.columns.name = None
            fut_del.index.name = 'Delta'
            fut_del = fut_del[fut_istu_order]

            #for_fut = pd.DataFrame([x for x in ktbf_data_list if '외국인' in x], columns=['Future', 'Institution', 'Volume', 'Delta'])
            #dom_fut = pd.DataFrame([x for x in ktbf_data_list if '기관계' in x], columns=['Future', 'Institution', 'Volume', 'Delta'])
                
            with col1_f:
                st.dataframe(fut_del.style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), use_container_width=True)
            with col2_f:
                st.dataframe(fut_vol.style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), use_container_width=True)

        st.divider()
        with st.container():
            col1_sd, col2_sd, col3_sd, col4_sd = st.columns(4)
            with col1_sd:
                start_dt_sd = datetime.strftime(st.date_input('Start Date ', date(2020,1,1)), '%Y-%m-%d')
            with col2_sd:
                end_dt_sd = datetime.strftime(st.date_input('End Date '), '%Y-%m-%d')
            with col3_sd:
                tenor = st.selectbox('Choose a Tenor ', maturity_list)
                auction_data_t = auction_data[auction_data['Maturity']==tenor]
            with col4_sd:
                institution = st.selectbox('Choose Institution', list(istu_dict.values()))
        
        with st.container():
            auction_dates = sorted(list(set(auction_data_t['Auction Date'].values)))
            demand_data_t = demand_data[(demand_data['Tenor']==tenor)&(demand_data['Institution']==istu_dict_inv[institution])] 
            demand_data_t = demand_data_t[['Date', 'Net Demand']]
            sply_data_t = sply_data[sply_data['Tenor']==tenor]
            sply_data_t = sply_data_t[['Date', 'Net Supply']]

            demand_supply = pd.concat([demand_data_t.set_index('Date'), sply_data_t.set_index('Date')], axis=1, sort=True)
            demand_supply['Auction Date'] = [1 if d in auction_dates else 0 for d in demand_supply.index]
            demand_supply = demand_supply.where(pd.notnull(demand_supply), 0)
            
            cumulative = []
            cum_demand = 0
            cum_supply = 0
            cum_date = 0
            trigger = 0
            for dt, d, s, a in zip(demand_supply['Net Demand'].index, demand_supply['Net Demand'].values, demand_supply['Net Supply'].values, demand_supply['Auction Date'].values):
                if trigger==0 and a == 1:
                    trigger=1
                    auction_d = dt
                    cum_demand += d
                    cum_supply += s
                    cum_date += 1
                    cumulative.append([auction_d , cum_demand, cum_supply, cum_date])
                elif trigger==1 and a == 1:
                    auction_d = dt
                    cum_demand = 0
                    cum_supply = 0
                    cum_date = 0
                    cum_demand += d
                    cum_supply += s
                    cum_date += 1
                    cumulative.append([auction_d , cum_demand, cum_supply, cum_date])
                elif trigger==1 and a == 0:
                    cum_demand += d
                    cum_supply += s
                    cum_date += 1
                    cumulative.append([auction_d , cum_demand, cum_supply, cum_date])
                else:
                    continue
            
            demand_supply_cum = pd.DataFrame(cumulative, columns=['Date', 'Demand', 'Supply', 'Auction Date'])
            demand_supply_cum['Demand/Supply'] = demand_supply_cum['Demand']/demand_supply_cum['Supply']
            #st.write(demand_supply_cum)
            #st.download_button(label="Download ratio data as CSV", data=convert_df(demand_supply),file_name='Supply_Demand_{}_{}_{}.csv'.format(tenor, start_dt_sd, end_dt_sd), mime='text/csv')
            #st.download_button(label="Download ratio data as CSV", data=convert_df(demand_supply_cum),file_name='Supply_Demand_Ratop_{}_{}_{}.csv'.format(tenor, start_dt_sd, end_dt_sd), mime='text/csv')

            demand_supply_cum_p = demand_supply_cum.pivot_table(values='Demand/Supply', index='Auction Date', columns='Date')
            demand_supply_cum_p_columns = [c for c in demand_supply_cum_p.columns if c <= end_dt_sd and c>= start_dt_sd]
            demand_supply_cum_p = demand_supply_cum_p[demand_supply_cum_p_columns]
            demand_supply_cum_p['Average'] = demand_supply_cum_p.mean(axis=1)
            demand_supply_cum_p['Standard Dev.'] = demand_supply_cum_p.std(axis=1)
            demand_supply_cum_p = demand_supply_cum_p[['Average', 'Standard Dev.']+sorted(demand_supply_cum_p_columns, reverse=True)]
            demand_supply_cum_p = demand_supply_cum_p[demand_supply_cum_p.index<=25]
            st.dataframe(demand_supply_cum_p.style.background_gradient(cmap='RdBu', axis=1)) #.style.apply(mean_highlighter).format(precision=4, decimal="."))
            
            demand_supply_cum_p_chart = demand_supply_cum_p.reset_index()
            fig = px.line(demand_supply_cum_p_chart, x='Auction Date', y=demand_supply_cum_p_chart.columns,title='Demand/Supply')    
            
            st.plotly_chart(fig, use_container_width=True)
            
        st.download_button(label="Download demand data as CSV", data=convert_df(pd.concat([demand_data_istu.set_index('Tenor'), sply_data_process.set_index('Tenor'), brow_data_df.set_index('Tenor')], axis=1)),file_name='Supply_Demand_{}_{}.csv'.format(start_dt, end_dt), mime='text/csv')
        st.download_button(label="Download future delta data as CSV", data=convert_df(fut_del),file_name='FutureDelta_{}_{}.csv'.format(start_dt, end_dt), mime='text/csv')
        st.download_button(label="Download ratio data as CSV", data=convert_df(demand_supply_cum_p),file_name='Supply_Demand_Ratop_{}_{}.csv'.format(start_dt_sd, end_dt_sd), mime='text/csv')

    with tab4:   
        #name_q = "SELECT KOR_ISNM, STND_ISCD FROM positiondb.tb_ktb WHERE KOR_ISNM LIKE '%국고%' OR KOR_ISNM LIKE '%물가%';"
        #ktb_name = dbm.get_fetchall(name_q)
        #ktb_name = [x for x in ktb_name if x[1]!='KRC0353P2068' and x[1]!='KRC0353P2761'] #없는 종목 보정
        
        istu_q = "SELECT ISTU_CODE, ISTU_NAME FROM positiondb.tb_istu;"
        istu = dbm.get_fetchall(istu_q)
        istu_df = pd.DataFrame(istu, columns=['Code', 'Name'])
        istu_dict = dict(istu)

        trade_data_q = "SELECT STND_ISCD, TRD_DATE, TRD_AMT, ISTU_CODE, TRD_OTC, TRD_DRCT FROM positiondb.tb_mkt_trd"
            
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            trade_start_dt = datetime.strftime(st.date_input('Trade Start Date'), "%Y-%m-%d")
        with col2:
            trade_end_dt = datetime.strftime(st.date_input('Trade End Date'), "%Y-%m-%d")
        with col3:
            trade_direction = st.selectbox("Trade Direction", ('Net', 'Buy', 'Sell'))
            trade_direction_dict = {'Buy':1, 'Sell':2, 'Net':3}
            trade_direction = trade_direction_dict[trade_direction]
            trade_direction_sign_dict = {1:1, 2:-1}
        with col4:
            trade_otc = st.selectbox("Trade OTC", ('All', 'OTC', 'KRX'))
            trade_otc_dict = {'OTC':1, 'KRX':2, 'All':3}
            trade_otc = trade_otc_dict[trade_otc]
        
        with st.container():
            col1_, col2_ = st.columns(2)
            current_duration = dur_data[dur_data['Date']<=trade_end_dt].groupby('Code').last().reset_index()
            current_duration = current_duration[current_duration['Code'].isin([x[1] for x in ktb_name])]
            current_duration_dict = dict(zip(current_duration['Code'], current_duration['Maturity Class']))
            
            with col1_:
                #col1_1, col2_1 = st.columns(2)
                #with col1_1:
                #    exclude_trade = st.number_input("Exclude Trades",20)
                #with col2_1:
                    maturity_class = st.selectbox("Maturity Class",['3M', '6M', '9M', '1Y', '18M', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y', '15Y', '20Y', '30Y', '50Y'])

            with col2_:
                ktb_name_ = [x for x in ktb_name if x[1] in list(current_duration_dict.keys())]
                ktb_name_maturity = [x for x in ktb_name_ if current_duration_dict[x[1]]==maturity_class]
                ktb_name_dict = dict(ktb_name_maturity)
                ktb_code_dict = dict([[x[1], x[0]] for x in ktb_name_maturity])
                ktb_selected = st.multiselect('Select KTB', [n[0] for n in ktb_name_maturity], default=None, max_selections=10)
                ktb_selected_code = [ktb_name_dict[c] for c in ktb_selected]

        with st.container(): 
            annex = ""
            if len(ktb_selected_code)>0:
                for i, code in enumerate(ktb_selected_code):
                    if i == 0:
                        annex += " WHERE STND_ISCD = '{}'".format(code)
                    elif i == len(ktb_selected_code)-1:
                        annex += " OR STND_ISCD = '{}';".format(code)
                    else:
                        annex += " OR STND_ISCD = '{}'".format(code)

                trade_data = dbm.get_fetchall(trade_data_q+annex)
                trade_data_df = pd.DataFrame([[ktb_code_dict[x[0]],x[1],x[2]*trade_direction_sign_dict[x[5]],istu_dict[x[3]],x[4],x[5]] for x in trade_data], columns=['종목', 'Date', 'Amount', 'Institution', 'OTC', 'Direction'])
                trade_data_df = trade_data_df[(trade_data_df['Date']>=trade_start_dt) & (trade_data_df['Date']<=trade_end_dt)]

                lstd_q = "SELECT STND_ISCD, RCD_DATE, LSTD_AMT FROM positiondb.tb_lstd"
                lstd_data = dbm.get_fetchall(lstd_q+annex)
                lstd_data_df = pd.DataFrame(lstd_data, columns=['Code', 'Date', 'Listed'])
                lstd_data_df = lstd_data_df[lstd_data_df['Date']<=trade_end_dt]
                lstd_data_last = lstd_data_df.groupby('Code').last()
                lstd_data_list = lstd_data_last.reset_index().values.tolist()
                lstd_data_list = [[ktb_code_dict[x[0]], x[2]] for x in lstd_data_list]
                lstd_data_list_df = pd.DataFrame(lstd_data_list, columns=['종목', '상장액']).set_index('종목')

                if trade_otc != 3:
                    trade_data_df = trade_data_df[trade_data_df['OTC']==trade_otc][['종목', 'Amount', 'Institution', 'Direction']]
                else:
                    trade_data_df = trade_data_df[['종목', 'Amount', 'Institution', 'Direction']]
                
                if trade_direction != 3:
                    trade_data_df = trade_data_df[trade_data_df['Direction']==trade_direction][['종목', 'Amount', 'Institution']].groupby(['종목', 'Institution']).sum()
                else:
                    trade_data_df = trade_data_df[['종목', 'Amount', 'Institution']].groupby(['종목', 'Institution']).sum()

                trade_data_result = trade_data_df.pivot_table(values='Amount', index='종목', columns='Institution').reset_index().set_index('종목')
                trade_data_result = pd.concat([lstd_data_list_df, trade_data_result], axis=1)
                column = list(trade_data_result.columns)
                c_order = {'상장액':0, '종목':1, '외국인':2, '금융투자':3, '보험':4, '자산운용':5, '은행':6, '종합금융':7, '기타금융':8, '기금/공제':9, '국가지자체 등':10, '기타법인':11, '개인':12}
                column.sort(key= lambda x:c_order[x])
                trade_data_result = trade_data_result[column]
                addition = pd.DataFrame(trade_data_result.sum(axis=0)).T
                addition['종목'] = '합계'
                trade_data_result = trade_data_result.reset_index().append(addition, ignore_index=True).set_index('종목')

                st.dataframe(trade_data_result.style.format(precision=0, thousands=",", decimal="."), use_container_width=True)           

    with tab5:
        with st.container():
            col1_b, col2_b, col3_b = st.columns(3)

            with col1_b:
                end_date = datetime.strftime(st.date_input('Search Date'), "%Y-%m-%d")
                with st.spinner("Querying Data, Will take about 20 seconds, Please Wait..."):
                    historical, comparison = real_money_trade(trade_borrow_data, end_date)

            with col2_b:
                maturity_class_ = st.selectbox("Maturity Class ",['3M', '6M', '9M', '1Y', '18M', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y', '15Y', '20Y', '30Y', '50Y'])
                #name_q = "SELECT KOR_ISNM, STND_ISCD FROM positiondb.tb_ktb WHERE (KOR_ISNM LIKE '%국고%' OR KOR_ISNM LIKE '%물가%') AND DATE_FORMAT(STR_TO_DATE(RDMP_DATE, '%Y-%m-%d'),'%Y-%m-%d') >= DATE_FORMAT(STR_TO_DATE('{}', '%Y-%m-%d'),'%Y-%m-%d');".format(end_date)
                #ktb_name = dbm.get_fetchall(name_q)
                #ktb_name = [x for x in ktb_name if x[1]!='KRC0353P2068' and x[1]!='KRC0353P2761'] #없는 종목 보정
                current_duration = dur_data[dur_data['Date']<=end_date].groupby('Code').last().reset_index()
                current_duration = current_duration[current_duration['Code'].isin([x[1] for x in ktb_name])]
                current_duration_dict = dict(zip(current_duration['Code'], current_duration['Maturity Class']))
                
            with col3_b:
                ktb_name_maturity = [x for x in ktb_name if current_duration_dict[x[1]]==maturity_class_]
                ktb_name_dict = dict(ktb_name_maturity)
                ktb_code_dict = dict([[x[1], x[0]] for x in ktb_name_maturity])
                code = st.multiselect('Select KTB', [n[0] for n in ktb_name_maturity], default=None, max_selections=1)
                
        with st.container():
            comparison_d = comparison.T
            comparison_d =  comparison_d[comparison_d['Maturity Date']>=end_date]
            comparison_d = comparison_d.sort_values(by='Maturity Date', ascending=False)
            comparison_d = comparison_d[['Code','Date', 'Name','Maturity Class','Pre Strip Listed','Borrow','Real Money Cum','Trading Cum','Real Money Ratio','Trading Ratio','Borrow Ratio',20,60,120,250]]
            st.write("**Real Money Demand and Borrowing**")
            st.dataframe(comparison_d.set_index('Code'), use_container_width=True, height=600) 

        with st.container():
            if len(code)>0:
                ktb_code = ktb_name_dict[code[0]] 
                historical_c = historical[ktb_code]
                #Price
                price_df = historical_c[['Yield', 'Market Yield', 'Spread']].reset_index()

                fig_p = go.Figure()
                fig_p.add_trace(go.Scatter(x=price_df['Date'], y=price_df['Yield'], name='Yield', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                fig_p.add_trace(go.Scatter(x=price_df['Date'], y=price_df['Market Yield'], name='Market Yield', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                fig_p.add_trace(go.Scatter(x=price_df['Date'], y=price_df['Spread'], name='Spread', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                fig_p.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                    yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                    yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))

                
                st.write("**Historical Yield**")
                st.plotly_chart(fig_p, use_container_width=True)

                #Real Money
                realmoney = historical_c[['Real Money Cum', 'Real Money Ratio', 'Borrow Ratio']].reset_index()
                fig_r = go.Figure()
                fig_r.add_trace(go.Scatter(x=realmoney['Date'], y=realmoney['Real Money Cum'], name='Real Money Cum', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}'))
                fig_r.add_trace(go.Scatter(x=realmoney['Date'], y=realmoney['Real Money Ratio'], name='Real Money Ratio', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y2"))
                fig_r.add_trace(go.Scatter(x=realmoney['Date'], y=realmoney['Borrow Ratio'], name='Borrow Ratio', mode='lines', hovertemplate='<br> %{x:|%B %d, %Y} : %{y:.3f}', yaxis="y3"))
                fig_r.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                    yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                    yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))

                st.write("**Real Money Demand**")
                st.plotly_chart(fig_r, use_container_width=True)


                #Real Money Trend
                realmoney_trend = historical_c[[20,60,120,250]].reset_index()
                fig_trend = px.line(realmoney_trend, x='Date', y=realmoney_trend.columns,hover_data={'Date': "|%B %d, %Y"})    
                fig_trend.update_xaxes(dtick="M3", tickformat="%Y.%m",
                                    rangeselector = dict(
                                    buttons=list([
                                    dict(count=1, label="1m", step="month", stepmode="backward"),
                                    dict(count=6, label="6m", step="month", stepmode="backward"),
                                    dict(count=1, label="YTD", step="year", stepmode="todate"),
                                    dict(count=1, label="1y", step="year", stepmode="backward"),
                                    dict(step="all")])))
                
                st.write("**Demand Trend Score**")
                st.plotly_chart(fig_trend, use_container_width=True)

        st.download_button(label="Download data as CSV",data= convert_df(comparison_d),file_name='RealMoneyDemand_{}.csv'.format(date.today().isoformat()), mime='text/csv')
                   
            
                
                




        
