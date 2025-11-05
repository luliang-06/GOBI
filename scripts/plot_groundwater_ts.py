import os
import re
import numpy as np
import pandas as pd
import seaborn as sns
import statsmodels.api as sm
import matplotlib.pyplot as plt
from statsmodels.robust.norms import HuberT
import matplotlib.dates as mdates
import matplotlib.ticker as mtick

# === 可调参数 ===
K_HUBER = 1.345     # Huber 阈值（标准化后）
EPS = 1e-6          # 防止除零
MIN_WEIGHT = 1e-3   # 最小权重
OUTLIER_SIGMA = 4.5 # outlier 放大系数

# === 1. Set up ===
sns.set_theme(style="whitegrid", context="talk")
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']

# set up path
input_path = '/Users/lianglu/Desktop/GOBI/data/2018-2022石羊河地下水位整合_水位.csv'
script_dir = os.getcwd()
plot_dir = os.path.join(script_dir, 'outputs_WLS_WaterLevel', 'plots')
csv_dir = os.path.join(script_dir, 'outputs_WLS_WaterLevel')
csv_file = os.path.join(csv_dir, 'WaterLevel_trend_summary.csv')
os.makedirs(plot_dir, exist_ok=True)
os.makedirs(csv_dir, exist_ok=True)

# 读取表格
df = pd.read_csv(input_path)
print(f"读取数据：{df.shape[0]} 行, {df.shape[1]} 列")
df.columns = df.columns.str.strip()  # 去掉可能首尾空格

# 关键列名
well_col = '统一编号'
year_col = '年份'
lon_col = '经度'
lat_col = '纬度'

# 自动定位“地面高程”列
elev_candidates = [c for c in df.columns if re.search(r'地面高程', str(c))]
if not elev_candidates:
    raise ValueError("在CSV中找不到包含“地面高程”的列, 请检查列名。")
elev_col = elev_candidates[0]

# 将海拔列预清理为数值（去掉可能的单位等）
df[elev_col] = (
    df[elev_col].astype(str).str.extract(r'([-+]?\d*\.?\d+)')[0]
)
df[elev_col] = pd.to_numeric(df[elev_col], errors='coerce')

# 找出监测日列
pattern = re.compile(r'^M\d{2}_D\d{2}$')
water_level_cols = [col for col in df.columns if pattern.match(str(col))]

# melt成长表
df_long = df.melt(
    id_vars=[well_col, year_col, lon_col, lat_col, elev_col],
    value_vars=water_level_cols,
    var_name='观测日期',
    value_name='水位'
)

## 解析日期
# 提取 month/day & 转 int
df_long[['month','day']] = df_long['观测日期'].str.extract(r'M(\d{2})_D(\d{2})').astype(float)
df_long[year_col] = pd.to_numeric(df_long[year_col], errors='coerce')
df_long = df_long.dropna(subset=[year_col, 'month', 'day'])

# 生成 datetime
df_long['date'] = pd.to_datetime(
    df_long[year_col].astype(int).astype(str) + '-' +
    df_long['month'].astype(int).astype(str).str.zfill(2) + '-' +
    df_long['day'].astype(int).astype(str).str.zfill(2),
    errors='coerce'
)
df_long = df_long.dropna(subset=['date'])

# 丢掉无效日期
df_long = df_long.dropna(subset=['date'])
print("无效日期数量：", df_long['date'].isna().sum())
print("年份范围：", df_long[year_col].min(), '-', df_long[year_col].max())

# 计算 time_fraction
year_int = df_long['date'].dt.year.astype(int)
start_of_year = pd.to_datetime(year_int.astype(str) + '-01-01')
end_of_year   = pd.to_datetime(year_int.astype(str) + '-12-31')
days_in_year  = (end_of_year - start_of_year).dt.days.replace(0, 365)
df_long['time_fraction'] = year_int + ((df_long['date'] - start_of_year).dt.days / days_in_year)

print(df_long[['统一编号','年份','观测日期','date']].head(30))

# 数据清洗
df_long['水位'] = pd.to_numeric(df_long['水位'], errors='coerce')
df_long['time_fraction'] = pd.to_numeric(df_long['time_fraction'], errors='coerce')
df_long[elev_col] = pd.to_numeric(df_long[elev_col], errors='coerce')

valid = (
    (~df_long['水位'].isna()) &
    (~df_long['time_fraction'].isna()) &
    (~df_long['水位'].isin([np.inf, -np.inf])) &
    (~df_long['time_fraction'].isin([np.inf, -np.inf]))
)
df_long = df_long[valid].copy()

