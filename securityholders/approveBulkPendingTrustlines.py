import sys
sys.path.append("../")
from globals import *

secretKey = "" # Admin temporary 1-weight signers... execute on offline airgapped sys... then remove from Issuer 
# todo: set as function input as environmnet var in aigapped HSM 
identityMappingCSV = "" # todo: make a style for a master identity ledger... store on offline airgapps sys with weekly? updates and sole physical backup monthly? with secure custodians (split btwn with partial images? - registered mail encrypted drives?) and then wipe Persona ea. week? on a 2-mo delayed basis? 
# that might be a bit much, and we could probably just use an authenticated sftp channel or put in Storj? 

def getAllPendingTrustlinesWithAsset():
  requestAddress = "https://" + HORIZON_INST + "..." + BT_ISSUER + "..."
  data = requests.get(requestAddress).json()
  
  allPendingTrustlines = {}
  pendingTrustline = data[...]
  while(pendingTrustline):
    potentialAddress = pendingTrustline[...]
    # ditto 
    
    asset = pendingTrustline[...]
    # this needs to format potentialAsset correctly for later
    len(asset) > 4 ? ASSET_TYPE_CREDIT_ALPHANUM12 : ASSET_TYPE_CREDIT_ALPHANUM4
    credit_alphanum4_asset = Asset("USDC", BT_ISSUER)
    credit_alphanum12_asset = Asset("BANANA", BT_ISSUER)
    
    allPendingTrustlines[potentialAddress] = asset
    requestAddress = "https://" + HORIZON_INST + "..." + BT_ISSUER + "..." -> next
    data = requests.get(requestAddress).json()
    pendingTrustline = data[...]
  return allPendingTrustlines

def getKnownAddressesFromIdentityMappingCSV(inputCSV):
  allVerifiedAddresses[] = ""
  identityMapping = open(inputCSV, "r")
  identityMapping.readline()
  while(identityMapping.readline()):
    allVerifiedAddresses.append(identityMapping.readline().split(',')[0])
  return allVerifiedAddresses

def verifyAddressesWithAssetDict(addressesWithAssetsDict):
  allKnownShareholderAddressesList = getKnownAddressesFromIdentityMappingCSV(identityMappingCSV)
  verifiedAddressesWithAssetDict = {}
  i = 0
  for potentialAddress, potentialAsset in addressesWithAssetsDict:
    if(potentialAddress in allKnownShareholderAddressesList)
      todo += 1
      if (++i < MAX_NUM_TXN_OPS):
        verifiedAddressesWithAssetDict[potentialAddress] = potentialAsset
  return verifiedAddressesWithAssetDict

def signBulkTrustlineApprovalsFromAddressAssetDict(addressesWithAssetsDict):
  server = Server(horizon_url= "https://" + HORIZON_INST)
  issuer = server.load_account(account = BT_ISSUER)
  try: 
    fee = server.fetch_base_fee()
  except: 
    fee = FALLBACK_MIN_FEE
  
  transactions = []
  transactions.append(
    TransactionBuilder(
      source_account = issuer,
      network_passphrase = Network.PUBLIC_NETWORK_PASSPHRASE,
      base_fee = fee,
    )
  )
  reason = "Approve trustline: Shareholder KYC verified"
  numTxnOps, idx = 0
  for address, asset in addressesWithAssetsDict:
    transactions[idx].append_set_trust_line_flags_op(
      trustor = address,
      asset = asset,
      set_flags = 1
    ) 
    numTxnOps += 1
    if(numTxnOps += 1 >= MAX_NUM_TXN_OPS):
      transactions[idx] = transactions[idx].add_text_memo(reason).set_timeout(3600).build().sign(Keypair.from_secret(secretKey))
      numTxnOps += 1 = 0
      idx += 1
      transactions.append(
        TransactionBuilder(
          source_account = issuer,
          network_passphrase = Network.PUBLIC_NETWORK_PASSPHRASE,
          base_fee = fee,
        )
      )
  transactions[idx] = transactions[idx].add_text_memo("Approve trustline: Shareholder KYC verified").set_timeout(3600).build().sign(Keypair.from_secret(secretKey))
  return transactions

def exportTrustlineApprovalTransaction(txnXDRarr):
  for bulkTxnXDR in txnXDRarr:
    output = open(datetime.now() + " signedApprovePendingTrustlineXDR.txt", "w")
    output.write(bulkTxnXDR)
    output.close()

def approveBulkPendingTrustlines():
  pendingAddressesWithAssetsDict = getAllPendingTrustlinesWithAsset()
  verifiedAddressesWithAssetsDict = verifyAddressesWithAssetDict(pendingAddressesWithAssetsDict)
  signedTrustlineApprovalXDRarr = signBulkTrustlineApprovalsFromAddressAssetDict(verifiedAddressesWithAssetDict)
  exportTrustlineApprovalTransaction(signedTrustlineApprovalXDRarr)

