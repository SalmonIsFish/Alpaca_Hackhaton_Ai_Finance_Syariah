from moomoo import OpenSecTradeContext, TrdEnv

trd_ctx = OpenSecTradeContext(
    host="127.0.0.1",
    port=11111
)

ret, data = trd_ctx.get_acc_list()
print("Connection result:", ret)
print(data)

trd_ctx.close()