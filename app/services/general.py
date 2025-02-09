import grpc
from cosmpy.aerial.config import NetworkConfig
from cosmpy.aerial.client import LedgerClient
from cosmpy.protos.cosmos.staking.v1beta1.query_pb2 import QueryDelegatorDelegationsRequest, \
    QueryValidatorDelegationsRequest
from cosmpy.protos.cosmos.staking.v1beta1.query_pb2_grpc import QueryStub
from cosmpy.protos.cosmos.base.query.v1beta1.pagination_pb2 import PageResponse, PageRequest

def get_delegators_from_cosmos():
    cosmos_config = NetworkConfig(
        chain_id="cosmoshub-4",
        url="grpc+https://grpc.cosmoshub-4.bronbro.io:443",
        fee_minimum_gas_price=0.01,
        fee_denomination="uatom",
        staking_denomination="uatom",
        faucet_url=None
    )

    client = LedgerClient(cosmos_config)

    latest_block = client.query_latest_block()
    print("Latest Block:", latest_block)

    # Подключение к gRPC серверу
    channel = grpc.insecure_channel("grpc+https://grpc.cosmoshub-4.bronbro.io:443")
    staking_client = QueryStub(channel)

    # Адрес валидатора
    validator_address = "cosmosvaloper106yp7zw35wftheyyv9f9pe69t8rteumjrx52jg"  # Укажите адрес нужного валидатора

    pagination = PageRequest(limit=500)
    delegators = []
    while True:
        req = QueryValidatorDelegationsRequest(validator_addr=validator_address,
                                               pagination=pagination)
        res = client.staking.ValidatorDelegations(req)
        delegators += res.delegation_responses
        if len(res.pagination.next_key) == 0:
            break
        pagination = PageRequest(limit=500, key=res.pagination.next_key)
    return delegators