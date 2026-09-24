import os
from openai import OpenAI
from dotenv import load_dotenv
import json
import httpx
from typing import Literal
import logging

logging.basicConfig(level=logging.INFO,format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

if api_key is None:
    raise RuntimeError("没有找到 DEEPSEEK_API_KEY 环境变量")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)


tools = [
    {
        "type":"function",
        "function":{
            "name":"get_order",
            "description":"根据订单编号查询真实的订单信息",
            "parameters":{
                "type":"object",
                "properties":{
                    "order_id":{
                        "type":"string",
                        "description":"需要查询的订单编号,例如A1001",
                    }
                },
                "required":["order_id"],
                "additionalProperties":False,
            }
        }
    },
    {
        "type":"function",
        "function":{
            "name":"list_orders",
            "description":"查询所有真实订单信息,可以根据status和product以及product_keyword分类查询",
            "parameters":{
                "type":"object",
                "properties":{
                    "status":{
                        "type":"string",
                        "description":"订单所处的状态,只有待发货,已发货,已取消"
                    },
                    "product":{
                        "type":"string",
                        "description":"商品的名称，如电脑，笔记本"
                    },
                    "product_keyword":{
                        "type":"string",
                        "description":"商品名称的模糊查询,适用于没有给出完整商品名称时使用"
                    },
                    "offset":{
                        "type":"integer",
                        "description":"跳过offset条记录,用于分页"
                    },
                    "limit":{
                        "type":"integer",
                        "description":"最大展示多少条订单"
                    }
                },"additionalProperties":False
            }

        }
    },
    {
        "type":"function",
        "function":{
            "name":"change_order_status",
            "description":"修改订单物流状态",
            "parameters":{
                "type":"object",
                "properties":{
                    "order_id":{
                        "type":"string",
                        "description":"需要修改的订单的编号"
                    },
                    "status":{
                        "type":"string",
                        "description":"实际需要修改的状态"
                    }
                },
                "required":["order_id","status"],
                "additionalProperties":False
            }
        }
    }
]

def call_model(messages):
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        tools=tools,
        tool_choice="auto",
        stream=False,
        extra_body={
            "thinking":{
                "type":"disabled",
            }
        }
    )
    return response.choices[0].message

ORDER_API_BASE_URL = "http://127.0.0.1:8000"

def get_order(order_id:str) -> dict:
    api_response = httpx.get(
        f"{ORDER_API_BASE_URL}/orders/{order_id}",
        timeout=5.0,
    )

    if api_response.status_code == 404:
        return {
            "error":"订单不存在",
            "order_id":order_id
        }

    api_response.raise_for_status()
    return api_response.json()


def list_orders(status:str|None = None,product:str|None = None,product_keyword:str|None = None,offset:int=0,limit:int =10):
    params = {"offset":offset,"limit":limit}
    if status is not None:
        params["status"] = status
    if product is not None:
        params["product"] = product
    if product_keyword is not None:
        params["product_keyword"] = product_keyword
    api_response=httpx.get(f"{ORDER_API_BASE_URL}/orders",params=params,timeout=5)

    api_response.raise_for_status()
    return api_response.json()

OrderStatus = Literal["已发货","待发货","已取消"]

def change_order_status(order_id:str,status:OrderStatus):
    current_order = get_order(order_id=order_id)
    if "error" in current_order:
        return current_order
    if current_order["status"] == status:
        return {"result":"no_change","message":f"该订单状态已经是 {status} 无需更改","data":current_order}
    conform = input(
        f"是否确定将订单 {order_id} 的状态"
        f"由 {current_order['status']}  改为 {status}  "
        f"确认输入 y 不确认输入 n"
    )
    if conform.strip().lower() == "y":
        api_response = httpx.patch(f"{ORDER_API_BASE_URL}/orders/{order_id}/status", json={"status": status}, timeout=5)

        if api_response.status_code == 403:
            error_data = api_response.json()
            return {"result":"rejected","message":error_data["detail"],"status_code":403}
        api_response.raise_for_status()
        updated_order = api_response.json()
        return {"result":"success","message":"订单修改成功","data":updated_order}
    elif conform.strip().lower() == "n":
        return {"result":"cancelled","message":"用户取消了修改"}
    else:
        return {"error":"用户的确认不合法,请输入y/n"}

