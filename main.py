import streamlit as st
import pandas as pd
from clients import WaveClient
from geopy.geocoders import Nominatim


wave = WaveClient()
geolocator = Nominatim(user_agent="example app")

@st.experimental_memo(ttl=600)
def get_runforukraine_invoices():
    return wave.get_invoices_for_slug("2FUA-RUN4UA")


@st.cache
def get_point(city, province, country):
    loc = city if city else ''
    loc += f"{', ' if loc else ''}{province}" if province else ''
    loc += f"{', ' if loc else ''}{country}"

    # try:
    geo = geolocator.geocode(loc)

    if geo is None:
        loc = province if province else ''
        loc += f"{', ' if loc else ''}{country}"
        geo = geolocator.geocode(loc)

    if geo is None:
        geo = geolocator.geocode(country)
    # except Exception:
    #     return (0, 0)

    if geo is not None: 
        return geo.point


def invoices_to_df(invoices, show_map=False):
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

        if country and show_map:
            point = get_point(city, province, country)
        else:
            point = (0, 0)

        data.append({
            'memo': inv['node']['memo'],
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
            'lat': point[0],
            'lon': point[1],
        })

    df = pd.DataFrame(data)
    df['total'] = df['total'].astype(float)
    df['amountDue'] = df['amountDue'].astype(float)
    df['amountPaid'] = df['amountPaid'].astype(float)

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

        for item in inv['node']['items']:
            data.append({
                'memo': inv['node']['memo'],
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
    df['total'] = df['total'].astype(float)
    df['amountDue'] = df['amountDue'].astype(float)
    df['amountPaid'] = df['amountPaid'].astype(float)
    df['unitPrice'] = df['unitPrice'].astype(float)
    df['quantity'] = df['quantity'].astype(int)

    return df


password = st.text_input("Гасло!", type="password")

if password == st.secrets['VIEWER_PASSWORD']:
    st.info("OK")
    show_map = st.checkbox("Show map", False)

    st.title("Run For Ukraine registration stats")
    invoices = get_runforukraine_invoices()
    df = invoices_to_df(invoices, show_map=show_map)
    items_df = invoices_to_items_df(invoices)

    df_paid = df[df['status'] == 'PAID']
    df_paid_unconfired = df_paid[df_paid['last_sent_via'] == 'NOT_SENT']
    invoices_df_unpaid = df[(df['status'] != 'PAID') & (df['status'] != 'DRAFT')]
    items_df_paid = items_df[items_df['status'] == 'PAID']

    c0, c1, c2, c3 = st.columns(4)
    c0.metric("Total collected", f"{df_paid['amountPaid'].sum():.2f}")
    c1.metric("Total unconfirmed", len(df_paid_unconfired))
    c2.metric("Total registered", len(df_paid))
    c3.metric("Total abandoned", len(invoices_df_unpaid))
    st.header("By country")
    st.table(df_paid.groupby(['address_country']).count()['customer_name'])

    with st.expander("By province/state"):
        st.table(df_paid.groupby(['address_country', 'address_province']).count()['customer_name'])

    st.header("By item")
    st.table(items_df_paid.groupby('name').count()['customer_name'])

    st.header("Notes")
    paid_memos = df[(df['memo'].str.len() > 0)]
    for _, inv in paid_memos.iterrows():
        st.markdown(f"*{inv['customer_name']}* from *{inv['address_city']}, {inv['address_country']}* {'registered and' if inv['status'] == 'PAID' else ''} said  \n```\n{inv['memo']}```")

    if show_map:
        st.header("Map")
        st.map(df_paid[['lat', 'lon']])

    st.markdown("---")
    show_participants = st.checkbox("Show participants", False)
    if show_participants:
        c0, c1, c2, c3 = st.columns(4)
        show_df = df
        filter_status = c0.selectbox("Registration status", ("ALL", "PAID", "SAVED", "VIEWED", "OVERDUE"), index=1)
        filter_sent_status = c1.selectbox("Email Confirmation", ("ALL", "NOT_SENT", "MARKED_SENT"), index=1)
        filter_country = c2.selectbox("Country", ["ALL", *show_df['address_country'].unique()])
        filter_text = c3.text_input("Search fields")
        show_columns = st.multiselect("Show columns", list(show_df.columns), ['invoice_number', 'customer_name', 'amountPaid', 'status', 'address_country', 'registered_at'])
        if filter_status != "ALL":
            show_df = show_df[show_df['status'] == filter_status]
        if filter_sent_status != "ALL":
            show_df = show_df[show_df['last_sent_via'] == filter_sent_status]
        if filter_country != "ALL":
            show_df = show_df[show_df['address_country'] == filter_country]
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

        st.write(show_df[show_columns])
    show_items = st.checkbox("Show items", False)
    if show_items:
        c0, c1 = st.columns(2)
        show_df = items_df
        filter_status = c0.selectbox("Status", ("ALL", "PAID", "SAVED", "VIEWED", "OVERDUE"), index=1)
        filter_text = c1.text_input("Search")
        filter_item = st.selectbox("Item", ("ALL", *list(show_df['name'].unique())))
        show_columns = st.multiselect("Show columns", list(show_df.columns), ['invoice_number', 'status', 'address_country', 'name', 'quantity', 'customer_name', 'amountPaid'])
        if filter_status != "ALL":
            show_df = show_df[show_df['status'] == filter_status]
        if filter_item != "ALL":
            show_df = show_df[show_df['name'] == filter_item]
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
        st.write(show_df[show_columns])

    
elif password:
    st.warning("Геть з України, москаль некрасівий! Ой, тобто, пароль неправильний.")
