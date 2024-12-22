import tushare as ts

# 初始化 Tushare
ts.set_token('893eb1c51517a48ea44f6690bc3709055e413c3239228b85b5090251')  # 替换为你的 API Token
pro = ts.pro_api()

# 获取中科曙光的实时数据
def get_real_time_data(stock_code):
    # 使用 pro.realtime_bars 获取实时数据
    data = pro.realtime_bars(ts_code=stock_code, asset='E', count=1)
    return data

# 示例调用
if __name__ == "__main__":
    stock_code = '603019.SH'  # 中科曙光的股票代码
    real_time_data = get_real_time_data(stock_code)
    print(real_time_data)