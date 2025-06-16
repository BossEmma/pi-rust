from stellar_sdk import Server, Keypair, TransactionBuilder, Asset
from mnemonic import Mnemonic
from keyfunc import account_keypair

my_seed_phrase = input("Enter your seed phrase: ")

def load_passphrases(filename):
    with open(filename, 'r') as file:
        return [line.strip() for line in file if line.strip()]

destination_phrases = load_passphrases('phrases.txt')

my_language = 'english' 
mnemo = Mnemonic(my_language)
if mnemo.check(my_seed_phrase):
    binary_seed = Mnemonic.to_seed(my_seed_phrase)
    destination_binary_seeds = [Mnemonic.to_seed(phrase) for phrase in destination_phrases]

account_number = 0 #
kp = account_keypair(binary_seed, account_number)

destination_keypairs = []
for binary_seed in destination_binary_seeds:
    dest_kp = account_keypair(binary_seed, account_number)
    destination_keypairs.append(Keypair.from_secret(dest_kp.secret))

source_keypair = Keypair.from_secret(kp.secret)
print(kp.secret) 

amount= "1"
server= Server("https://api.mainnet.minepi.com/") 

source_account = server.load_account(source_keypair.public_key) 
base_fee = server.fetch_base_fee() 

transaction_builder = (
    TransactionBuilder(
        source_account=source_account,
        network_passphrase="Pi Network",
        base_fee=base_fee,
    )
)

for dest_keypair in destination_keypairs:
    transaction_builder = transaction_builder.append_payment_op(dest_keypair.public_key, Asset.native(), amount)

transaction = transaction_builder.set_timeout(100).build()
transaction.sign(source_keypair)
response = server.submit_transaction(transaction)
print(response)
