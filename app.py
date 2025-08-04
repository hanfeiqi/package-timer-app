
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
import matplotlib.pyplot as plt

st.set_page_config(page_title="包裹血条状态工具", layout="wide")
st.title("📦 包裹血条状态计算工具（目的中心作为派送中心）")

st.markdown("上传两份文件：")
waybill_file = st.file_uploader("① 上传包裹数据文件（含“签入时间”、“目的中心”等）", type=["xlsx"])
sla_file = st.file_uploader("② 上传 SLA 配置文件（字段包含“中心”和“SLA小时”）", type=["xlsx"])

if waybill_file and sla_file:
    df = pd.read_excel(waybill_file)
    st.write("📋 文件列名如下（用于排查字段）：", df.columns.tolist())

    if '签入时间' not in df.columns or '目的中心' not in df.columns:
        st.error("❌ 数据中缺少“签入时间”或“目的中心”字段，请检查文件格式")
        st.stop()

    sla_df = pd.read_excel(sla_file)
    sla_dict = dict(zip(sla_df['中心'], sla_df['SLA小时']))

    # 数据清洗
    df['签入时间'] = pd.to_datetime(df['签入时间'], errors='coerce')
    df['中心'] = df['目的中心'].astype(str).str[:3]
    df['SLA小时'] = df['中心'].map(sla_dict)
    now = datetime.now()

    df_valid = df[df['SLA小时'].notnull()].copy()
    df_valid['截止时间'] = df_valid['签入时间'] + pd.to_timedelta(df_valid['SLA小时'], unit='h')
    df_valid['剩余时效'] = (df_valid['截止时间'] - now).dt.total_seconds() / 3600

    def classify(row):
        if row['剩余时效'] < 0:
            return '超时', 'darkred'
        elif row['剩余时效'] < 24:
            return '紧急', 'red'
        elif row['剩余时效'] < 48:
            return '预警', 'yellow'
        else:
            return '正常', 'green'

    df_valid[['血条状态', '血条颜色']] = df_valid.apply(classify, axis=1, result_type='expand')

    # 状态统计
    status_summary = (
        df_valid.groupby('血条状态')
        .size()
        .reset_index(name='包裹数量')
    )
    status_summary['占比'] = (status_summary['包裹数量'] / status_summary['包裹数量'].sum()).round(4)

    st.subheader("🧾 血条状态统计")
    st.dataframe(status_summary)

    st.subheader("📋 包裹明细（部分示例）")
    show_cols = ['箱/袋号', '中心', '签入时间', '截止时间', '剩余时效', '血条状态']
    for col in show_cols:
        if col not in df_valid.columns:
            show_cols.remove(col)
    st.dataframe(df_valid[show_cols].head(50))

    # 导出
    def to_excel(dataframes: dict) -> BytesIO:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            for name, df in dataframes.items():
                df.to_excel(writer, index=False, sheet_name=name[:31])
        output.seek(0)
        return output

    all_sheets = {status: group for status, group in df_valid.groupby('血条状态')}
    all_sheets['血条状态总览'] = status_summary

    excel_data = to_excel(all_sheets)
    st.download_button("📥 下载完整分析结果 Excel", data=excel_data, file_name="血条状态分析结果.xlsx")
    
    import matplotlib.pyplot as plt

    status_summary = pd.DataFrame({
        'Status': ['On-Time', 'Warning', 'Urgent', 'Overdue'],
        'Count': [120, 45, 20, 15]
})

# 英文柱状图
    fig_bar, ax_bar = plt.subplots()
    ax_bar.bar(status_summary['Status'], status_summary['Count'], color=['green', 'yellow', 'red', 'darkred'])
    ax_bar.set_title('📊 Package SLA Status (Bar Chart)')
    ax_bar.set_ylabel('Parcel Count')

# 英文饼图
    fig_pie, ax_pie = plt.subplots()
    ax_pie.pie(status_summary['Count'], labels=status_summary['Status'],
               autopct='%1.1f%%', startangle=90,
               colors=['green', 'yellow', 'red', 'darkred'])
    ax_pie.set_title('🧁 Package SLA Status (Pie Chart)')

    fig_bar, fig_pie
