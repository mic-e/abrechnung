from datetime import date

import schema
from aiohttp import web
from aiohttp.abc import Request

from abrechnung.http.serializers import TransactionSerializer
from abrechnung.http.utils import json_response, validate

routes = web.RouteTableDef()


@routes.get(r"/groups/{group_id:\d+}/transactions")
async def list_transactions(request):
    group_id: int = int(request.match_info["group_id"])
    transactions = await request.app["transaction_service"].list_transactions(
        user_id=request["user"]["user_id"], group_id=group_id
    )

    serializer = TransactionSerializer(transactions)
    return json_response(data=serializer.to_repr())


@routes.post(r"/groups/{group_id:\d+}/transactions")
@validate(
    schema.Schema(
        {
            "description": str,
            "type": str,
            "value": schema.Or(float, int),
            "currency_symbol": str,
            "billed_at": schema.Use(date.fromisoformat),
            "currency_conversion_rate": schema.Or(float, int),
        }
    )
)
async def create_transaction(request: Request, data: dict):
    group_id: int = int(request.match_info["group_id"])

    transaction_id = await request.app["transaction_service"].create_transaction(
        user_id=request["user"]["user_id"],
        group_id=group_id,
        description=data["description"],
        type=data["type"],
        currency_symbol=data["currency_symbol"],
        currency_conversion_rate=float(data["currency_conversion_rate"]),
        billed_at=date.fromisoformat(data["billed_at"]),
        value=float(data["value"]),
    )

    return json_response(data={"transaction_id": transaction_id})


@routes.get(r"/transactions/{transaction_id:\d+}")
async def get_transaction(request: Request):

    transaction = await request.app["transaction_service"].get_transaction(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
    )

    serializer = TransactionSerializer(transaction)

    return json_response(data=serializer.to_repr())


