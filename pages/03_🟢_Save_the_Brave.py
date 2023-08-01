import re
import streamlit as st
import pandas as pd
import altair as alt
from clients import WaveClient
from geopy.geocoders import Nominatim


wave = WaveClient()
geolocator = Nominatim(user_agent="example app")

MEMO_RE = re.compile(r"(Company name\:(?P<company>.*))?\n*(Note\:(?P<comment>.*))?")
CAMPAIGN = "2FUA-SVTBV"

@st.cache_data(ttl=600)
def get_capmaign_invoices(slug):
    return wave.get_invoices_for_slug(slug)


def parse_memo(memo):
    match = MEMO_RE.match(memo)
    if match:
        components = match.groupdict()

        return (components.get('comment') or '').strip(), (components.get('company') or '').strip()

    return memo, None

def invoices_to_df(invoices):
    data = []

    for inv in invoices:
        shipping_details = inv['node']['customer'].get('shippingDetails') or {}
        shipping_address = shipping_details.get('address') or {}
        city = shipping_address.get('city')
        if city and ', ' in city:
            city_parts = city.split(', ')
            city = ', '.join(city_parts[:-1])
            province = city_parts[-1]
        else:
            province = (shipping_address.get('province') or {}).get('name')
        country = (shipping_address.get('country') or {}).get('name')
        comment, company = parse_memo(inv['node']['memo'])

        data.append({
            'memo': inv['node']['memo'],
            'comment': comment,
            'company': company,
            'status': inv['node']['status'],
            'invoice_number': inv['node']['invoiceNumber'],
            'last_sent_at': inv['node']['lastSentAt'],
            'last_sent_via': inv['node']['lastSentVia'],
            'registered_at': inv['node']['createdAt'],
            'amountDue': inv['node']['amountDue']['value'],
            'amountPaid': inv['node']['amountPaid']['value'],
            'total': inv['node']['total']['value'],
            'customer_name': inv['node']['customer']['name'],
            'customer_email': inv['node']['customer']['email'],
            'customer_phone': shipping_details.get('phone'),
            'address_line_1': shipping_address.get('addressLine1'),
            'address_line_2': shipping_address.get('addressLine2'),
            'address_city': city,
            'address_province': province,
            'address_country': country,
            'address_postal_code': shipping_address.get('postalCode', None),
        })

    df = pd.DataFrame(data)
    df['total'] = df['total'].str.replace(',', '').astype(float)
    df['amountDue'] = df['amountDue'].str.replace(',', '').astype(float)
    df['amountPaid'] = df['amountPaid'].str.replace(',', '').astype(float)
    df['registered_at'] = pd.to_datetime(df['registered_at'])
    df['registered_at_date'] = df['registered_at'].dt.date

    return df


def invoices_to_items_df(invoices):
    data = []

    for inv in invoices:
        shipping_details = inv['node']['customer'].get('shippingDetails') or {}
        shipping_address = shipping_details.get('address') or {}
        city = shipping_address.get('city')
        if city and ', ' in city:
            city_parts = city.split(', ')
            city = ', '.join(city_parts[:-1])
            province = city_parts[-1]
        else:
            province = (shipping_address.get('province') or {}).get('name')
        country = (shipping_address.get('country') or {}).get('name')
        comment, company = parse_memo(inv['node']['memo'])

        for item in inv['node']['items']:
            data.append({
                'memo': inv['node']['memo'],
                'comment': comment,
                'company': company,
                'status': inv['node']['status'],
                'invoice_number': inv['node']['invoiceNumber'],
                'last_sent_at': inv['node']['lastSentAt'],
                'last_sent_via': inv['node']['lastSentVia'],
                'registered_at': inv['node']['createdAt'],
                'amountDue': inv['node']['amountDue']['value'],
                'amountPaid': inv['node']['amountPaid']['value'],
                'total': inv['node']['total']['value'],
                'customer_name': inv['node']['customer']['name'],
                'customer_email': inv['node']['customer']['email'],
                'customer_phone': shipping_details.get('phone'),
                'address_line_1': shipping_address.get('addressLine1'),
                'address_line_2': shipping_address.get('addressLine2'),
                'address_city': city,
                'address_province': province,
                'address_country': country,
                'address_postal_code': shipping_address.get('postalCode', None),
                'quantity': item['quantity'],
                'description': item['description'],
                'unitPrice': item['unitPrice'],
                'id': item['product']['id'],
                'name': item['product']['name'],
            })

    df = pd.DataFrame(data)
    df['total'] = df['total'].str.replace(',', '').astype(float)
    df['amountDue'] = df['amountDue'].str.replace(',', '').astype(float)
    df['amountPaid'] = df['amountPaid'].str.replace(',', '').astype(float)
    df['unitPrice'] = df['unitPrice'].str.replace(',', '').astype(float)
    df['quantity'] = df['quantity'].astype(int)
    df['registered_at'] = pd.to_datetime(df['registered_at'])
    df['registered_at_date'] = df['registered_at'].dt.date

    return df

@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

