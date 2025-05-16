from stellar_sdk import Server, Keypair, Asset, TransactionBuilder
from mnemonic import Mnemonic
from keyfunc import account_keypair  
import json

# Get user input
my_seed_phrase = input("Enter your seed phrase: ")
my_seed_phrase2 = input("Enter your seed phrase (Fee): ")
des_address = input("Enter the destination address: ")
amount = input("Enter the amount to send: ")
balance_id = input("Enter the balance ID: ")

# Validate mnemonic
mnemo = Mnemonic('english')
if not mnemo.check(my_seed_phrase):
    print("❌ Invalid seed phrase.")
    exit()

# Derive keypair
binary_seed = Mnemonic.to_seed(my_seed_phrase)
binary_seed2 = Mnemonic.to_seed(my_seed_phrase2)
kp = account_keypair(binary_seed, 0)
kp2 = account_keypair(binary_seed2, 0)
source_keypair = Keypair.from_secret(kp.secret)
source_keypair2 = Keypair.from_secret(kp2.secret)

# Connect to Horizon server
server = Server("https://api.mainnet.minepi.com/")
source_account = server.load_account(account_id=source_keypair2.public_key)
base_fee = server.fetch_base_fee()
current_seq = int(source_account.sequence)

# Prepare multiple fee bump transactions
txs = []
for i in range(200):
    tx_builder = TransactionBuilder(
        source_account=source_account,
        network_passphrase="Pi Network",
        base_fee=base_fee
    )
    tx_builder.append_claim_claimable_balance_op(balance_id=balance_id, source=source_keypair.public_key)
    tx_builder.append_payment_op(destination=des_address, asset=Asset.native(), amount=amount, source=source_keypair.public_key)
    tx_builder.set_timeout(2000)
    tx = tx_builder.build()
    tx.sequence = str(current_seq + i + 1)
    tx.sign(source_keypair2)
    tx.sign(source_keypair)
    txs.append(tx.to_xdr())

    print(f"\n📦 Transaction {i+1}")
    print("Sequence:", tx.sequence)
    print("Fee Bump XDR:", tx.to_xdr())

# Save XDRs to file as strings
output = {f"transaction{i+1}": xdr for i, xdr in enumerate(txs)}
with open("xdrs.json", "w") as json_file:
    json.dump(output, json_file, indent=2)

print("\n✅ XDRs saved to xdrs.json")