### 2. 分组画图
result_list = []
for name, group in df_long.groupby(well_col):
    group = group.sort_values('date')

    # 该井的海拔（尽量取有效值）
    elevation = np.nan
    if elev_col in group.columns and group[elev_col].notna().any():
        elevation = group[elev_col].dropna().iloc[0]

    X = group['time_fraction'].astype(float)
    y = group['水位'].astype(float)
    if len(group) < 6:
        continue

    X_sm = sm.add_constant(X)

    # 1. Ordinary Least Squares (OLS)
    ols_res = sm.OLS(y, X_sm).fit()
    b_ols, m_ols = ols_res.params
    m_ols_err    = ols_res.bse.iloc[1]

    # 2. MAD Standard + (1/|r|) * HUBER weight -> WLS
    resid0 = y - (b_ols + m_ols * X)
    mad0 = np.median(np.abs(resid0 - np.median(resid0)))
    s0 = 1.4826 * mad0 + EPS
    u0 = resid0 / s0
    # Huber 权重
    w_huber0 = np.where(np.abs(u0) <= K_HUBER, 1.0, K_HUBER / (np.abs(u0) + EPS))
    # L1 风格权重（倒数）
    w_l1_0 = 1.0 / (np.abs(u0) + EPS)
    # 组合权重（更强鲁棒）：两者相乘
    w1 = np.clip(w_huber0 * w_l1_0, MIN_WEIGHT, None)

    rlm1_res = sm.WLS(y, X_sm, weights=w1).fit()
    b_rlm1, m_rlm1 = rlm1_res.params
    m_rlm1_err     = rlm1_res.bse.iloc[1]

    # 3. 2nd WLS
    resid1 = y - (b_rlm1 + m_rlm1 * X)
    mad1 = np.median(np.abs(resid1 - np.median(resid1)))
    s1 = 1.4826 * mad1 + EPS
    u1 = resid1 / s1

    w_huber1 = np.where(np.abs(u1) <= K_HUBER, 1.0, K_HUBER / (np.abs(u1) + EPS))
    w_l1_1   = 1.0 / (np.abs(u1) + EPS)
    w2 = np.clip(w_huber1 * w_l1_1, MIN_WEIGHT, None)

    rlm2_res = sm.WLS(y, X_sm, weights=w2).fit()
    b_rlm2, m_rlm2 = rlm2_res.params
    m_rlm2_err     = rlm2_res.bse.iloc[1]
    
    # plot
    fig, ax = plt.subplots(figsize=(12,7))
    sns.scatterplot(
        x=group['date'], y=y, ax=ax,
        s=60, alpha=0.5,
        facecolor='steelblue', edgecolor='navy', linewidth=0.8,
        label='Observed Data'
    )

    # OLS fitted line
    ax.plot([group['date'].min(), group['date'].max()],
            [b_ols + m_ols * X.min(), b_ols + m_ols * X.max()],
            linestyle='--', linewidth=2, color='#4a6ed9',
            label=f'OLS: {m_ols:.3f} ± {m_ols_err:.3f} m/yr')

    # 2nd WLS fitted line
    ax.plot([group['date'].min(), group['date'].max()],
            [b_rlm2 + m_rlm2 * X.min(), b_rlm2 + m_rlm2 * X.max()],
            linestyle='-', linewidth=2, color='#d94a70',
            label=f'WLS: {m_rlm2:.3f} ± {m_rlm2_err:.3f} m/yr')
    
    # Outliers
    resid_final = y - (b_rlm2 + m_rlm2 * X)
    thr = resid_final.abs().mean() + OUTLIER_SIGMA * resid_final.abs().std()
    is_out = resid_final.abs() > thr
    if is_out.any():
        y_main = y[~is_out]
        y_min_z, y_max_z = y_main.min(), y_main.max()
        margin = (y_max_z - y_min_z) * 0.10
        ax.set_ylim(y_min_z - margin, y_max_z + margin)
        sns.scatterplot(
            x=group['date'][is_out], y=y[is_out], ax=ax,
            color='red', marker='X', s=100,
            edgecolor='black', linewidth=1.2,
            label='Outlier', legend=False
        )
        
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.xaxis.set_minor_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_minor_formatter(plt.NullFormatter())
    ax.yaxis.set_major_formatter(mtick.FormatStrFormatter('%.0f'))
    ax.grid(True, which='major', linestyle='--', linewidth=0.7, color='grey')
    ax.grid(True, which='minor', linestyle='--', linewidth=0.5, color='lightgrey')

    ax.set_xlabel('Date', fontsize=14)
    ax.set_ylabel('Groundwater Level (m)', fontsize=14)

    elev_txt = f"{elevation:.2f}" if pd.notna(elevation) else "NA"
    ax.set_title(f'Well: {name}, Elevation: {elev_txt} m', fontsize=14)

    ax.legend(frameon=True, fontsize=12, framealpha=0.5, facecolor='white')
    ax.tick_params(axis='both', labelsize=14)
    plt.tight_layout()

    # 保存
    safe_name = re.sub(r'[\\/:*?"<>|]', '_', str(name))
    save_path = os.path.join(plot_dir, f'well_{safe_name}.png')
    plt.savefig(save_path)
    plt.close()
    print(f'已保存：{save_path}')

    ### 3. 统计
    result_list.append({
        'Well_ID': str(name),
        'Elevation_m': elevation,
        'OLS_slope_m_per_year': m_ols,
        'OLS_slope_std_error': m_ols_err,
        'RLM1_slope_m_per_year': m_rlm1,
        'RLM1_slope_std_error': m_rlm1_err,
        'RLM2_slope_m_per_year': m_rlm2,
        'RLM2_slope_std_error': m_rlm2_err,
        'Num_observations': len(X)
    })

# 汇总保存
result_df = pd.DataFrame(result_list)
result_df.to_csv(
    csv_file,
    index=False,
    encoding='utf-8-sig',
    float_format='%.3f'
)
print(f"统计结果已保存：{os.path.abspath(csv_file)}")


