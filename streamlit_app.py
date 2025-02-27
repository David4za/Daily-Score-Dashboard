from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px


# Streamlit

st.title("Daily Score Dashboard")
st.write("Upload open and closed orders")

# file uploading section

col_1, col_2 = st.columns(2)
with col_1:
    uploaded_open_orders = st.file_uploader("Open orders in .csv format", type="csv",)
with col_2:
    uploaded_closed_orders = st.file_uploader("Closed Orders", type="csv")

if uploaded_open_orders and uploaded_closed_orders:

    # global variables
    df_closed = pd.read_csv(uploaded_closed_orders,delimiter=";" )
    df_open = pd.read_csv(uploaded_open_orders, delimiter=';' )
    
    # Add this column to ensure both dfs have the exact same column headers
    # Here using the pd.to_datetime works really well, because datetime.now() gives a different type of time stamp
    # that is not useable to same way as most datetime formats.
    df_open['(Zelf) Gerealiseerde Leverdatum'] = pd.to_datetime(datetime.now().date())
    
    # This is to keep track of which df the data comes from in the merged columns
    df_closed['OrderType'] = 'Closed'
    df_open['OrderType'] = 'Open'
    
    yesterday = datetime.now() - timedelta(days=1)
    
    # convert the data to DateTime
    
    df_closed['(Zelf) Gerealiseerde Leverdatum'] = pd.to_datetime(df_closed['(Zelf) Gerealiseerde Leverdatum'])
    df_closed['VDoc Positie Laatst bev. datum'] = pd.to_datetime(df_closed['VDoc Positie Laatst bev. datum'])
    df_closed['VDoc Positie Eerst bev. datum'] = pd.to_datetime(df_closed['VDoc Positie Eerst bev. datum'])
    df_open['VDoc Positie Eerst bev. datum'] = pd.to_datetime(df_open['VDoc Positie Eerst bev. datum'])
    df_open['VDoc Positie Laatst bev. datum'] = pd.to_datetime(df_open['VDoc Positie Laatst bev. datum'])
    df_open['(Zelf) Verwachte Leverdatum'] = pd.to_datetime(df_open['(Zelf) Verwachte Leverdatum'])
    
    # dates for dimDates Table
    min_date = df_closed['(Zelf) Gerealiseerde Leverdatum'].min()
    max_date =  df_open['(Zelf) Verwachte Leverdatum'].max()
    
    # Create a dimDate table in order to effectively analyse the data
    # Same concept as in Power BI
    dates = pd.date_range(start=min_date, end=max_date)
    
    dimDates = pd.DataFrame({'Date':dates})
    dimDates['Year'] =dimDates['Date'].dt.year
    dimDates['Month'] =dimDates['Date'].dt.month
    dimDates['Day'] =dimDates['Date'].dt.day
    dimDates['Weekday'] =dimDates['Date'].dt.weekday
    dimDates['Quarter'] =dimDates['Date'].dt.quarter
    
    dimDates['Date'] = pd.to_datetime(dimDates['Date'])
    
    # coding the DP1 of both open and late
    closed_mapping = {
        'Op tijd geleverd (Op tijd geleverd)': 1,
        'Te laat geleverd (Te laat geleverd)': 0,
        'Te vroeg geleverd (Te vroeg geleverd)': 1,
        "Niet van toepassing (Niet van toepassing)": 99
    }
    
    # setting the DP1 to equal values make analysis much easier. 
    df_closed['DP1'] = df_closed['(Zelf) Leverbetrouwbaarheid 1'].map(closed_mapping)
    
    df_open['DP1'] = np.where(
        (df_open['(Zelf) Leverbetrouwbaarheid 1'] == 'Te laat (Te laat)') | (df_open['VDoc Positie Eerst bev. datum'] <= yesterday),
        0,
        99
    )
    
    # DP2 closed
    dp2_conditions = [
        df_closed['DP1'] == 1,
        df_closed['(Zelf) Gerealiseerde Leverdatum'] <= df_closed['VDoc Positie Laatst bev. datum']
    ]
    dp2_result = [1,1]
    df_closed['DP2'] = np.select(dp2_conditions, dp2_result, 0)
    
    # DP2 Open
    df_open['DP2'] = np.where(
        (df_open['DP1'] == 0) & (df_open['VDoc Positie Laatst bev. datum'] <= yesterday),
        0,
        99
    )
    
    # combining the two dfs. Using concat, it stacks the data if they have the same columns. 
    # When using pd.merge then it adds the columns
    
    df_orders = pd.concat([df_closed, df_open], ignore_index=True)
    
    # Merge the orders with dates
    #df_orders = dimDates.merge(df_orders, left_on='Date', right_on='(Zelf) Gerealiseerde Leverdatum', how='left')
    
    # Remove data from the Gerealiseerde Leverdatum for open orders as they do no make sense
    df_orders['(Zelf) Gerealiseerde Leverdatum'] = np.where(
        df_orders['OrderType'] == 'Open',
        pd.NaT,
        df_orders['(Zelf) Gerealiseerde Leverdatum']
    )
    
    # convert it back to datetime because after making the dates NaN the column cannot be treated as one Date Tyep
    df_orders['(Zelf) Gerealiseerde Leverdatum'] = pd.to_datetime(df_orders['(Zelf) Gerealiseerde Leverdatum'])
    
    # Get total scores
    Total_DP1_On_Time = df_orders['DP1'].value_counts().get(1)
    Total_DP1_Late = df_orders['DP1'].value_counts().get(0)
    daily_score = Total_DP1_On_Time / (Total_DP1_On_Time + Total_DP1_Late)
    
    def backlog_orders_DP1(df_orders, dimDates):
        
        results = []
    
        for current_date in sorted(dimDates['Date'].unique()):
            backlog_df = df_orders[
                (df_orders['VDoc Positie Eerst bev. datum'] < current_date) &
                (
                    df_orders['(Zelf) Gerealiseerde Leverdatum'].isna() |
                    (df_orders['(Zelf) Gerealiseerde Leverdatum'] > current_date)
                )
            ]
    
            backlog_count = backlog_df.shape[0]
            results.append({
                'Date':current_date,
                'Year': dimDates.loc[dimDates['Date'] == current_date, "Year"].sum(),
                'Month': dimDates.loc[dimDates['Date'] == current_date, "Month"].sum(),
                'Day': dimDates.loc[dimDates['Date'] == current_date, "Day"].sum(),
                'Weekday': dimDates.loc[dimDates['Date'] == current_date, "Weekday"].sum(),
                'Quarter': dimDates.loc[dimDates['Date'] == current_date, "Quarter"].sum(),
                'Open backlog count': backlog_count
            })
      
        return pd.DataFrame(results)
    
    def daily_score_dp1(df_orders, dimDates, backlog_df):
    
        results = []
    
        for current_date in sorted(dimDates['Date'].unique()):
            due_orders_df = df_orders[df_orders['VDoc Positie Eerst bev. datum'] == current_date]
    
            on_time = due_orders_df[due_orders_df['(Zelf) Gerealiseerde Leverdatum'] <= current_date].shape[0]
            late = due_orders_df[due_orders_df['(Zelf) Gerealiseerde Leverdatum'] > due_orders_df['VDoc Positie Eerst bev. datum']].shape[0]
            backlog_on_day = backlog_df.loc[backlog_df['Date'] == current_date, "Open backlog count"].sum()
            total_due = on_time + late + backlog_on_day
    
            daily_score = (on_time / total_due if total_due > 0 else 0)*100
    
            results.append({
                'Date':current_date,
                'Daily Score':round(daily_score,2),
                'On Time':on_time,
                'Late':late,
                'Backlog':backlog_on_day,
                'Year': dimDates.loc[dimDates['Date'] == current_date, "Year"].sum(),
                'Month': dimDates.loc[dimDates['Date'] == current_date, "Month"].sum(),
                'Day': dimDates.loc[dimDates['Date'] == current_date, "Day"].sum(),
                'Weekday': dimDates.loc[dimDates['Date'] == current_date, "Weekday"].sum(),
                'Quarter': dimDates.loc[dimDates['Date'] == current_date, "Quarter"].sum()
            })
        
        return pd.DataFrame(results)
    
    
    backlog_df = backlog_orders_DP1(df_orders, dimDates)
    daily_score_df = daily_score_dp1(df_orders, dimDates, backlog_df)
    daily_score_df_2024 = daily_score_df[daily_score_df['Year'] == 2024]

    # ------- Dashboard --------

    st.subheader("Performance Overview")

    # KPIs

    avergae_score = daily_score_df['Daily Score'].mean()
    total_on_time = daily_score_df['On Time'].sum()
    total_late = daily_score_df['Late'].sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Daily Score", f'{avergae_score:.2f}')
    with col2:
        st.metric("Total On Time",total_on_time)
    with col3:
        st.metric("Total Late", total_late)

    # Filtering by year

    years = daily_score_df['Year'].unique()
    selected_year = st.selectbox("Select Year", options=years, index=len(years)-1)
    filtered_df = daily_score_df[daily_score_df['Year'] == years]

    # Date range 
    
    min_date = filtered_df['Date'].min()
    max_date = filtered_df['Date'].max()
    date_range = st.date_input("Select Date Range", [min_date, max_date])
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[(filtered_df['Date'] >= pd.to_datetime(start_date)) & (filtered_df['Date'] <= pd.to_datetime(end_date))]
    
    st.subheader("Daily Score Trend")
    fig_bar = px.bar(filtered_df, x='Date',y=['On Time', 'Late', 'Backlog'], title='Daily Overview', barmode='stack')
    st.plotly_chart(fig_bar)
