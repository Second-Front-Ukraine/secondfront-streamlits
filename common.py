from urllib.parse import urlparse, parse_qs
import re

import streamlit as st
import pandas as pd
import altair as alt
from clients import WaveClient, TrackingClient, decode_invoice_id
from geopy.geocoders import Nominatim


wave = WaveClient()
geolocator = Nominatim(user_agent="example app")
tracking = TrackingClient(aws_key=st.secrets['aws']['AWS_ACCESS_KEY_ID'], aws_secret=st.secrets['aws']['AWS_SECRET_ACCESS_KEY'])

MEMO_RE = re.compile(r"(Company name\:(?P<company>.*))?\n*(Note\:(?P<comment>.*))?")


def sanitize_address(raw_address):
    city = raw_address.get('city')
    if city and ', ' in city:
        city_parts = city.split(', ')
        city = ', '.join(city_parts[:-1])
        province = city_parts[-1]
    else:
        province = (raw_address.get('province') or {}).get('name')
    country = (raw_address.get('country') or {}).get('name')

    return (
        raw_address.get('addressLine1'),
        raw_address.get('addressLine2'),
        city,
        province,
        country,
        raw_address.get('postalCode', None)
    )


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
        shipping_address = sanitize_address(shipping_details.get('address') or {})
        address_details = sanitize_address(inv['node']['customer'].get('address') or {})
        comment, company = parse_memo(inv['node']['memo'])

        _, invoice_id = decode_invoice_id(inv['node']['id'])
        data.append({
            'id': invoice_id,
            'memo': inv['node']['memo'],
            'comment': comment,
            'company': company,
            'status': inv['node']['status'],
            'invoice_number': inv['node']['invoiceNumber'],
            'last_sent_at': inv['node']['lastSentAt'],
            'last_sent_via': inv['node']['lastSentVia'],
            'registered_at': inv['node']['createdAt'],
            'createdAt': inv['node']['createdAt'],
            'amountDue': inv['node']['amountDue']['value'],
            'amountPaid': inv['node']['amountPaid']['value'],
            'total': inv['node']['total']['value'],
            'customer_name': inv['node']['customer']['name'],
            'customer_email': inv['node']['customer']['email'],
            'customer_phone': shipping_details.get('phone'),
            'shipping_address_line_1': shipping_address[0],
            'shipping_address_line_2': shipping_address[1],
            'shipping_address_city': shipping_address[2],
            'shipping_address_province': shipping_address[3],
            'shipping_address_country': shipping_address[4],
            'shipping_address_postal_code': shipping_address[5],
            'address_line_1': address_details[0],
            'address_line_2': address_details[1],
            'address_city': address_details[2],
            'address_province': address_details[3],
            'address_country': address_details[4],
            'address_postal_code': address_details[5],
        })

    df = pd.DataFrame(data)
    df['total'] = df['total'].str.replace(',', '').astype(float)
    df['amountDue'] = df['amountDue'].str.replace(',', '').astype(float)
    df['amountPaid'] = df['amountPaid'].str.replace(',', '').astype(float)
    df['registered_at'] = pd.to_datetime(df['registered_at'])
    df['createdAt'] = pd.to_datetime(df['createdAt'])
    df['registered_at_date'] = df['registered_at'].dt.date
    df['createdAtDate'] = df['createdAt'].dt.date

    return df


def invoices_to_items_df(invoices):
    data = []

    for inv in invoices:
        shipping_details = inv['node']['customer'].get('shippingDetails') or {}
        shipping_address = sanitize_address(shipping_details.get('address') or {})
        address_details = sanitize_address(inv['node']['customer'].get('address') or {})
        comment, company = parse_memo(inv['node']['memo'])

        for item in inv['node']['items']:
            _, invoice_id = decode_invoice_id(inv['node']['id'])
            data.append({
                'id': invoice_id,
                'memo': inv['node']['memo'],
                'comment': comment,
                'company': company,
                'status': inv['node']['status'],
                'invoice_number': inv['node']['invoiceNumber'],
                'last_sent_at': inv['node']['lastSentAt'],
                'last_sent_via': inv['node']['lastSentVia'],
                'registered_at': inv['node']['createdAt'],
                'createdAt': inv['node']['createdAt'],
                'amountDue': inv['node']['amountDue']['value'],
                'amountPaid': inv['node']['amountPaid']['value'],
                'total': inv['node']['total']['value'],
                'customer_name': inv['node']['customer']['name'],
                'customer_email': inv['node']['customer']['email'],
                'customer_phone': shipping_details.get('phone'),
                'shipping_address_line_1': shipping_address[0],
                'shipping_address_line_2': shipping_address[1],
                'shipping_address_city': shipping_address[2],
                'shipping_address_province': shipping_address[3],
                'shipping_address_country': shipping_address[4],
                'shipping_address_postal_code': shipping_address[5],
                'address_line_1': address_details[0],
                'address_line_2': address_details[1],
                'address_city': address_details[2],
                'address_province': address_details[3],
                'address_country': address_details[4],
                'address_postal_code': address_details[5],
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
    df['createdAt'] = pd.to_datetime(df['createdAt'])
    df['createdAtDate'] = df['createdAt'].dt.date

    return df

def tracking_raw_to_df(data):
    df = pd.DataFrame(data)
    def apply_utm_campaign(value):
        return ','.join(parse_qs(urlparse(value).query).get('utm_campaign', []))
    df['utm_campaign'] = df['referrer'].apply(apply_utm_campaign)

    def apply_utm_medium(value):
        return ','.join(parse_qs(urlparse(value).query).get('utm_medium', []))
    df['utm_medium'] = df['referrer'].apply(apply_utm_medium)

    return df
