import os
import streamlit as st
from gql import gql, Client
from gql.transport.aiohttp import AIOHTTPTransport


WAVE_TOKEN = st.secrets['wave']['WAVE_TOKEN']
WAVE_URL = "https://gql.waveapps.com/graphql/public"
WAVE_BUSINESS_ID = st.secrets['wave']["WAVE_BUSINESS_ID"]


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

