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
def get_point(location):
    return geolocator.geocode(location).point


def invoices_to_df(invoices):
    data = []

    for inv in invoices:
        shipping_details = inv['node']['customer'].get('shippingDetails') or {}
        shipping_address = shipping_details.get('address') or {}
        city = shipping_address.get('city')
        province = (shipping_address.get('province') or {}).get('name')
        country = (shipping_address.get('country') or {}).get('name')

        if country:
            loc = city if city else ''
            loc += f"{', ' if loc else ''}{province}" if province else ''
            loc += f"{', ' if loc else ''}{country}"
            point = get_point(loc)
        else:
            point = (0, 0)

        data.append({
            'memo': inv['node']['memo'],
            'status': inv['node']['status'],
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
        for item in inv['node']['items']:
            data.append({
                'memo': inv['node']['memo'],
                'status': inv['node']['status'],
                'amountDue': inv['node']['amountDue']['value'],
                'amountPaid': inv['node']['amountPaid']['value'],
                'total': inv['node']['total']['value'],
                'customer_name': inv['node']['customer']['name'],
                'customer_email': inv['node']['customer']['email'],
                'customer_phone': shipping_details.get('phone'),
                'address_line_1': shipping_address.get('addressLine1'),
                'address_line_2': shipping_address.get('addressLine2'),
                'address_city': shipping_address.get('city'),
                'address_province': (shipping_address.get('province') or {}).get('name'),
                'address_country': (shipping_address.get('country') or {}).get('name'),
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

    st.title("Run For Ukraine registration stats")
    invoices = get_runforukraine_invoices()
    # st.write(invoices)
    df = invoices_to_df(invoices)
    items_df = invoices_to_items_df(invoices)

    df_paid = df[df['status'] == 'PAID']
    invoices_df_unpaid = df[(df['status'] != 'PAID') & (df['status'] != 'DRAFT')]
    items_df_paid = items_df[items_df['status'] == 'PAID']

    c0, c1, c2 = st.columns(3)
    c0.metric("Total collected", f"{df_paid['amountPaid'].sum():.2f}")
    c1.metric("Total registered", len(df_paid))
    c2.metric("Total abandoned", len(invoices_df_unpaid))
    st.header("By country")
    st.table(df_paid.groupby(['address_country']).count()['customer_name'])

    with st.expander("By province/state"):
        st.table(df_paid.groupby(['address_country', 'address_province']).count()['customer_name'])

    st.header("By item")
    st.table(items_df_paid.groupby('name').count()['customer_name'])

    st.header("Notes")
    paid_memos = df[(df['memo'].str.len() > 0)]
    for _, inv in paid_memos.iterrows():
        st.markdown(f"*{inv['customer_name']}* from *{inv['address_city']}, {inv['address_country']}* {'registered and' if inv['status'] == 'PAID' else ''} said  \n> {inv['memo']}")

    st.header("Map")
    st.map(df_paid[['lat', 'lon']])

    # st.markdown("---")
    # with st.expander("All invoices"):
    #     st.write(df)
    # with st.expander("All items"):
    #     st.write(items_df)

    
elif password:
    st.warning("Геть з України, москаль некрасівий! Ой, тобто, пароль неправильний.")
