#!/usr/bin/env python3
'''
Written by Lu Liang, University of Edinburgh, School of Geosciences, 2025.

===========
Description
===========
Script to transfer Chinese address into coordinations through Amap API: 
https://lbs.amap.com/api/webservice/guide/api/georegeo

============
Inputs Files
============
local/
    address.xlsx

============
Output Files
============
local/
    address_with_latlng.xlsx
'''
# Change Log
'''
v1.0 20251215, Lu Liang, UoE
'''

import os
import sys
import time
import requests
import pandas as pd

author = 'Lu Liang, University of Edinburgh, School of Geosciences'
ver = 'v1.0'
last_update = '2025-12-15'

# Start
start = time.time()
print('\n{} ver{} {} {}'.format(os.path.basename(sys.argv[0]), ver, last_update, author))


# 你的高德API key
api_key = '051288489242c002525e170828eadb1b'

# 读取Excel
input_file = '/Users/lianglu/Desktop/GroundWaterData/address.xlsx'
df = pd.read_excel(input_file)

# 假设地址在第一列（即第0列），你可以根据实际修改
address_col = address_col = "监测点位置"

# 新增“经度”“纬度”列
df['经度'] = ''
df['纬度'] = ''

for idx, row in df.iterrows():
    address = str(row[address_col])
    # 跳过空地址
    if not address or address.strip() == '':
        continue

    url = f'https://restapi.amap.com/v3/geocode/geo?address={address}&output=JSON&key={api_key}'
    try:
        resp = requests.get(url)
        data = resp.json()
        if data['status'] == '1' and int(data['count']) > 0:
            location = data['geocodes'][0]['location']
            lng, lat = location.split(',')
            df.at[idx, '经度'] = lng
            df.at[idx, '纬度'] = lat
        else:
            print(f"未查询到经纬度：{address}")
    except Exception as e:
        print(f"发生错误：{address}, {e}")

    # 防止被限流，每次请求间隔0.2秒
    time.sleep(0.2)

# 保存新Excel
output_file = 'address_with_latlng.xlsx'
df.to_excel(output_file, index=False)
print(f"全部完成，已输出到：{output_file}")

# Finish
elapsed = time.time() - start
h = int(elapsed / 3600)
m = int((elapsed % 3600) / 60)
s = int(elapsed % 60)
print('\nElapsed time: {:02}h {:02}m {:02}s'.format(h, m, s))
print('\n{} successfully finished!\n'.format(os.path.basename(sys.argv[0])))
