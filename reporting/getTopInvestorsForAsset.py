import sys
sys.path.append("../")
from globals import *

def getTopInvestorsForAsset(queryAsset, numTopInvestors):
  ledgerBalances = getLedgerBalances(queryAsset)
  return sorted(
    ledgerBalances.items(),
    key = lambda x:x[1],
    reverse = True
  )[:numTopInvestors]
