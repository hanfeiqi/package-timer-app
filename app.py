
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO

st.set_page_config(page_title="Package SLA Monitor", layout="wide")

st.title("📦 Package SLA Tracker with Upload")
st.markdown("Upload waybill Excel file and SLA standard file (center & deadline in hours).")

waybill_file = st.file_uploader("📤 Upload Waybill Data (.xlsx)", type="xlsx")
sla_file = st.file_uploader("📤 Upload SLA Standards (.xlsx)", type="xlsx")

if waybill_file and sla_file:
    df = pd.read_excel(waybill_file)
    sla_df = pd.read_excel(sla_file)

    # 清洗字段
    df['签入时间'] = pd.to_datetime(df['签入时间'], dayfirst=True, errors='coerce')
    df['中心'] = df['目的中心'].str[:3]

    # 合并SLA标准
    sla_dict = dict(zip(sla_df['中心'], sla_df['时效考核要求（小时）']))
    df['SLA时效（小时）'] = df['中心'].map(sla_dict)

    # 当前时间 & 计算已耗时
    now = pd.Timestamp.now()
    df['已耗时（小时）'] = (now - df['签入时间']).dt.total_seconds() / 3600

    # 血条状态分类
    def classify(row):
        deadline = row['SLA时效（小时）']
        used = row['已耗时（小时）']
        if pd.isna(deadline) or pd.isna(used):
            return '未知', 'gray'
        if used < 0.5 * deadline:
            return '正常', 'green'
        elif used < 0.8 * deadline:
            return '预警', 'yellow'
        elif used < deadline:
            return '紧急', 'red'
        else:
            return '超时', 'darkred'

    df[['血条状态', '血条颜色']] = df.apply(classify, axis=1, result_type='expand')
    df_valid = df.dropna(subset=['签入时间', 'SLA时效（小时）'])

    st.success(f"✅ Loaded {len(df_valid)} valid records")

    # 状态英文映射
    status_map = {'正常': 'On-Time', '预警': 'Warning', '紧急': 'Urgent', '超时': 'Overdue'}
    df_valid['SLA Status'] = df_valid['血条状态'].map(status_map)

    # 图表展示
    status_summary = df_valid['SLA Status'].value_counts().reset_index()
    status_summary.columns = ['Status', 'Count']

    with st.expander("📊 View SLA Status Distribution Charts"):
        fig_bar, ax_bar = plt.subplots(figsize=(6, 4))
        ax_bar.bar(status_summary['Status'], status_summary['Count'], color=['green', 'yellow', 'red', 'darkred'])
        ax_bar.set_title('📊 Package SLA Status (Bar Chart)')
        ax_bar.set_ylabel('Parcel Count')
        st.pyplot(fig_bar)

        fig_pie, ax_pie = plt.subplots(figsize=(5, 5))
        ax_pie.pie(status_summary['Count'], labels=status_summary['Status'],
                   autopct='%1.1f%%', startangle=90,
                   colors=['green', 'yellow', 'red', 'darkred'])
        ax_pie.set_title('🧁 Package SLA Status (Pie Chart)')
        st.pyplot(fig_pie)

    # 展示表格
    st.dataframe(df_valid[['运单号', '签入时间', '派送方', '中心', 'SLA时效（小时）', '已耗时（小时）', '血条状态']])

    # 导出功能
    def to_excel(dataframe: pd.DataFrame) -> BytesIO:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            dataframe.to_excel(writer, index=False, sheet_name='SLA Report')
        output.seek(0)
        return output

    export_data = to_excel(df_valid)
    st.download_button("📥 Download Result as Excel", data=export_data, file_name="sla_result.xlsx")
