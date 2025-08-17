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
    """Helper function to save data using joblib with exception handling."""
    try:
        file_path = os.path.join(data_folder, file_name)
        dump(data, file_path, compress=3)  # Compression level 3 (balances speed & size)
        logging.info(f"Saved {file_name} using joblib")
    except Exception as e:
        logging.error(f"Failed to save {file_name}: {e}")

def load_joblib(file_name):
    data_folder = file_dir+"\\HSBCMonitor"
    os.makedirs(data_folder, exist_ok=True)
    """Helper function to load joblib files with error handling."""
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
    date_list = [file.name.split('_')[1].split('.')[0] for file in delta_data_files]
    return date_list

@st.cache_data(show_spinner=False)
def get_trade_data_date_list():
    data_folder = file_dir+"\\HSBCMonitor"
    files = get_files_by_extension(data_folder, 'joblib')
    trade_data_files = [file for file in files if 'tradedata_' in file.name]
    date_list = [file.name.split('_')[1].split('.')[0] for file in trade_data_files]
    return date_list

@st.cache_data(show_spinner=False)
def load_auction_data():
    auction_stat_data = load_joblib(auction_stat_data.joblib)
    auction_otrofr_spread_data = load_joblib(auction_otrofr_spread_data.joblib)
    auction_borrowing_data = load_joblib(auction_borrowing_data.joblib)
    auction_butterfly_data = load_joblib(auction_butterfly_data.joblib)
    auction_option_data = load_joblib(auction_option_data.joblib)
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
    trade_data = load_joblib(f"tradedata_{end_dt}.joblib")
    return trade_data

with st.spinner("Querying Data, Will take about 2 minutes, Please Wait..."):
    tenor_order = {'3M':0, '6M':1, '9M':2, '1Y':3, '18M':4, '2Y':5, '3Y':6, '4Y':7, '5Y':8, '7Y':9, '10Y':10, '15Y':11, '20Y':12, '30Y':13, '50Y':14}
    istu_order = ['01','02','03','04','05','06','07','08','09','10','11']
    fut_istu_order = {'01':0,'02':1,'03':2,'04':3,'05':4,'06':5,'07':6,'08':7,'09':8,'10':9,'11':10,'13':11,'00':12}
    ktb_info, ktb_otr = load_ktb_info()
    auction_stat_data, auction_otrofr_spread_data, auction_borrowing_data, auction_butterfly_data, auction_option_data = load_auction_data()
    date_list = get_delta_data_date_list()

with st.container():
    tab1, tab2, tab3 = st.tabs(['Delta S/D', 'KTB S/D', 'KTB Auction'])

    with open(css_dir) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html = True)

    with tab1:
        with st.container():
            col1, col2, col3 = st.columns(3)
            with col1:
                file_date = st.selectbox('Choose a Date', date_list)
                delta_data = load_delta_data(file_date)
            with col2:
                days_covered = st.selectbox('Days Covered', [1,5])
                
                delta_demand = delta_data[days_covered]['delta_demand_summary']
                delta_supply = delta_data[days_covered]['delta_supply_summary']
                delta_borrow = delta_data[days_covered]['delta_borrow_summary']
                delta_future = delta_data[days_covered]['delta_future_summary']
                volume_future = delta_data[days_covered]['volume_future_summary']
                
        with st.container():
            col1_d, col2_d = st.columns(2)

            with col1_d:
                st.markdown('Delta Demand')
                st.dataframe(delta_demand.set_index('Tenor').style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), height=525, use_container_width=True)
                
            with col2_d:
                col2_d_1, col2_d_2 = st.columns(2)
                with col2_d_1:
                    st.markdown('Delta Supply')
                    st.dataframe(delta_supply.set_index('Tenor').style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), height=525, use_container_width=True)
                with col2_d_2:
                    st.markdown('Delta Borrowing')
                    st.dataframe(delta_borrow.set_index('Tenor').style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), height=525, use_container_width=True)

        with st.container():
            st.markdown('Futures Traded')
            col1_f, col2_f = st.columns(2)
            
            with col1_f:
                st.dataframe(delta_future.style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), use_container_width=True)
            with col2_f:
                st.dataframe(volume_future.style.applymap(style_negative, props='color:red;').format(precision=0, thousands=","), use_container_width=True)
