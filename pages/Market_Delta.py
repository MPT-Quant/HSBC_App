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
import os
from joblib import dump, load
import logging
from pathlib import Path
sys.path.append(file_dir)

if 'note' not in st.session_state:
    st.session_state.note = ''

st.session_state.note = st.sidebar.text_area('Note', st.session_state.note, height=300)


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

@st.cache_resource
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('EUC-KR')


def get_files_by_extension(folder_path, extension):
    # Convert string path to Path object
    path = Path(folder_path)
    # Get all files with specific extension
    files = list(path.glob(f"*.{extension}"))
    return files

def save_joblib(file_name, data):
    data_folder = file_dir+"\\HSBCMonitor"
    os.makedirs(data_folder, exist_ok=True)
    try:
        file_path = os.path.join(data_folder, file_name)
        dump(data, file_path, compress=3)  # Compression level 3 (balances speed & size)
        logging.info(f"Saved {file_name} using joblib")
    except Exception as e:
        logging.error(f"Failed to save {file_name}: {e}")

def load_joblib(file_name):
    data_folder = file_dir+"\\HSBCMonitor"
    os.makedirs(data_folder, exist_ok=True)
    file_path = os.path.join(data_folder, file_name)
    try:
        if os.path.exists(file_path):
            return load(file_path)
        else:
            logging.warning(f"{file_name} not found. Returning None.")
            return None
    except Exception as e:
        logging.error(f"Error loading {file_name}: {e}")
        return None
    
@st.cache_data(show_spinner=False)
def get_delta_data_date_list():
    data_folder = file_dir+"\\HSBCMonitor"
    files = get_files_by_extension(data_folder, 'joblib')
    delta_data_files = [file for file in files if 'deltadata_' in file.name]
    date_list = [file.name.split('_')[-1].split('.')[0] for file in delta_data_files]
    return date_list

@st.cache_data(show_spinner=False)
def get_trade_data_date_list():
    data_folder = file_dir+"\\HSBCMonitor"
    files = get_files_by_extension(data_folder, 'joblib')
    trade_data_files = [file for file in files if 'tradedata_' in file.name]
    date_list = [file.name.split('_')[-1].split('.')[0] for file in trade_data_files]
    return date_list

@st.cache_data(show_spinner=False)
def load_auction_data():
    auction_stat_data = load_joblib('auction_stat_data.joblib')
    auction_otrofr_spread_data = load_joblib('auction_otrofr_spread_data.joblib')
    auction_borrowing_data = load_joblib('auction_borrowing_data.joblib')
    auction_butterfly_data = load_joblib('auction_butterfly_data.joblib')
    auction_option_data = load_joblib('auction_option_data.joblib')
    return auction_stat_data, auction_otrofr_spread_data, auction_borrowing_data, auction_butterfly_data, auction_option_data

@st.cache_data(show_spinner=False)
def load_ktb_info():
    ktb_info = pd.read_excel(file_dir + "\\HSBCMonitor\\KTBInfo.xlsx", sheet_name='ktbinfo')
    ktb_otr = pd.read_excel(file_dir + "\\HSBCMonitor\\KTBInfo.xlsx", sheet_name='otr')
    return ktb_info, ktb_otr

def load_delta_data(end_dt):
    delta_data = load_joblib(f"deltadata_{end_dt}.joblib")
    return delta_data

def load_trade_data(end_dt):
    trade_data_0 = load_joblib(f"tradedata_123_{end_dt}.joblib")
    trade_data_1 = load_joblib(f"tradedata_4567891011_{end_dt}.joblib")
    trade_data = {**trade_data_0, **trade_data_1}
    return trade_data


###
def load_volume_profilate_data():
    volume_profile_data = load_joblib("volume_profile_data.joblib")
    return volume_profile_data

with st.spinner("Querying Data, Will take about 2 minutes, Please Wait..."):
    tenor_order = {'3M':0, '6M':1, '9M':2, '1Y':3, '18M':4, '2Y':5, '3Y':6, '4Y':7, '5Y':8, '7Y':9, '10Y':10, '15Y':11, '20Y':12, '30Y':13, '50Y':14}
    istu_order = ['01','02','03','04','05','06','07','08','09','10','11']
    fut_istu_order = {'01':0,'02':1,'03':2,'04':3,'05':4,'06':5,'07':6,'08':7,'09':8,'10':9,'11':10,'13':11,'00':12}
    ktb_istu_match_dict = {'01':'Foreigns', '02':'Securities', '03':'Insurances', '04':'Asset Mgrs.', '05':'Banks','07':'Other Fins.', '08':'Pensions', '10':'Other Corps.', '11':'Individuals'}
    ktb_info, ktb_otr = load_ktb_info()
    auction_stat_data, auction_otrofr_spread_data, auction_borrowing_data, auction_butterfly_data, auction_option_data = load_auction_data()
    delta_date_list = get_delta_data_date_list()
    trade_date_list = get_trade_data_date_list()
    ###
    potential_supply_long_dict, potential_supply_short_dict, delta_traded_dict, potential_supply_tenor_long_dict, potential_supply_tenor_short_dict, delta_traded_tenor_dict = load_volume_profilate_data()