if 'shall_pass' not in st.session_state:
    password = st.text_input("Гасло!", type="password")

    if password == st.secrets['VIEWER_PASSWORD']:
        st.button("Proceed", key="shall_pass")
    elif password:
        st.warning("Геть з України, москаль некрасівий! Ой, тобто, пароль неправильний.")
elif st.session_state.get('shall_pass'):
    st.info("OK")

    st.title(f"{CAMPAIGN} stats")
    invoices = get_capmaign_invoices(CAMPAIGN)
    try:
        df = invoices_to_df(invoices)
    except Exception:
        print(invoices)
        raise
    items_df = invoices_to_items_df(invoices)

    df_paid = df[df['status'] == 'PAID']
    df_paid_unconfired = df_paid[df_paid['last_sent_via'] == 'NOT_SENT']
    invoices_df_unpaid = df[(df['status'] != 'PAID') & (df['status'] != 'DRAFT')]
    items_df_paid = items_df[items_df['status'] == 'PAID']

    c0, c1, c2, c3 = st.columns(4)
    c0.metric("Total collected", f"{df_paid['amountPaid'].sum():.2f}")
    # c1.metric("Emails unsent", len(df_paid_unconfired))
    c2.metric("Total donated", len(df_paid))
    c3.metric("Total abandoned", len(invoices_df_unpaid))

    st.write("Amounts distribution")
    st.bar_chart(df_paid['amountPaid'].value_counts())

    hover = alt.selection_single(
        fields=["registered_at_date"],
        nearest=True,
        on="mouseover",
        # empty="none",
        clear="mouseout"
    )
    amount_chart = alt.Chart(df_paid).mark_bar(color='#57A44C').encode(
        x=alt.X('registered_at_date:T', axis=alt.Axis(title='Date')),
        y=alt.Y('sum(amountPaid):Q', axis=alt.Axis(title='Sum of amountPaid', titleColor='#57A44C')),
    )
    text_chart = amount_chart.mark_text(
        align='left',
        baseline='middle',
        dy=-10,
        dx=-10,
        color="#57A44C"
    ).encode(
        text='sum(amountPaid):Q'
    )
    count_chart = alt.Chart(df_paid).mark_circle(color='#007bff', size=60).encode(
        x=alt.X('registered_at_date:T', axis=alt.Axis(title='Date')),
        y=alt.Y('count():Q',
          axis=alt.Axis(title='Count of Donations', titleColor='#007bff')),
    )
    st.altair_chart(alt.layer(amount_chart + text_chart, count_chart).resolve_scale(
        y = 'independent'
    ).add_selection(
        hover
    ).configure(padding=50).interactive(), use_container_width=True)

    st.header("By company")
    st.subheader("Counts")
    st.table(df_paid.groupby(['company']).count()['customer_name'])
    st.subheader("Amounts")
    st.table(df_paid.groupby(['company'])[['amountPaid']].sum()['amountPaid'])

    st.header("By item")
    st.table(items_df_paid.groupby('name').count()['customer_name'])

    st.header("Notes")
    paid_memos = df[(df['comment'].str.len() > 0)]
    for _, inv in paid_memos.iterrows():
        company_span = f"from *{inv['company']}*" if inv['company'] else ''
        st.markdown(f"*{inv['customer_name']}* {company_span} {'registered and' if inv['status'] == 'PAID' else ''} said  \n```\n{inv['comment']}")

    st.markdown("---")
    show_donors = st.checkbox("Show donors", False)
    if show_donors:
        c0, c1, c2= st.columns(3)
        show_df = df
        filter_status = c0.selectbox("Paid status", ("ALL", "PAID", "SAVED", "VIEWED", "OVERDUE"), index=1)
        filter_sent_status = c1.selectbox("Email Confirmation", ("ALL", "NOT_SENT", "MARKED_SENT"), index=1)
        filter_text = c2.text_input("Search fields")
        show_columns = st.multiselect("Show columns", list(show_df.columns), ['invoice_number', 'customer_name', 'amountPaid', 'status', 'memo', 'registered_at'])
        if filter_status != "ALL":
            show_df = show_df[show_df['status'] == filter_status]
        if filter_sent_status != "ALL":
            show_df = show_df[show_df['last_sent_via'] == filter_sent_status]
        if filter_text:
            search = (
                show_df['customer_name'].str.contains(filter_text, case=False) |
                show_df['customer_email'].str.contains(filter_text, case=False) |
                show_df['invoice_number'].str.contains(filter_text, case=False) |
                show_df['customer_phone'].str.contains(filter_text, case=False) |
                show_df['address_city'].str.contains(filter_text, case=False) |
                show_df['address_province'].str.contains(filter_text, case=False) |
                show_df['address_postal_code'].str.contains(filter_text, case=False) |
                show_df['address_line_1'].str.contains(filter_text, case=False) |
                show_df['memo'].str.contains(filter_text, case=False)
            )
            show_df = show_df[search]

        st.markdown(f"Showing {len(show_df)} out of all {len(df)}")
        st.write(show_df[show_columns])
        st.download_button(
            label="Download the donors table above as CSV",
            data=convert_df(show_df[show_columns]),
            file_name='donors.csv',
            mime='text/csv',
        )
    
    st.markdown("---")
    if st.button("Clear cache"):
        st.cache_data.clear()
