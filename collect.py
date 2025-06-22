from stellar_sdk import Server, Keypair, TransactionBuilder, Asset
from mnemonic import Mnemonic
from keyfunc import account_keypair  

def load_passphrases(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip()]

DESTINATION_PHRASES_FILE = "phrases.txt"
SOURCE_PASSPHRASE = input("Enter your seed phrase (Source Wallet): ")

server = Server("http://173.230.130.166:8000/")
my_language = 'english'
mnemo = Mnemonic(my_language)

destination_phrases = load_passphrases(DESTINATION_PHRASES_FILE)


if mnemo.check(SOURCE_PASSPHRASE):
    binary_seed_source = Mnemonic.to_seed(SOURCE_PASSPHRASE)
    kp_source = account_keypair(binary_seed_source, 0)
    source_keypair = Keypair.from_secret(kp_source.secret)
else:
    raise Exception("Invalid source passphrase")


destination_binary_seeds = [Mnemonic.to_seed(phrase) for phrase in destination_phrases]
destination_keypairs = []
for binary_seed_dest in destination_binary_seeds:
    dest_kp = account_keypair(binary_seed_dest, 0)
    destination_keypairs.append(Keypair.from_secret(dest_kp.secret))

payment_ops = []
signers = []
for idx, dest_keypair in enumerate(destination_keypairs):
    try:
        account = server.accounts().account_id(dest_keypair.public_key).call()
        for b in account['balances']:
            if b.get('asset_type') == 'native':
                bal = float(b.get('balance'))
                amount_to_send = bal - 0.99
                if amount_to_send > 0:
                    send_amt_str = f"{amount_to_send:.7f}".rstrip('0').rstrip('.') if '.' in f"{amount_to_send:.7f}" else f"{amount_to_send:.7f}"
                    print(f"Destination {idx+1} ({dest_keypair.public_key}) balance: {bal} | sending back: {send_amt_str}")
                    payment_ops.append({
                        "source": dest_keypair.public_key,
                        "amount": send_amt_str
                    })
                    signers.append(dest_keypair)
                else:
                    print(f"Balance too low to send from {dest_keypair.public_key}")
    except Exception as e:
        print(f"Destination {idx+1} ({dest_keypair.public_key}) not found or error: {e}")

if payment_ops:
    for op, signer in zip(payment_ops, signers):
        transaction_builder = TransactionBuilder(
            source_account=server.load_account(source_keypair.public_key),
            network_passphrase="Pi Network",
            base_fee=server.fetch_base_fee(),
        )
        transaction_builder = transaction_builder.append_payment_op(
            destination=source_keypair.public_key,
            asset=Asset.native(),
            amount=op["amount"],
            source=op["source"]
        )
        transaction = transaction_builder.set_timeout(2000).build()
        transaction.sign(signer)
        transaction.sign(source_keypair)
        response = server.submit_transaction(transaction)
        print(f"Response for {signer.public_key}: {response}")
else:
    print("No payments to collect.")
