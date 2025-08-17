file_dir = 'C:\\Users\\kimju\\MPT-Quant\\MacroTrading'
css_dir = 'C:\\Users\\kimju\\MPT-Quant\\SystemMacro_App\\pages\\style.css'

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from datetime import date
import time
from time import mktime
import pandas as pd
import numpy as np
import QuantLib as ql
from scipy.stats import norm
import sys
sys.path.append(file_dir)
from Feature_Preprocessing import RatesDataProcess
from MPTSRT_IntraDB import db_execute_manager as dbm_i
dbm = dbm_i.DBExecuteManager()

if 'note' not in st.session_state:
    st.session_state.note = ''

st.session_state.note = st.sidebar.text_area('Note', st.session_state.note, height=300)

@st.cache_resource
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

@st.cache_resource(show_spinner=False)
def pull_strategy_data():
    dp = RatesDataProcess('2012-10-01', date.today().isoformat())
    return dp

@st.cache_data(show_spinner=False)
def get_krx_ktb_data():
    query = "SELECT STND_ISCD, TIME_STMP, DATE, HOUR, YLD, PRCE, VOL FROM intradb.tb_krx_ktb;"
    data = pd.DataFrame([list(x) for x in dbm.get_fetchall(query)], columns=['STND_ISCD', 'Timestamp', 'Date', 'Hour', 'Yield', 'Price', 'Volume'])
    return data

@st.cache_data(show_spinner=False)
def pull_price_data():
    query = "SELECT CLPR_FRMT_DATE, STND_ISCD, CLPR_ERT, CLPR FROM positiondb.tb_clpr;"
    price = pd.DataFrame([[x[0], x[1], float(x[2]), float(x[3])] for x in dbm.get_fetchall(query)], columns=['Date', 'STND_ISCD', 'Yield', 'Price']).set_index('Date')
    return price

@st.cache_data(show_spinner=False)
def get_auction_data():
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
        clpr_ = clpr[clpr['STND_ISCD']==stnd_iscd]['Yield'].shift(1)
        return clpr_[clpr_.index<=date][-1]
    
    auction_data_df_['Previous Date Price'] = auction_data_df_[['Code','Date']].apply(lambda x:get_previous_rate(x.Code, x.Date), axis=1).fillna(auction_data_df_['Offer Price'])
    auction_data_df_['vs Previous Date'] = (auction_data_df_['Offer Price'].astype(float) - auction_data_df_['Previous Date Price'].astype(float))*100
    auction_data_df_ = auction_data_df_[list(original_columns)+['US Rate']+['vs Previous Date']]
    
    return auction_data_df_.sort_index()

def get_otr_data():
    ktb_q = "SELECT STND_ISCD, KOR_ISNM FROM positiondb.tb_ktb;"
    ktb_name = pd.DataFrame(dbm.get_fetchall(ktb_q), columns=['Code','Name'])
    ktb_name_dict = dict(zip(ktb_name.Code, ktb_name.Name))

    otr_q = "SELECT STND_ISCD, DATE, MATU_CLAS FROM positiondb.tb_ktb_otr;"
    otr = pd.DataFrame(dbm.get_fetchall(otr_q), columns=['Code', 'Date', 'Maturity_Class'])
    return ktb_name_dict, otr


with st.spinner("Querying Data, Will take about 1 minute, Please Wait..."):
    dp = pull_strategy_data()
    krx_intraday_data = get_krx_ktb_data()
    ktb_name_dict, otr = get_otr_data()
    auction_data = get_auction_data()
    clpr = pull_price_data()

