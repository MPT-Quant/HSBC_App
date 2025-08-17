import streamlit as st

st.title('HSBC Research App')
st.subheader('by Jungwon Kim')
st.markdown('Macro Quant / HSBC Seoul Rates Trading')
st.divider()
st.markdown('Email  : jung.won.kim@kr.hsbc.com')
st.markdown('Mobile : 82-10-9248-1552')

if 'note' not in st.session_state:
    st.session_state.note = ''

st.session_state.note = st.sidebar.text_area('Note', st.session_state.note, height=300)

