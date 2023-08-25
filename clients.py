import os
import base64

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config
import streamlit as st
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


WAVE_TOKEN = st.secrets['wave']['WAVE_TOKEN']
WAVE_URL = "https://gql.waveapps.com/graphql/public"
WAVE_BUSINESS_ID = st.secrets['wave']["WAVE_BUSINESS_ID"]


def decode_invoice_id(value):
    try:
        s = base64.b64decode(value).decode()
        parts = s.split(';')

        business_id = parts[0].split(':')[1].strip()
        invoice_id = parts[1].split(':')[1].strip()
    except Exception:
        return 'unknown', value

    return business_id, invoice_id

INVOICES_QUERY = gql("""query($businessId: ID!, $page: Int!, $slug: String!) {
  business(id: $businessId) {
    id
    invoices(
      page: $page,
      invoiceNumber: $slug
    ) {
      edges {
        node {
          id
          title
          subhead
          invoiceNumber
          footer
          memo
          status
          lastSentAt
          lastSentVia
          createdAt
          amountDue {
            raw
            value
          }
          amountPaid {
            raw
            value
          }
          total {
            raw
            value
          }
          customer {
            id
            name
            email
            address {
                addressLine1
                addressLine2
                city
                province {
                    code
                    name
                }
                country {
                    code
                    name
                }
                postalCode
            }
            shippingDetails {
                name
                phone
                address {
                    addressLine1
                    addressLine2
                    city
                    province {
                        code
                        name
                    }
                    country {
                        code
                        name
                    }
                    postalCode
                }
            }
          }
          items {
            description
            quantity
            unitPrice
            product {
              id
              name
            }
          }
        }
      }
      pageInfo {
        totalPages
        currentPage
        totalCount
      }
    }
  }
}""")

class WaveClient:
    """
    Client for Wave GraphQL API.

    API Playgound - https://developer.waveapps.com/hc/en-us/articles/360018937431-API-Playground
    """

    def __init__(self, business_id=WAVE_BUSINESS_ID):
        self.business_id = business_id
        headers = {"Authorization": f"Bearer {WAVE_TOKEN}"}
        transport = AIOHTTPTransport(url=WAVE_URL, headers=headers)
        self.client = Client(transport=transport)
    
    def get_invoices_for_slug(self, slug: str):
        invoices = []
        page = 1
        while True:
            response = self.client.execute(INVOICES_QUERY, variable_values={
                'businessId': self.business_id,
                'page': page,
                'slug': slug.upper(),
            })
            invoices.extend(response['business']['invoices']['edges'])

            # Check for next page
            total_pages = response['business']['invoices']['pageInfo']['totalPages']
            if page >= total_pages:
                break
            page += 1
        
        return invoices


class TrackingClient:
    
    def __init__(self, aws_key, aws_secret, business_id=WAVE_BUSINESS_ID):
        aws_config = Config(
            region_name = 'us-east-2',
            signature_version = 'v4',
            retries = {
                'max_attempts': 10,
                'mode': 'standard'
            }
        )
        self.dynamodb = boto3.resource('dynamodb',
            config=aws_config,                           
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret
        )
        self.attribution_table = self.dynamodb.Table('donation-tracking')
        self.business_id = base64.b64decode(business_id).decode().split(':')[1]

    def get_all(self):
        response = self.attribution_table.query(
            KeyConditionExpression=Key('business_id').eq(self.business_id)
        )
        data = response['Items']
        while 'LastEvaluatedKey' in response:
            response = self.attribution_table.query(ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response['Items'])

        return data
