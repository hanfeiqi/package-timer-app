import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime

# 设置页面标题
st.set_page_config(page_title="📦 Package SLA Tracker", layout="wide")

st.title("📦 Package SLA Tracker with GOFO Time")

# 上传数据文件
uploaded_file = st.file_uploader("Upload your package data (.xlsx or .csv)", type=["xlsx", "csv"])
sla_file = st.file_uploader("Upload SLA config (.xlsx or .csv)", type=["xlsx", "csv"])

# 上传 SLA 配置文件
sla_file = st.file_uploader("Upload SLA config (.xlsx)", type=["xlsx"])

if uploaded_file and sla_file:
    df = pd.read_excel(uploaded_file)
    sla_df = pd.read_excel(sla_file)

    # 预处理字段
    df['GOFO签入时间'] = pd.to_datetime(df['GOFO签入时间'], errors='coerce')
    df['统计日期'] = pd.to_datetime(df['统计日期'], errors='coerce')

    # 合并SLA
    df = df.merge(sla_df, left_on='目的中心', right_on='中心', how='left')

    # 当前时间
    now = pd.Timestamp.now()

    # 计算耗时
    df['耗时(小时)'] = (now - df['GOFO签入时间']).dt.total_seconds() / 3600

    # 状态判断
    def classify_status(row):
        sla = row['SLA标准小时']
        elapsed = row['耗时(小时)']
        if pd.isna(sla) or pd.isna(elapsed):
            return 'Unknown'
        elif elapsed <= sla * 0.8:
            return 'On-Time'
        elif elapsed <= sla * 0.95:
            return 'Warning'
        elif elapsed <= sla:
            return 'Urgent'
        else:
            return 'Overdue'

    df['血条状态'] = df.apply(classify_status, axis=1)

    # 按中心+统计日期分类
    grouped = df.groupby(['目的中心', '统计日期', '血条状态']).size().unstack(fill_value=0).reset_index()

    # 展示表格
    st.subheader("📋 Classified Package SLA Summary")
    st.dataframe(grouped)

    # 状态汇总图
    st.subheader("📊 Package SLA Status Distribution")

    status_counts = df['血条状态'].value_counts().reindex(['On-Time', 'Warning', 'Urgent', 'Overdue'], fill_value=0)
    fig_bar, ax_bar = plt.subplots(figsize=(6, 4))
    ax_bar.bar(status_counts.index, status_counts.values, color=['green', 'yellow', 'orange', 'red'])
    ax_bar.set_title("📊 Package SLA Status (Bar Chart)")
    ax_bar.set_ylabel("Parcel Count")

    fig_pie, ax_pie = plt.subplots(figsize=(5, 5))
    ax_pie.pie(status_counts.values, labels=status_counts.index, autopct='%1.1f%%',
               startangle=90, colors=['green', 'yellow', 'orange', 'red'])
    ax_pie.set_title("🧁 Package SLA Status (Pie Chart)")

    # 折叠展示图表
    with st.expander("📈 Show SLA Charts"):
        st.pyplot(fig_bar)
        st.pyplot(fig_pie)

    # 导出功能
    def to_excel(dataframe: pd.DataFrame) -> BytesIO:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            dataframe.to_excel(writer, index=False, sheet_name='SLA_Status')
        output.seek(0)
        return output

    excel_data = to_excel(df)
    st.download_button("📤 Download Full Result (Excel)", data=excel_data,
                       file_name=f"SLA_Status_Result_{datetime.now().date()}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("📌 Please upload both the package data and the SLA config file.")
