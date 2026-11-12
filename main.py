# %%
import os
import sys

print("Current working directory:", os.getcwd())
#print("Python executable:", sys.executable)
#print("Python import paths:", sys.path)

from pprint import pprint
from src.auth import create_aws_session
from src.collector import list_iam_users, list_user_access_keys, get_access_key_usage, normalize_access_key, list_iam_roles, normalize_role_trust_policy
from src.aws_inventory import collect_aws_iam_inventory

session = create_aws_session("security-audit")
iam = session.client("iam")

iam_inventory = collect_aws_iam_inventory(iam)

pprint(iam_inventory)


#role = iam_roles[0]
#print("Role details", role)
#print("Role Name:", role["RoleName"])
#pprint(iam_roles)
#print("Trust Policy:")
#pprint(role["AssumeRolePolicyDocument"])
#normalized_roles = []
#for role in iam_roles:
   #normalized_roles.extend([normalize_role_trust_policy(role)])
   #statements = role["AssumeRolePolicyDocument"]["Statement"]
#effect = statements[0]["Effect"]
#action = statements[0]["Action"]
#principal = statements[0]["Principal"]
   #for statement in statements:
   #   print(f"effect is {statement["Effect"]}")
   #   print(f"action is {statement["Action"]}")
   #   print(f"principal is {statement["Principal"]}")
#iam_inventory = collect_aws_iam_inventory(iam)

#print(len(normalized_roles))
#print(normalized_roles)

#print(iam_inventory)



# %%
