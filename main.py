from tkinter import W
import streamlit as st
import pandas as pd
from clients import WaveClient

wave = WaveClient()

@st.experimental_memo(ttl=3600)
def get_runforukraine_invoices():
    return wave.get_invoices_for_slug("2FUA-RUN4UA")


def invoices_to_df(invoices):
    data = []

    for inv in invoices:
        shipping_details = inv['node']['customer'].get('shippingDetails') or {}
        shipping_address = shipping_details.get('address') or {}

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



password = st.sidebar.text_input("Password")

if password == st.secrets['VIEWER_PASSWORD']:
    st.sidebar.info("OK")

    st.markdown("# Run For Ukraine registration stats")
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
    st.write("By country")
    st.table(df_paid.groupby('address_country').count()['customer_name'])

    st.write("By item")
    st.table(items_df_paid.groupby('name').count()['customer_name'])

    with st.expander("All invoices"):
        st.write(df)
    with st.expander("All items"):
        st.write(items_df)
elif password:
    st.sidebar.warning("Геть з України, москаль некрасівий! Ой, тобто, пароль неправильний.")
