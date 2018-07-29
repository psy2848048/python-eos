import json
import urllib.request
import urllib.parse

from eospy import endpoints
from eospy.transaction_builder import TransactionBuilder, Action


class EosClient:
    def __init__(self, api_endpoint=None, wallet_endpoint=None):
        if not api_endpoint:
            api_endpoint = endpoints.DEFAULT_EOS_API_ENDPOINT

        self.api_endpoint = api_endpoint
        self.wallet_endpoint = wallet_endpoint

    def request(self, endpoint, uri, body=None):
        if body:
            body = json.dumps(body).encode()
        url = urllib.parse.urljoin(endpoint, uri)
        request = urllib.request.Request(url, data=body)
        response = urllib.request.urlopen(request)
        return json.load(response)

    def api_request(self, uri, body=None):
        return self.request(self.api_endpoint, uri, body)

    def wallet_request(self, uri, body=None):
        if not self.wallet_endpoint:
            raise ValueError('No wallet endpoint set, cannot make wallet request!')
        return self.request(self.wallet_endpoint, uri, body)

    # ===== v1/wallet/ =====
    def wallet_lock(self, wallet='default'):
        return self.wallet_request(endpoints.WALLET_LOCK, wallet)

    def wallet_unlock(self, key, wallet='default'):
        return self.wallet_request(endpoints.WALLET_UNLOCK, [wallet, key])

    def wallet_open(self, wallet='default'):
        return self.wallet_request(endpoints.WALLET_OPEN, wallet)

    def wallet_get_public_keys(self):
        return self.wallet_request(endpoints.WALLET_GET_PUBLIC_KEYS)

    def wallet_sign_transaction(self, transaction, public_keys, chain_id):
        return self.wallet_request(
            endpoints.WALLET_SIGN_TRANSACTION, [transaction, public_keys, chain_id])

    # ===== v1/chain/ =====
    def chain_get_info(self):
        return self.api_request(endpoints.CHAIN_GET_INFO)

    def chain_get_block(self, num_or_id):
        return self.api_request(endpoints.CHAIN_GET_BLOCK, {'block_num_or_id': num_or_id})

    def chain_abi_json_to_bin(self, abi_args):
        return self.api_request(endpoints.CHAIN_ABI_JSON_TO_BIN, abi_args)

    def chain_get_required_keys(self, transaction, available_keys):
        return self.api_request(endpoints.CHAIN_GET_REQUIRED_KEYS, {
            'transaction': transaction,
            'available_keys': available_keys
        })

    def chain_push_transaction(self, transaction):
        return self.api_request(endpoints.CHAIN_PUSH_TRANSACTION, {
            'transaction': transaction,
            'compression': 'none',
            'signatures': transaction['signatures']
        })

    # ===== SYSTEM CONTRACT TRANSACTIONS =====
    def get_system_newaccount_binargs(self, creator, name, owner_key, active_key):
        return self.chain_abi_json_to_bin({
            "code": "eosio", "action": "newaccount",
            "args": {
                "creator": creator, "name": name,
                "owner": {
                    "threshold": 1,
                    "keys": [{
                        "key": owner_key,
                        "weight": 1
                    }],
                    "accounts": [],
                    "waits": []
                },
                "active": {
                    "threshold": 1,
                    "keys": [{
                        "key": active_key,
                        "weight": 1
                    }],
                    "accounts": [],
                    "waits": []
                }
            }
        })['binargs']

    def get_system_buyram_binargs(self, payer, receiver, quant):
        return self.chain_abi_json_to_bin({
            "code": "eosio", "action": "buyram",
            "args": {"payer": payer, "receiver": receiver, "quant": quant}
        })['binargs']

    def get_system_buyrambytes_binargs(self, payer, receiver, bytes_):
        return self.chain_abi_json_to_bin({
            "code": "eosio", "action": "buyrambytes",
            "args": {"payer": payer, "receiver": receiver, "bytes": bytes_}})['binargs']

    def get_system_delegatebw_binargs(self, from_, receiver, stake_net_quantity, stake_cpu_quantity, transfer):
        return self.chain_abi_json_to_bin({
            "code": "eosio", "action": "delegatebw",
            "args": {
                "from": from_,
                "receiver": receiver,
                "stake_net_quantity": stake_net_quantity,
                "stake_cpu_quantity": stake_cpu_quantity,
                "transfer": transfer
            }})['binargs']

    def system_newaccount(self, creator_account, created_account, owner_key, active_key,
                          stake_net_quantity, stake_cpu_quantity, transfer, buy_ram_kbytes):
        newaccount_binargs = self.get_system_newaccount_binargs(
            creator_account, created_account, owner_key, active_key)
        buyrambytes_binargs = self.get_system_buyrambytes_binargs(
            creator_account, created_account, buy_ram_kbytes * 1024)
        delegatebw_binargs = self.get_system_delegatebw_binargs(
            creator_account, created_account, stake_net_quantity, stake_cpu_quantity, transfer)

        transaction, chain_id = TransactionBuilder(self).build_sign_transaction_request((
            Action('eosio', 'newaccount', creator_account, 'active', newaccount_binargs),
            Action('eosio', 'buyrambytes', creator_account, 'active', buyrambytes_binargs),
            Action('eosio', 'delegatebw', creator_account, 'active', delegatebw_binargs),
        ))

        available_public_keys = self.wallet_get_public_keys()
        required_public_keys = self.chain_get_required_keys(transaction, available_public_keys)['required_keys']
        signed_transaction = self.wallet_sign_transaction(transaction, required_public_keys, chain_id)
        return self.chain_push_transaction(signed_transaction)


# w = Client(wallet_endpoint='http://localhost:8900')
# w.system_newaccount(
#     'tokenika4eos', 'perduta1test',
#     'EOS7VdRNSwuoUWjYEP4vG4Kz2Xe4HWHUDKxcHbqkAjoT2wk17ZB1y',
#     'EOS7VdRNSwuoUWjYEP4vG4Kz2Xe4HWHUDKxcHbqkAjoT2wk17ZB1y',
#     '0.2500 EOS', '0.2500 EOS', True, 8
# )