with st.container():
    tab1, tab2, tab3, tab4 = st.tabs(['Delta S/D', 'KTB S/D', 'KTB Auction', 'Volume Profile'])

    with open(css_dir) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

    with tab1:
        with st.container():
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                delta_file_date = st.selectbox('Date', delta_date_list)
                delta_data = load_delta_data(delta_file_date)
            with col4:
                fx = st.number_input('USDKRW', value=1350.0, step=0.1, format='%f')
            with col3:
                currency = st.selectbox('Display Currency', ['KRW', 'USD'])
                if currency == 'KRW':
                    fx_multiplier = 1
                else:
                    fx_multiplier = 1/(fx/1000)
            with col2:
                days_covered = st.selectbox('Days Covered', [1,5])
                
                delta_demand = delta_data[days_covered]['delta_demand_summary']*fx_multiplier
                delta_supply = delta_data[days_covered]['delta_supply_summary']*fx_multiplier
                delta_borrow = delta_data[days_covered]['delta_borrow_summary']*fx_multiplier
                delta_future = delta_data[days_covered]['delta_future_summary']*fx_multiplier
                volume_future = delta_data[days_covered]['volume_future_summary']
                
        with st.container():
            col1_d, col2_d = st.columns(2)

            with col1_d:
                st.markdown('Delta Demand')
                delta_demand.index.name = 'Tenor'
                st.dataframe(delta_demand.style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), height=525, use_container_width=True)
                
            with col2_d:
                col2_d_1, col2_d_2 = st.columns(2)
                with col2_d_1:
                    st.markdown('Delta Supply')
                    delta_supply.index.name = 'Tenor'
                    st.dataframe(delta_supply.style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), height=525, use_container_width=True)
                with col2_d_2:
                    st.markdown('Delta Borrowing')
                    delta_borrow.index.name = 'Tenor'
                    st.dataframe(delta_borrow.style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), height=525, use_container_width=True)

        with st.container():
            st.markdown('Futures Traded')
            col1_f, col2_f = st.columns(2)
            
            with col1_f:
                st.dataframe(delta_future.style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), use_container_width=True)
            with col2_f:
                st.dataframe(volume_future.style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), use_container_width=True)

    with tab2:
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                col1_1, col1_2 = st.columns(2)
                with col1_2:
                    end_date = datetime.strftime(st.date_input('End Date', datetime.strptime(max(trade_date_list), '%Y-%m-%d'), max_value=datetime.strptime(max(trade_date_list), '%Y-%m-%d')), '%Y-%m-%d')
                    #end_date = st.selectbox('End Date', trade_date_list)
                    trade_data = load_trade_data(end_date)
                with col1_1:
                    start_date = datetime.strftime(st.date_input('Start Date'), '%Y-%m-%d')
                    if start_date>end_date:
                        st.error('Start Date must be earlier than End Date')
            with col2:
                col2_1, col2_2 = st.columns(2)
                with col2_2:
                    fx = st.number_input('USDKRW ', value=1350.0, step=0.1, format='%f')
                with col2_1:
                    currency = st.selectbox('Display Currency ', ['KRW', 'USD'])
                    if currency == 'KRW':
                        fx_multiplier = 1
                    else:
                        fx_multiplier = 1/(fx/1000)
            with col3:
                col3_1, col3_2 = st.columns(2)
                with col3_1:
                    ktb_type = st.multiselect('Select KTB Type', ['국고', '국고이자', '국고원금', '물가'], default =['국고'], max_selections=4)
                with col3_2:
                    ktb_istu_match_dict_reverse = dict(zip(ktb_istu_match_dict.values(), ktb_istu_match_dict.keys()))
                    institution = st.selectbox('Institution', list(ktb_istu_match_dict_reverse.keys()))
                    istu_code = ktb_istu_match_dict_reverse[institution]

            ktb_info_ = ktb_info[(ktb_info['RDMP_DATE'] >= start_date)]
            ktb_codes = []
            for c, n in zip(ktb_info_.STND_ISCD, ktb_info_.KOR_ISNM):
                for t in ktb_type:
                    if t == '국고':
                        if '국고' in n and '국고이자' not in n and '국고원금' not in n:
                            ktb_codes.append(c)
                    else:
                        if t in n:
                            ktb_codes.append(c)
            ktb_info_ = ktb_info_[ktb_info_.STND_ISCD.isin(ktb_codes)]   
            ktb_info_ = ktb_info_[['STND_ISCD', 'KOR_ISNM','SRFC_INT', 'RDMP_DATE']].sort_values(by='RDMP_DATE').set_index('STND_ISCD').reset_index()
            ktb_info_.columns = ['Code', 'Name', 'Coupon', 'Maturity Date']
            
            #proecess data
            trade_data_ = trade_data['01']
            trade_data_['Direction'] = trade_data_['Direction'].replace({1:1, 2:-1})
            trade_data_['Amount'] = trade_data_['Volume']*trade_data_['Direction']
            trade_data_['Delta'] = -1*trade_data_['Amount']*trade_data_['Price']*trade_data_['Duration']*fx_multiplier/1000
            trade_data_d = trade_data_[(trade_data_.Date>=start_date)&(trade_data_.Date<=end_date)&(trade_data_.Code.isin(ktb_codes))].set_index('Date').reset_index()

            trade_data_amount = trade_data_d.pivot_table(index='Code', columns='Date', values='Amount').fillna(0)
            trade_data_amount.columns.name = None
            trade_data_amount.index.name = None
            trade_data_delta = trade_data_d.pivot_table(index='Code', columns='Date', values='Delta').fillna(0)
            trade_data_delta.columns.name = None
            trade_data_delta.index.name = None
            
            ktb_info_d = ktb_info_[ktb_info_['Code'].isin(trade_data_amount.index)].set_index('Code')
            trade_data_amount = pd.merge(ktb_info_d.reset_index()[['Code', 'Name']].set_index('Code'), trade_data_amount,  left_index=True, right_index=True, how='left')
            trade_data_delta = pd.merge(ktb_info_d.reset_index()[['Code', 'Name']].set_index('Code'), trade_data_delta,  left_index=True, right_index=True, how='left')
        
        with st.container():
            col1, col2 = st.columns([1, 2])  # 1:2 ratio for width distribution
            
            with col1:
                st.markdown('KTB List')
                st.dataframe(
                    ktb_info_d.style.format({
                        'SRFC_INT': '{:.3f}',
                        'RDMP_DATE': '{:%Y-%m-%d}'
                    }), 
                    use_container_width=True
                )
            
            with col2:
                st.markdown('Trade Data Amount')
                st.dataframe(
                    trade_data_amount.style
                    .applymap(style_negative, props='color:red;')
                    .format(precision=0, thousands=","), 
                    use_container_width=True
                )
               
        with st.container():
            col1, col2 = st.columns([1, 2])  # 1:2 ratio for width distribution
            
            with col1:
                st.markdown('KTB List')
                st.dataframe(
                    ktb_info_d.style.format({
                        'SRFC_INT': '{:.3f}',
                        'RDMP_DATE': '{:%Y-%m-%d}'
                    }), 
                    use_container_width=True
                )
            
            with col2:
                st.markdown('Trade Data Delta')
                st.dataframe(
                    trade_data_delta.style
                    .applymap(style_negative, props='color:red;')
                    .format(precision=0, thousands=","), 
                    use_container_width=True
                )

    with tab3:
        st.markdown('KTB Auction Data')


    with tab4:
        with st.container():
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                volume_profile_type = st.selectbox('Volume Profile Type', ['Curve', 'Tenor'])
            with col2:
                volume_profile_direction = st.selectbox('Volume Profile Direction', ['Long', 'Short', 'Volume'])
            with col3:
                if volume_profile_type == 'Curve':
                    volume_profile_strat = st.selectbox('Volume Profile Direction', ['Long', 'Short'])
                else:
                    volume_profile_strat = st.selectbox('Volume Profile Direction', ['Long', 'Short'])
            with col5:
                fx = st.number_input('USDKRW', value=1350.0, step=0.1, format='%f')
            with col4: 
                currency = st.selectbox('Display Currency', ['KRW', 'USD'])
                if currency == 'KRW':
                    fx_multiplier = 1
                else:
                    fx_multiplier = 1/(fx/1000)

            if volume_profile_type == 'Curve' and volume_profile_direction == 'Long':
                volume_profile_data = potential_supply_long_dict
            elif volume_profile_type == 'Curve' and volume_profile_direction == 'Short':
                volume_profile_data = potential_supply_short_dict
            elif volume_profile_type == 'Tenor' and volume_profile_direction == 'Long':
                volume_profile_data = potential_supply_tenor_long_dict
            potential_supply_long_dict, potential_supply_short_dict, delta_traded_dict, potential_supply_tenor_long_dict, potential_supply_tenor_short_dict, delta_traded_tenor_dict = load_volume_profilate_data()



