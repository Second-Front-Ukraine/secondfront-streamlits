import streamlit as st


st.set_page_config(
    page_title="Second Front Stats",
    page_icon="⚔️",
)

txt = """
# Second Front Ukraine Foundation campaign stats
This app shows donations and registrations by campaign for Second Front.
"""

st.markdown(txt)

st.warning("Most of the information here is confidential. Dissemination of any of the information contained within is strictly forbidden outside of members, organizers, or volunteers of Second Front Ukraine Foundation.")

txt = """
Select campaign in the left sidebar. Each campaign is behind a unique password. To request password, message [@Taras Yanchynskyy](https://secondfrontua.slack.com/archives/D035ALV4ZN1) in Slack
"""

st.markdown(txt)