@routes.post(r"/transactions/{transaction_id:\d+}")
@validate(
    schema.Schema(
        {
            "description": str,
            "value": schema.Or(float, int),
            "currency_symbol": str,
            "billed_at": schema.Use(date.fromisoformat),
            "currency_conversion_rate": schema.Or(float, int),
        }
    )
)
async def update_transaction(request: Request, data: dict):
    await request.app["transaction_service"].update_transaction(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
        value=data["value"],
        description=data["description"],
        currency_symbol=data["currency_symbol"],
        currency_conversion_rate=data["currency_conversion_rate"],
        billed_at=date.fromisoformat(data["billed_at"]),
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.post(r"/transactions/{transaction_id:\d+}/commit")
async def commit_transaction(request: Request):
    await request.app["transaction_service"].commit_transaction(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.delete(r"/transactions/{transaction_id:\d+}")
async def delete_transaction(request: Request):
    await request.app["transaction_service"].delete_transaction(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.post(r"/transactions/{transaction_id:\d+}/new_change")
async def create_transaction_change(request: Request):
    await request.app["transaction_service"].create_transaction_change(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.post(r"/transactions/{transaction_id:\d+}/discard")
async def discard_transaction_change(request: Request):
    await request.app["transaction_service"].discard_transaction_changes(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.post(r"/transactions/{transaction_id:\d+}/creditor_shares")
@validate(
    schema.Schema(
        {
            "account_id": int,
            "value": schema.Or(float, int),
        }
    )
)
async def add_or_change_creditor_share(request: Request, data: dict):
    await request.app["transaction_service"].add_or_change_creditor_share(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
        account_id=data["account_id"],
        value=float(data["value"]),
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.post(r"/transactions/{transaction_id:\d+}/creditor_shares/switch")
@validate(
    schema.Schema(
        {
            "account_id": int,
            "value": schema.Or(float, int),
        }
    )
)
async def switch_creditor_share(request: Request, data: dict):
    await request.app["transaction_service"].switch_creditor_share(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
        account_id=data["account_id"],
        value=float(data["value"]),
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.delete(r"/transactions/{transaction_id:\d+}/creditor_shares")
@validate(
    schema.Schema(
        {
            "account_id": int,
        }
    )
)
async def delete_creditor_share(request: Request, data: dict):
    await request.app["transaction_service"].delete_creditor_share(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
        account_id=data["account_id"],
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.post(r"/transactions/{transaction_id:\d+}/debitor_shares")
@validate(
    schema.Schema(
        {
            "account_id": int,
            "value": schema.Or(float, int),
        }
    )
)
async def add_or_change_debitor_share(request: Request, data: dict):
    await request.app["transaction_service"].add_or_change_debitor_share(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
        account_id=data["account_id"],
        value=float(data["value"]),
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.post(r"/transactions/{transaction_id:\d+}/debitor_shares/switch")
@validate(
    schema.Schema(
        {
            "account_id": int,
            "value": schema.Or(float, int),
        }
    )
)
async def switch_debitor_share(request: Request, data: dict):
    await request.app["transaction_service"].switch_debitor_share(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
        account_id=data["account_id"],
        value=float(data["value"]),
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.delete(r"/transactions/{transaction_id:\d+}/debitor_shares")
@validate(
    schema.Schema(
        {
            "account_id": int,
        }
    )
)
async def delete_debitor_share(request: Request, data: dict):
    await request.app["transaction_service"].delete_debitor_share(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
        account_id=data["account_id"],
    )

    return json_response(status=web.HTTPNoContent.status_code)


@routes.post(r"/transactions/{transaction_id:\d+}/purchase_items")
@validate(
    schema.Schema(
        {
            "name": str,
            "price": schema.Or(int, float),
            "communist_shares": schema.Or(int, float),
        }
    )
)
async def create_purchase_item(request: Request, data: dict):
    item_id = await request.app["transaction_service"].create_purchase_item(
        user_id=request["user"]["user_id"],
        transaction_id=int(request.match_info["transaction_id"]),
        name=data["name"],
        price=data["price"],
        communist_shares=data["communist_shares"],
    )

    return json_response(data={"item_id": item_id})


@routes.post(r"/purchase_items/{item_id:\d+}")
@validate(
    schema.Schema(
        {
            "name": str,
            "price": schema.Or(int, float),
            "communist_shares": schema.Or(int, float),
        }
    )
)
async def update_purchase_item(request: Request, data: dict):
    await request.app["transaction_service"].update_purchase_item(
        user_id=request["user"]["user_id"],
        item_id=int(request.match_info["item_id"]),
        name=data["name"],
        price=data["price"],
        communist_shares=data["communist_shares"],
    )

    return web.Response(status=web.HTTPNoContent.status_code)


@routes.post(r"/purchase_items/{item_id:\d+}/shares")
@validate(
    schema.Schema(
        {
            "account_id": int,
            "share_amount": schema.Or(int, float),
        }
    )
)
async def add_or_change_item_share(request: Request, data: dict):
    await request.app["transaction_service"].add_or_change_item_share(
        user_id=request["user"]["user_id"],
        item_id=int(request.match_info["item_id"]),
        account_id=data["account_id"],
        share_amount=data["share_amount"],
    )

    return web.Response(status=web.HTTPNoContent.status_code)


@routes.delete(r"/purchase_items/{item_id:\d+}/shares")
@validate(
    schema.Schema(
        {
            "account_id": int,
        }
    )
)
async def delete_item_share(request: Request, data: dict):
    await request.app["transaction_service"].delete_item_share(
        user_id=request["user"]["user_id"],
        item_id=int(request.match_info["item_id"]),
        account_id=data["account_id"],
    )

    return web.Response(status=web.HTTPNoContent.status_code)


@routes.delete(r"/purchase_items/{item_id:\d+}")
async def delete_purchase_item(request: Request):
    await request.app["transaction_service"].delete_purchase_item(
        user_id=request["user"]["user_id"], item_id=int(request.match_info["item_id"])
    )

    return web.Response(status=web.HTTPNoContent.status_code)