TOOL_FUNCTIONS = {
    "get_order": get_order,
    "list_orders":list_orders,
    "change_order_status":change_order_status,
}

def get_http_error_message(response:httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return "订单服务返回了无法解析的错误"
    detail = data.get("detail")
    if isinstance(detail,str):
        return detail
    if isinstance(detail,list) and detail:
        return detail[0].get("msg","订单服务返回未知错误")
    return "订单服务返回未知错误"

def run_agent(
        user_question:str,
        messages:list,
        max_rounds:int = 5,
):
    messages.append({"role":"user","content":user_question})

    round_count = 0

    while round_count<max_rounds:
        round_count+=1

        message = call_model(messages=messages)

        if not message.tool_calls:
            messages.append(message)
            return message.content

        messages.append(message)
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            arguments_text = tool_call.function.arguments

            try:
                arguments = json.loads(arguments_text)
            except json.JSONDecodeError:
                tool_result = {"error":"工具参数不是合法JSON"}
                messages.append(
                    {
                        "role":"tool",
                        "tool_call_id":tool_call.id,
                        "content":json.dumps(tool_result,ensure_ascii=False)
                    }
                )
                continue
            if not isinstance(arguments,dict):
                tool_result = {"error":"参数不是字典类型"}
                messages.append(
                    {
                        "role":"tool",
                        "tool_call_id":tool_call.id,
                        "content":json.dumps(tool_result,ensure_ascii=False)
                    }
                )
                continue

            function = TOOL_FUNCTIONS.get(tool_name)
            if function is None:
                tool_result = {"error":f"不允许调用工具{tool_name}"}
                messages.append(
                    {
                        "role":"tool",
                        "tool_call_id":tool_call.id,
                        "content":json.dumps(tool_result,ensure_ascii=False)
                    }
                )
                continue

            logger.info(
                "第 %s 轮调用工具 %s ,调用 ID= %s ,参数字段=%s",
                round_count,tool_name,tool_call.id,list(arguments),
            )
            try:
                tool_result = function(**arguments)
            except TypeError as exc:
                logger.warning("工具参数错误：%s",exc)
                tool_result = {"error":"工具参数缺失或字段错误"}
            except httpx.RequestError:
                tool_result = {"error":"订单服务暂时无法连接"}
            except httpx.HTTPStatusError as exc:
                tool_result =  {
                    "error":"订单服务返回错误",
                    "status_code":exc.response.status_code,
                    "msg":get_http_error_message(exc.response)
                }

            if isinstance(tool_result,dict):
                operation_result = tool_result.get("result")
            else:
                operation_result = None

            if isinstance(tool_result, dict) and "error" in tool_result:
                logger.warning("工具 %s 失败：%s", tool_name, tool_result["error"])
            elif operation_result == "rejected":
                logger.warning("工具 %s 被业务规则拒绝： %s",tool_name,tool_result["message"])
            elif operation_result in {"cancelled","no_change"}:
                logger.info("工具 %s 未执行写入： %s",tool_name,tool_result["message"])
            else:
                logger.info("工具 %s 成功执行",tool_name)

            messages.append(
                {
                    "role":"tool",
                    "tool_call_id":tool_call.id,
                    "content":json.dumps(tool_result,ensure_ascii=False)
                },
            )

    raise RuntimeError(f"Agent执行超过最大次数：{max_rounds}")

messages = [{"role":"system","content":"你是一个订单客服助手。"}]

while True:
    question = input("请输入问题：")
    if question == "退出" or question == "q":
        break
    answer = run_agent(question,messages)
    print("最终回答：",answer)