with st.container():
    tab1, tab2 = st.tabs(['KRX KTB', 'KRX KTB Auction'])

    with open(css_dir) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

    with tab1:
        with st.container():
            col1, col2 = st.columns(2)

            with col1:
                col1_1, col1_2, col1_3 = st.columns(3)
                with col1_1:
                    start_dt_ = st.date_input('Start Date', date(2024,1,3), min_value=date(2020,12,1))
                    start_dt = datetime.strftime(start_dt_, '%Y-%m-%d')
                    ktb_otr_df = otr[otr['Date']<=start_dt].groupby('Maturity_Class').last().reset_index()
                    matu_class_list = ['2Y', '3Y', '5Y', '10Y', '20Y', '30Y']
                    ktb_otr_df = ktb_otr_df[ktb_otr_df.Maturity_Class.isin(matu_class_list)].sort_values(by='Maturity_Class', key=lambda x: x.map({'2Y':0, '3Y':1, '5Y':2, '10Y':3, '20Y':4, '30Y':5}))
                    ktb_otr_df['Name'] = [ktb_name_dict[x] for x in  ktb_otr_df.Code]
                    ktb_list = [m+": "+ ktb_name_dict[c] + ", "+c for m, c in zip(ktb_otr_df.Maturity_Class, ktb_otr_df.Code)]
                with col1_2:
                    end_dt = datetime.strftime(st.date_input('End Date', start_dt_), '%Y-%m-%d')
                with col1_3:
                    notation = st.selectbox('Notation', ['Yield', 'Price'])
            with col2:
                ktb_selected_ = st.multiselect('Choose KTB', ktb_list)
                ktb_selected = [k.split(", ")[1] for k in ktb_selected_]
            
            krx_intraday_data_selected = krx_intraday_data[krx_intraday_data.STND_ISCD.isin(ktb_selected)]
            krx_intraday_data_selected = krx_intraday_data_selected[(krx_intraday_data.Date>=start_dt)&(krx_intraday_data.Date<=end_dt)].set_index('STND_ISCD').reset_index()
            krx_intraday_data_selected['Name'] = [ktb_name_dict[x] for x in krx_intraday_data_selected.STND_ISCD]
            krx_intraday_data_selected['Datetime'] = [datetime.strftime(datetime.fromtimestamp(t), "%Y-%m-%d %H:%M:%S") for t in krx_intraday_data_selected.Timestamp]
            
            if notation=='Price':
                krx_intraday_data_selected_chart = krx_intraday_data_selected[['Datetime', 'Name', 'Price']]
                krx_intraday_data_selected_chart = krx_intraday_data_selected_chart.pivot(index='Datetime', columns='Name', values='Price')
            else:
                krx_intraday_data_selected_chart = krx_intraday_data_selected[['Datetime', 'Name', 'Yield']]
                krx_intraday_data_selected_chart = krx_intraday_data_selected_chart.pivot(index='Datetime', columns='Name', values='Yield')

            selected_list = list(krx_intraday_data_selected_chart.columns)
            krx_intraday_data_selected_chart = krx_intraday_data_selected_chart.fillna(method='ffill').reset_index()
            #st.write(krx_intraday_data_selected_chart)
            #st.write(krx_intraday_data_selected_chart)
            #st.line_chart(krx_intraday_data_selected_chart)

            if len(selected_list) > 0:
                #if len(selected_list) == 1:
                #    fig = px.line(krx_intraday_data_selected_chart , x='Datetime', y=krx_intraday_data_selected_chart.columns,hover_data={'Datetime': "|%H:%M:%S, %B %d, %Y"})    
                #    fig.update_xaxes(dtick=600000, tickformat="%Y-%m-%d %H:%M")
                #    st.plotly_chart(fig, use_container_width=True)
                
                if len(selected_list) == 1:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][0]], name=[str(c) for c in selected_list][0], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}'))
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]))
                    
                elif len(selected_list) == 2:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][0]], name=[str(c) for c in selected_list][0], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][1]], name=[str(c) for c in selected_list][1], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"))
                
                elif len(selected_list) == 3:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][0]], name=[str(c) for c in selected_list][0], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][1]], name=[str(c) for c in selected_list][1], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][2]], name=[str(c) for c in selected_list][2], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.95]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(selected_list) == 4:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][0]], name=[str(c) for c in selected_list][0], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][1]], name=[str(c) for c in selected_list][1], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][2]], name=[str(c) for c in selected_list][2], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][3]], name=[str(c) for c in selected_list][3], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.92]),
                                        yaxis2=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis3=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(selected_list) == 5:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][0]], name=[str(c) for c in selected_list][0], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][1]], name=[str(c) for c in selected_list][1], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][2]], name=[str(c) for c in selected_list][2], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][3]], name=[str(c) for c in selected_list][3], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][4]], name=[str(c) for c in selected_list][4], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.92]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.015),
                                        yaxis3=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.955),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.99))
                
                elif len(selected_list) == 6:
                    fig_ = go.Figure()
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][0]], name=[str(c) for c in selected_list][0], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}'))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][1]], name=[str(c) for c in selected_list][1], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y2"))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][2]], name=[str(c) for c in selected_list][2], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y3"))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][3]], name=[str(c) for c in selected_list][3], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y4"))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][4]], name=[str(c) for c in selected_list][4], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y5"))
                    fig_.add_trace(go.Scatter(x=krx_intraday_data_selected_chart['Datetime'], y=krx_intraday_data_selected_chart[[str(c) for c in selected_list][5]], name=[str(c) for c in selected_list][5], mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}', yaxis="y6"))
                    
                    fig_.update_layout(xaxis=dict(domain=[0.05, 0.90]),
                                        yaxis2=dict(anchor="free",overlaying="y",side="left", position=0.015),
                                        yaxis3=dict(anchor="x",overlaying="y",side="right"),
                                        yaxis4=dict(anchor="free",overlaying="y",side="right", position=0.93),
                                        yaxis5=dict(anchor="free",overlaying="y",side="right", position=0.955), 
                                        yaxis6=dict(anchor="free",overlaying="y",side="right", position=0.98))
                
                fig_.update_xaxes(rangebreaks=[dict(bounds=[15.5001, 9.0001], pattern="hour"), dict(bounds=['sat', 'mon'])])
                fig_.update_xaxes(dtick=600000, tickformat="%Y-%m-%d %H:%M") #600000
                st.plotly_chart(fig_, use_container_width=True)

                st.download_button(label="Download data as CSV", data= convert_df(krx_intraday_data_selected_chart.set_index('Datetime')),file_name='KRX_KTB_{}.csv'.format(start_dt), mime='text/csv')

    with tab2:
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                col1_1, col2_1 = st.columns(2)
                with col1_1:
                    maturity_list = ['2Y', '3Y', '5Y','10Y', '20Y', '30Y', '50Y']
                    auction_tenor = st.selectbox('Auction Tenor', maturity_list)
                    auction_data_t = auction_data[auction_data['Maturity']==auction_tenor]
                with col2_1:
                    tenor = st.selectbox('Intraday Tenor', maturity_list)
                    
            with col2:
                col1_, col2_ = st.columns(2)
                with col1_:
                    start_dt = datetime.strftime(st.date_input('Auction Start', date(2021,8,1)), '%Y-%m-%d')
                with col2_:
                    end_dt = datetime.strftime(st.date_input('Auction End'), '%Y-%m-%d')
            with col3:
                st.markdown("")
                st.markdown("")
                start_button = st.button('Show Chart')

        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                col1_1, col1_2 = st.columns(2)
                with col1_1:
                    notation = st.selectbox('Notation ', ['Yield', 'Price'])
                with col1_2:
                    manual = st.selectbox('Manual Date Input', ['Auto', 'Manual'])

            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_1:
                    us_rate_change = st.number_input('US Rate Change in bp', -10, 10, value=0)
                with col2_2:
                    noncomp = st.selectbox('Noncomp Offer', [False, True])
            
            with col3:
                dday_month = st.multiselect('Select Auction Month', [1,2,3,4,5,6,7,8,9,10,11,12], default =[1,2,3,4,5,6,7,8,9,10,11,12], max_selections=12)
               
        auction_data_t = auction_data_t[(auction_data_t['Auction Date']>=start_dt)&(auction_data_t['Auction Date']<=end_dt)].set_index('Auction Date')
        auction_data_t = get_auction_sort(auction_data_t, clpr, us_rate_change, noncomp, dday_month)
        strategy_date_list = sorted(list(set(auction_data_t.index.values)))
        auction_data_t['Deactivate'] = True

        with st.container():
            if manual == 'Manual':
                text_input = st.text_input("Enter dates", placeholder='2023-06-05, 2023-09-04')
                date_string_list = [t.replace(' ', '') for t in text_input.split(',')]
        
        st.divider()
        st.markdown("**Auction Data**")
        st.data_editor(auction_data_t, column_config={"Deactivate":st.column_config.CheckboxColumn("Deactivate", default=True)}, use_container_width=True)
        #st.dataframe(auction_data_t, use_container_width=True)
        if manual == "Auto":
            date_string_list =sorted(list(set(auction_data_t[auction_data_t['Deactivate']==True].index.tolist())))
        
        st.divider()
        
        with st.container():
            if len([x for x in date_string_list if x!=""])>0 and start_button:
                ktb_selected_cross = []
                column_list = []
                prev_date_price = []
                prev_date_yield = []
                for i, dt in enumerate(date_string_list):
                    ktb_otr_df_cross = otr[otr['Date']<=dt].groupby('Maturity_Class').last().reset_index()
                    stnd_iscd = ktb_otr_df_cross[ktb_otr_df_cross.Maturity_Class==tenor].Code.values[0]
                    column_list.append("{}_{}".format(stnd_iscd, dt))
                    prev_date_yield.append(clpr[(clpr.index<=dt)&(clpr.STND_ISCD==stnd_iscd)]['Yield'].values[-2])
                    prev_date_price.append(clpr[(clpr.index<=dt)&(clpr.STND_ISCD==stnd_iscd)]['Price'].values[-2])
                    krx_intraday_data_selected_cross = krx_intraday_data[(krx_intraday_data.STND_ISCD==stnd_iscd)&(krx_intraday_data.Date==dt)]
                    #print(krx_intraday_data_selected_cross)
                    if i == 0:
                        krx_intraday_data_selected_cross_yield = krx_intraday_data_selected_cross[['Hour', 'Yield']].set_index('Hour')
                        krx_intraday_data_selected_cross_price = krx_intraday_data_selected_cross[['Hour', 'Price']].set_index('Hour')
                    else:
                        krx_intraday_data_selected_cross_yield = pd.concat([krx_intraday_data_selected_cross_yield, krx_intraday_data_selected_cross[['Hour', 'Yield']].set_index('Hour')], axis=1, sort=True)
                        krx_intraday_data_selected_cross_price = pd.concat([krx_intraday_data_selected_cross_price, krx_intraday_data_selected_cross[['Hour', 'Price']].set_index('Hour')], axis=1, sort=True)
                #st.write(krx_intraday_data_selected_cross)
                krx_intraday_data_selected_cross_yield.columns = column_list
                krx_intraday_data_selected_cross_yield = krx_intraday_data_selected_cross_yield.dropna(axis=1, how='all')
                krx_intraday_data_selected_cross_yield = krx_intraday_data_selected_cross_yield.fillna(method='bfill').dropna()
                #st.write(krx_intraday_data_selected_cross_yield)
                krx_intraday_data_selected_cross_yield = krx_intraday_data_selected_cross_yield.reset_index().sort_values(by='Hour')
                column_list_ = krx_intraday_data_selected_cross_yield.columns.tolist()
                krx_intraday_data_selected_cross_yield = krx_intraday_data_selected_cross_yield.append(dict(zip(['Hour']+column_list, ['09:00:00']+prev_date_yield)), ignore_index=True).sort_values(by='Hour').set_index('Hour').reset_index()
                krx_intraday_data_selected_cross_yield['Average'] = np.round(krx_intraday_data_selected_cross_yield[column_list_].mean(axis=1),3)
                krx_intraday_data_selected_cross_yield = krx_intraday_data_selected_cross_yield.set_index('Hour') - krx_intraday_data_selected_cross_yield.set_index('Hour').iloc[0,:]
                krx_intraday_data_selected_cross_price.columns = column_list
                krx_intraday_data_selected_cross_price = krx_intraday_data_selected_cross_price.dropna(axis=1, how='all')
                krx_intraday_data_selected_cross_price  = krx_intraday_data_selected_cross_price.fillna(method='bfill').dropna()
                krx_intraday_data_selected_cross_price = krx_intraday_data_selected_cross_price.reset_index().sort_values(by='Hour')
                column_list_ = krx_intraday_data_selected_cross_price.columns.tolist()
                krx_intraday_data_selected_cross_price = krx_intraday_data_selected_cross_price.append(dict(zip(['Hour']+column_list, ['09:00:00']+prev_date_price)), ignore_index=True).sort_values(by='Hour').set_index('Hour').reset_index()
                krx_intraday_data_selected_cross_price = krx_intraday_data_selected_cross_price.append(dict(zip(['Hour']+column_list, ['09:00:00']+prev_date_price)), ignore_index=True).sort_values(by='Hour').set_index('Hour').reset_index()
                krx_intraday_data_selected_cross_price['Average'] = np.round(krx_intraday_data_selected_cross_price[column_list_].mean(axis=1),3)
                krx_intraday_data_selected_cross_price = krx_intraday_data_selected_cross_price.set_index('Hour') - krx_intraday_data_selected_cross_price.set_index('Hour').iloc[0,:]

                if notation=='Price':
                    krx_intraday_data_selected_cross = krx_intraday_data_selected_cross_price.reset_index()[['Hour', 'Average']].set_index('Hour').sort_index().reset_index()
                    krx_intraday_data_selected_cross['Hour'] = ["0"+h if len(h)==7 else h for h in krx_intraday_data_selected_cross.Hour]
                    krx_intraday_data_selected_chart_cross = krx_intraday_data_selected_cross[['Hour', 'Average']]
                    #krx_intraday_data_selected_chart = krx_intraday_data_selected_chart.pivot(index='Datetime', columns='Name', values='Price')
                else:
                    krx_intraday_data_selected_cross = krx_intraday_data_selected_cross_yield.reset_index()[['Hour', 'Average']].set_index('Hour').sort_index().reset_index()
                    krx_intraday_data_selected_cross['Hour'] = ["0"+h if len(h)==7 else h for h in krx_intraday_data_selected_cross.Hour]
                    krx_intraday_data_selected_chart_cross = krx_intraday_data_selected_cross[['Hour', 'Average']]
                    #krx_intraday_data_selected_chart = krx_intraday_data_selected_chart.pivot(index='Datetime', columns='Name', values='Yield')

                #st.write(krx_intraday_data_selected_cross_price.sort_index())
                selected_list_cross = list(krx_intraday_data_selected_chart_cross.columns)
                #krx_intraday_data_selected_chart = krx_intraday_data_selected_chart.reset_index()
                #st.write(krx_intraday_data_selected_chart)
                #st.line_chart(krx_intraday_data_selected_chart)
                krx_intraday_data_selected_chart_cross['Date'] = end_dt
                krx_intraday_data_selected_chart_cross['Timestamp'] = [int(datetime.fromtimestamp(mktime(time.strptime(d+" "+h, "%Y-%m-%d %H:%M:%S"))).timestamp()) for d,h in zip(krx_intraday_data_selected_chart_cross['Date'].values.tolist(), krx_intraday_data_selected_chart_cross['Hour'].values.tolist())]
                krx_intraday_data_selected_chart_cross['Datetime'] = [datetime.strftime(datetime.fromtimestamp(t), "%Y-%m-%d %H:%M:%S") for t in krx_intraday_data_selected_chart_cross.Timestamp]
                krx_intraday_data_selected_chart_cross = krx_intraday_data_selected_chart_cross.sort_values(by='Timestamp')
                krx_intraday_data_selected_chart_cross = krx_intraday_data_selected_chart_cross[['Datetime', 'Average']]
                #krx_intraday_data_selected_chart_cross = krx_intraday_data_selected_chart_cross.sort_values(by='Datetime')

                #st.write(krx_intraday_data_selected_chart_cross)
                if len(selected_list_cross) > 1:
                    #fig = px.line(krx_intraday_data_selected_chart_cross , x='Hour', y=krx_intraday_data_selected_chart_cross.columns,hover_data={'Hour': "|%H:%M:%S"})    
                    #fig.update_xaxes(dtick=600000, tickformat="%H:%M:%S")
                    #st.plotly_chart(fig, use_container_width=True)
                    st.markdown("**Intraday Movement**")
                    #st.write(date_string_list)
                    #st.write(krx_intraday_data_selected_chart_cross)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=krx_intraday_data_selected_chart_cross['Datetime'], y=krx_intraday_data_selected_chart_cross['Average'], name='Average PnL', mode='lines', hovertemplate='<br> %{x:|%H:%M:%S, %B %d, %Y} : %{y:.3f}'))
                    fig.update_xaxes(rangebreaks=[dict(bounds=[15.50001, 9.0001], pattern="hour")])
                    fig.update_xaxes(dtick=600000, tickformat="%Y-%m-%d %H:%M")
                    st.plotly_chart(fig, use_container_width=True)
                    #st.write(krx_intraday_data_selected_chart_cross)
                
                    if notation == "Price":
                        st.download_button(label="Download daily data as CSV", data= convert_df(krx_intraday_data_selected_cross_price),file_name='KRX_KTB_Cross_Daily_Price_{}.csv'.format(date.today().isoformat()), mime='text/csv')
                    else:
                        st.download_button(label="Download daily data as CSV", data= convert_df(krx_intraday_data_selected_cross_yield),file_name='KRX_KTB_Cross_Daily_Yield_{}.csv'.format(date.today().isoformat()), mime='text/csv')
                
                st.download_button(label="Download auction data as CSV", data= convert_df(auction_data_t),file_name='Auction_Data_{}.csv'.format(date.today().isoformat()), mime='text/csv')
                    

                    
