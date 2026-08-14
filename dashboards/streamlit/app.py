import streamlit as st
import clickhouse_connect
import plotly.express as px

st.set_page_config(page_title="Fraud Analyst View", layout="wide")


@st.cache_resource
def get_client():
    return clickhouse_connect.get_client(host="clickhouse", port=8123)


client = get_client()

st.title("Fraud Analyst View")

df = client.query_df("""
    SELECT transaction_id, user_id, amount, merchant, country,
           event_timestamp, source, is_fraud, fraud_reason, confidence_score
    FROM transactions
    ORDER BY event_timestamp DESC
    LIMIT 5000
""")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Flagged transactions by merchant")
    flagged = df[df["is_fraud"] == 1]
    st.plotly_chart(px.bar(flagged["merchant"].value_counts().reset_index(),
                            x="merchant", y="count"), use_container_width=True)

with col2:
    st.subheader("Amount over time")
    st.plotly_chart(px.scatter(df, x="event_timestamp", y="amount", color="is_fraud"),
                     use_container_width=True)

st.subheader("Flagged transactions")
st.dataframe(flagged[["transaction_id", "user_id", "amount", "merchant",
                       "country", "fraud_reason", "confidence_score"]])
