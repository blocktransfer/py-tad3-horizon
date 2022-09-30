from stellar_sdk import Asset, Keypair, Network, Server, TransactionBuilder, TrustLineFlags
from stellar_sdk.xdr import TransactionResult
from datetime import datetime
from decimal import Decimal
from pprint import pprint
import json, os.path, pandas, requests, sys, toml
import globalTxnFormatting

G_DIR = os.path.dirname(__file__)
sys.path.append("../")
try:
  from local_secrets import *
except ModuleNotFoundError:
  TRIAL_KEY = "SBTPLXTXJDMJOXFPYU2ANLZI2ARDPHFKPKK4MJFYVZVBLXYM5AIP3LPK"
  ISSUER_KEY = DISTRIBUTOR_KEY = TREASURY_KEY = TRIAL_KEY

# Debug issuers:
# accounts - GD3VPKNLTLBEKRY56AQCRJ5JN426BGQEPE6OIX3DDTSEEHQRYIHIUGUM
# trustlines - GD7HBNPUAIK5QW7MLC7VKKHIQZCYZYCAC4YNRT3YOPYPQRK3G5ZGQJOS
BT_ISSUER = "GDRM3MK6KMHSYIT4E2AG2S2LWTDBJNYXE4H72C7YTTRWOWX5ZBECFWO7"
BT_DISTRIBUTOR = "GAQKSRI4E5643UUUMJT4RWCZVLY25TBNZXDME4WLRIF5IPOLTLV7N4N6"
BT_TREASURY = "GD2OUJ4QKAPESM2NVGREBZTLFJYMLPCGSUHZVRMTQMF5T34UODVHPRCY"
USDC_ASSET = Asset("USDC", "GA5ZSEJYB37JRC5AVCIA5MOP4RHTM335X2KGX3IHOJAPP5RE34K4KZVN")
USD_ASSET = Asset("USD", BT_ISSUER)
# USD_ASSET = Asset("TERN", "GDGQDVO6XPFSY4NMX75A7AOVYCF5JYGW2SHCJJNWCQWIDGOZB53DGP6C") # 8949 testing
MICR_CSV = f"{G_DIR}/../pii/master-identity-catalog-records.csv" #todo: modify here to load from Box; set auth

BT_STELLAR_TOML = "https://blocktransfer.io/.well-known/stellar.toml"
HORIZON_INST = "horizon.stellar.org"
MAX_NUM_DECIMALS = "7"
MAX_SEARCH = "200"
MAX_NUM_TXN_OPS = 100
BASE_FEE_MULT = 2
WASH_SALE_DAY_RANGE = 30

server = Server(horizon_url = "https://" + HORIZON_INST)
issuer = server.load_account(account_id = BT_ISSUER)
distributor = server.load_account(account_id = BT_DISTRIBUTOR)
treasury = server.load_account(account_id = BT_TREASURY)
fee = server.fetch_base_fee() * BASE_FEE_MULT

# Todo: clean up globals by moving functions to imports under main dir

def getAssetAccountsRequestAddr(queryAsset):
  return f"https://{HORIZON_INST}/accounts?asset={queryAsset}:{BT_ISSUER}&limit={MAX_SEARCH}"

def getStellarBlockchainBalances(queryAsset):
  StellarBlockchainBalances = {}
  requestAddr = getAssetAccountsRequestAddr(queryAsset)
  ledger = requests.get(requestAddr).json()
  while(ledger["_embedded"]["records"]):
    for accounts in ledger["_embedded"]["records"]:
      accountAddr = accounts["id"]
      for balances in accounts["balances"]:
        try:
          if balances["asset_code"] == queryAsset and balances["asset_issuer"] == BT_ISSUER:
            queryBalance = Decimal(balances["balance"])
        except KeyError:
          continue
      StellarBlockchainBalances[accountAddr] = queryBalance
    ledger = getNextLedgerData(ledger)
  return StellarBlockchainBalances

def getNextLedgerData(ledger):
  nextAddr = ledger["_links"]["next"]["href"].replace("%3A", ":").replace("\u0026", "&")
  ledger = requests.get(nextAddr).json()
  return ledger

#todo: stress test
def submitTxnGarunteed(transaction):
  while(True):
    if(server.submit_transaction(transaction)):
      return 1

def resolveFederationAddress(properlyFormattedAddr):
  splitAddr = properlyFormattedAddr.split("*")
  federationName = splitAddr[0]
  federationDomain = splitAddr[1]
  homeDomainFederationServer = getFederationServerFromDomain(federationDomain)
  requestAddr = f"{homeDomainFederationServer}?q={properlyFormattedAddr}&type=name"
  data = requests.get(requestAddr).json()
  try: 
    return data["account_id"]
  except Exception:
    sys.exit("Could not find {}".format(properlyFormattedAddr))

def getFederationServerFromDomain(federationDomain):
  def formatNoEndSlash(link):
    return link if link.split("/")[-1] else link[:-1]
  try:
    requestAddr = f"https://{federationDomain}/.well-known/stellar.toml"
    data = loadTomlData(requestAddr)
    homeDomainFederationServer = formatNoEndSlash(data["FEDERATION_SERVER"])
  except Exception:
    sys.exit(f"Failed to lookup federation server at {federationDomain}")
  return homeDomainFederationServer

def loadTomlData(link):
  return toml.loads(requests.get(link).content.decode())

def getAssetCodeFromTomlLink(link):
  return link[32:-5]

def getCUSIP(queryAsset):
  try:
    data = loadTomlData(BT_STELLAR_TOML)
    for currencies in data["CURRENCIES"]:
      assetCode = getAssetCodeFromTomlLink(currencies["toml"])
      if(assetCode == queryAsset):
        data = loadTomlData(currencies["toml"])
        CUSIP = currencies["anchor_asset"]
        break
  except Exception:
    sys.exit(f"Failed to lookup ITIN for {queryAsset}")
  return CUSIP

def toFullAddress(street, streetExtra, city, state, postal, country):
  uncheckedArr = [street, streetExtra, city, state, postal, country]
  cleanArr = []
  for items in uncheckedArr:
    if(items):
      cleanArr.append(items)
  return ", ".join(cleanArr)

def getValidAccountPublicKeys():
  validAccountPublicKeys = []
  inFile = open(MICR_CSV)
  MICR = inFile.read().strip().split("\n")
  inFile.close()
  for lines in MICR[1:]:
    lines = lines.split(",")
    validAccountPublicKeys.append(lines[0]) # assumes only one account
  return validAccountPublicKeys

def getStockOutstandingShares(queryAsset):
  requestAddr = f"https://{HORIZON_INST}/assets?asset_code={QueryAsset}&asset_issuer=BT_ISSUER"
  data = requests.get(requestAddr).json()
  outstandingInclTreasuryShares = data["_embedded"]["records"][0]["amount"]
  treasuryAddr = resolveFederationAddress(f"{queryAsset}*treasury.holdings")
  requestAddr = f"https://{HORIZON_INST}/accounts/{treasuryAddr}"
  accountBalances = requests.get(requestAddr).json()["balances"]
  queryAsset = Asset(queryAsset, BT_ISSUER)
  for balances in accountBalances:
    if(balances["asset_type"] != "native" and Asset(balances["asset_code"], balances["asset_issuer"]) == queryAsset):
      treasuryShares = balances["balance"]
  return outstandingInclTreasuryShares - treasuryShares

